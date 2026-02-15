from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from jiwer import cer
from pydantic import BaseModel
from rich.console import Console

from ffmpeg_tools import FFmpegMissingError, assert_ffmpeg_tools, ffmpeg_loudnorm_measure, ffprobe_video
from manifest_checks import (
    beat_duration_stats,
    diversity_stats,
    load_manifest,
    safe_area_check,
    storyboard_stats,
    text_stats,
)
from patcher import generate_patch_suggestions
from scoring import compute_score, gate_checks

console = Console()


class EvaluateArgs(BaseModel):
    video: str
    manifest: str
    expected_text: Optional[str] = None
    out: str
    quality: str = "src/config/quality.json"
    target: Optional[float] = None


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sample_visual_metrics(video_path: str) -> Dict[str, Any]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    sample_step_black = max(1, int(round(fps)))
    sample_step_flicker = max(1, int(round(fps / 2)))

    black_count = 0
    black_total = 0

    sampled_luma: List[float] = []

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        luma = float(np.mean(gray))

        if frame_idx % sample_step_black == 0:
            black_total += 1
            if luma < 5.0:
                black_count += 1

        if frame_idx % sample_step_flicker == 0:
            sampled_luma.append(luma)

        frame_idx += 1

    cap.release()

    if len(sampled_luma) > 1:
        diffs = np.abs(np.diff(np.array(sampled_luma, dtype=np.float32)))
        p95_delta = float(np.percentile(diffs, 95))
    else:
        p95_delta = 0.0

    return {
        "blackFrameRatio": float(black_count / black_total) if black_total else 0.0,
        "blackSamples": black_total,
        "blackFrames": black_count,
        "p95DeltaLuma": p95_delta,
        "sampledLumaFrames": len(sampled_luma),
    }


def _maybe_asr(video_path: str, expected_text_path: Optional[str]) -> Dict[str, Any]:
    if not expected_text_path:
        return {"skipped": True, "reason": "expected_text not provided"}

    expected_path = Path(expected_text_path)
    if not expected_path.exists():
        return {"skipped": True, "reason": f"expected_text not found: {expected_text_path}"}

    expected_text = expected_path.read_text(encoding="utf-8").strip()
    if not expected_text:
        return {"skipped": True, "reason": "expected_text is empty"}

    try:
        import whisper  # type: ignore
    except Exception:
        return {"skipped": True, "reason": "openai-whisper not installed"}

    try:
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        transcript = (result.get("text") or "").strip()
        return {
            "skipped": False,
            "model": "whisper-base",
            "cer": float(cer(expected_text, transcript)),
            "transcript": transcript,
        }
    except Exception as exc:
        return {"skipped": True, "reason": f"whisper failed: {exc}"}


def _build_manifest_metrics(manifest: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
    beats = manifest.get("beats") or []
    text_blocks = manifest.get("textBlocks") or []

    rhythm_cfg = quality.get("rhythm", {})
    limits = quality.get("limits", {})

    beat_stats = beat_duration_stats(
        beats,
        min_sec=float(rhythm_cfg.get("minBeatSec", 2.5)),
        max_sec=float(rhythm_cfg.get("maxBeatSec", 4.0)),
    )

    safe = safe_area_check(text_blocks, quality.get("safeArea"))
    diversity = diversity_stats(manifest)
    text = text_stats(manifest, limits)
    storyboard = storyboard_stats(manifest)

    return {
        "safe": safe,
        "beat": beat_stats,
        "diversity": diversity,
        "text": text,
        "storyboard": storyboard,
    }


def _parse_args() -> EvaluateArgs:
    parser = argparse.ArgumentParser(description="Evaluate rendered video quality")
    parser.add_argument("--video", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected_text", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--quality", default="src/config/quality.json")
    parser.add_argument("--target", type=float, default=None)
    ns = parser.parse_args()

    return EvaluateArgs(
        video=ns.video,
        manifest=ns.manifest,
        expected_text=ns.expected_text,
        out=ns.out,
        quality=ns.quality,
        target=ns.target,
    )


def main() -> int:
    args = _parse_args()

    quality = _load_json(args.quality)
    target = float(args.target if args.target is not None else quality.get("targetScore", 60))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    try:
        assert_ffmpeg_tools()
    except FFmpegMissingError as exc:
        empty_breakdown = {
            "rhythm": 0.0,
            "text": 0.0,
            "motion_consistency": 0.0,
            "audio": 0.0,
            "visual_stability": 0.0,
        }
        report = {
            "gate": {
                "pass": False,
                "checks": {
                    "ffmpeg_tools": False,
                    "resolution": False,
                    "fps": False,
                    "duration": False,
                    "black_frame_ratio": False,
                    "audio_true_peak": False,
                    "audio_lufs": False,
                    "safe_area": False,
                },
            },
            "score": {"total": 0, "breakdown": empty_breakdown},
            "metrics": {
                "video": {},
                "audio": {},
                "manifest": {},
                "asr": {"skipped": True, "reason": "evaluation prerequisites missing"},
                "error": str(exc),
            },
            "suggestions": {"patch_suggestions": []},
            "exit_code": 3,
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        console.print(f"[red]{exc}[/red]")
        return 3

    video_probe = ffprobe_video(args.video)
    loudness = ffmpeg_loudnorm_measure(args.video)
    visual = _sample_visual_metrics(args.video)

    manifest = load_manifest(args.manifest)
    manifest_metrics = _build_manifest_metrics(manifest, quality)

    video_metrics = {
        "width": int(video_probe.get("width", 0)),
        "height": int(video_probe.get("height", 0)),
        "fps": float(video_probe.get("fps", 0.0)),
        "durationSec": float(video_probe.get("duration", 0.0)),
        "nbFrames": int(video_probe.get("nb_frames", 0)),
        **visual,
    }

    audio_metrics = loudness

    gate = gate_checks(video_metrics, audio_metrics, manifest_metrics, quality)
    score = compute_score(video_metrics, audio_metrics, manifest_metrics, quality)

    asr_metrics = _maybe_asr(args.video, args.expected_text)

    report: Dict[str, Any] = {
        "gate": gate,
        "score": score,
        "metrics": {
            "video": video_metrics,
            "audio": audio_metrics,
            "manifest": manifest_metrics,
            "asr": asr_metrics,
        },
    }

    manifest_spec_path = manifest.get("specPath")
    spec: Dict[str, Any] = {}
    if manifest_spec_path:
        candidate = Path(manifest_spec_path)
        if candidate.exists():
            spec = _load_json(str(candidate))

    report["suggestions"] = {
        "patch_suggestions": generate_patch_suggestions(
            report,
            quality,
            spec,
            quality_path=args.quality,
            spec_path=manifest_spec_path or "src/specs/skill.timeline.json",
        ),
    }

    if gate["pass"] and float(score["total"]) >= target:
        exit_code = 0
    elif gate["pass"]:
        exit_code = 2
    else:
        exit_code = 3

    report["exit_code"] = exit_code

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    console.print(
        f"gate.pass={gate['pass']} score={score['total']} target={target} exit_code={exit_code}"
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
