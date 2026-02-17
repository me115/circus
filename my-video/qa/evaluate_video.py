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
    frame_bounds_check,
    layout_stats,
    load_manifest,
    no_element_gap_stats,
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
    sample_step_element = max(1, int(round(fps / 2)))
    element_edge_threshold = 0.0012
    element_laplacian_threshold = 10.0

    black_count = 0
    black_total = 0

    sampled_luma: List[float] = []
    no_element_run = 0
    max_no_element_run = 0
    element_samples = 0
    foreground_coverages: List[float] = []
    foreground_center_x: List[float] = []
    foreground_center_y: List[float] = []
    foreground_lower_half: List[float] = []
    foreground_bbox_heights: List[float] = []
    foreground_bbox_widths: List[float] = []
    foreground_bbox_aspects: List[float] = []
    strip_flags: List[float] = []

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

        if frame_idx % sample_step_element == 0:
            edges = cv2.Canny(gray, 70, 140)
            edge_ratio = float(np.mean(edges > 0))
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            element_samples += 1
            if edge_ratio < element_edge_threshold and laplacian_var < element_laplacian_threshold:
                no_element_run += 1
            else:
                no_element_run = 0
            max_no_element_run = max(max_no_element_run, no_element_run)

            grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            grad_mag = cv2.magnitude(grad_x, grad_y)
            fg_mask = (grad_mag > 30.0).astype(np.uint8)
            fg_mask = cv2.dilate(fg_mask, np.ones((3, 3), dtype=np.uint8), iterations=1)

            coverage = float(np.mean(fg_mask))
            foreground_coverages.append(coverage)

            ys, xs = np.where(fg_mask > 0)
            if len(xs) > 0:
                min_x = float(np.min(xs))
                max_x = float(np.max(xs))
                min_y = float(np.min(ys))
                max_y = float(np.max(ys))
                bbox_w = (max_x - min_x + 1.0) / max(gray.shape[1], 1)
                bbox_h = (max_y - min_y + 1.0) / max(gray.shape[0], 1)
                bbox_aspect = bbox_w / max(bbox_h, 1e-6)
                foreground_bbox_widths.append(float(bbox_w))
                foreground_bbox_heights.append(float(bbox_h))
                foreground_bbox_aspects.append(float(bbox_aspect))
                strip_flags.append(1.0 if (bbox_h < 0.22 and bbox_aspect > 4.8) else 0.0)
                foreground_center_x.append(float(np.mean(xs) / gray.shape[1]))
                foreground_center_y.append(float(np.mean(ys) / gray.shape[0]))
                foreground_lower_half.append(float(np.mean(ys >= gray.shape[0] * 0.5)))

        frame_idx += 1

    cap.release()

    if len(sampled_luma) > 1:
        diffs = np.abs(np.diff(np.array(sampled_luma, dtype=np.float32)))
        p95_delta = float(np.percentile(diffs, 95))
    else:
        p95_delta = 0.0

    fg_cov_mean = float(np.mean(foreground_coverages)) if foreground_coverages else 0.0
    fg_cov_p25 = (
        float(np.percentile(np.array(foreground_coverages, dtype=np.float32), 25))
        if foreground_coverages
        else 0.0
    )
    fg_cov_p50 = (
        float(np.percentile(np.array(foreground_coverages, dtype=np.float32), 50))
        if foreground_coverages
        else 0.0
    )
    fg_center_x_mean = float(np.mean(foreground_center_x)) if foreground_center_x else 0.5
    fg_center_y_mean = float(np.mean(foreground_center_y)) if foreground_center_y else 0.5
    fg_lower_half_mean = float(np.mean(foreground_lower_half)) if foreground_lower_half else 0.0
    fg_lower_half_p25 = (
        float(np.percentile(np.array(foreground_lower_half, dtype=np.float32), 25))
        if foreground_lower_half
        else 0.0
    )
    fg_bbox_h_mean = float(np.mean(foreground_bbox_heights)) if foreground_bbox_heights else 0.0
    fg_bbox_h_p25 = (
        float(np.percentile(np.array(foreground_bbox_heights, dtype=np.float32), 25))
        if foreground_bbox_heights
        else 0.0
    )
    fg_bbox_w_mean = float(np.mean(foreground_bbox_widths)) if foreground_bbox_widths else 0.0
    fg_bbox_w_p25 = (
        float(np.percentile(np.array(foreground_bbox_widths, dtype=np.float32), 25))
        if foreground_bbox_widths
        else 0.0
    )
    fg_bbox_aspect_p75 = (
        float(np.percentile(np.array(foreground_bbox_aspects, dtype=np.float32), 75))
        if foreground_bbox_aspects
        else 0.0
    )
    fg_strip_rate = float(np.mean(strip_flags)) if strip_flags else 0.0

    return {
        "blackFrameRatio": float(black_count / black_total) if black_total else 0.0,
        "blackSamples": black_total,
        "blackFrames": black_count,
        "p95DeltaLuma": p95_delta,
        "sampledLumaFrames": len(sampled_luma),
        "elementSamples": element_samples,
        "maxNoElementGapSecVideo": float(max_no_element_run * sample_step_element / max(fps, 1.0)),
        "foregroundCoverageMean": fg_cov_mean,
        "foregroundCoverageP25": fg_cov_p25,
        "foregroundCoverageP50": fg_cov_p50,
        "foregroundCenterXPctMean": fg_center_x_mean,
        "foregroundCenterYPctMean": fg_center_y_mean,
        "foregroundCenterXDeviation": abs(fg_center_x_mean - 0.5),
        "foregroundLowerHalfRatioMean": fg_lower_half_mean,
        "foregroundLowerHalfRatioP25": fg_lower_half_p25,
        "foregroundBBoxHeightMean": fg_bbox_h_mean,
        "foregroundBBoxHeightP25": fg_bbox_h_p25,
        "foregroundBBoxWidthMean": fg_bbox_w_mean,
        "foregroundBBoxWidthP25": fg_bbox_w_p25,
        "foregroundBBoxAspectP75": fg_bbox_aspect_p75,
        "foregroundStripRate": fg_strip_rate,
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
    bounds = frame_bounds_check(text_blocks)
    diversity = diversity_stats(manifest)
    text = text_stats(manifest, limits)
    storyboard = storyboard_stats(manifest)
    layout = layout_stats(manifest, limits)
    no_element_gap = no_element_gap_stats(
        manifest,
        max_gap_sec=float(limits.get("maxNoElementGapSec", 3.0)),
    )

    return {
        "safe": safe,
        "bounds": bounds,
        "beat": beat_stats,
        "diversity": diversity,
        "text": text,
        "storyboard": storyboard,
        "layout": layout,
        "no_element_gap": no_element_gap,
    }


def _parse_args() -> EvaluateArgs:
    parser = argparse.ArgumentParser(description="Evaluate rendered video quality")
    parser.add_argument("--video", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected_text", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--quality", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--target", type=float, default=None)
    ns = parser.parse_args()
    quality = ns.quality or ns.config or "src/config/quality.json"

    return EvaluateArgs(
        video=ns.video,
        manifest=ns.manifest,
        expected_text=ns.expected_text,
        out=ns.out,
        quality=quality,
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
            "composition": 0.0,
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
                    "layout_bounds": False,
                    "safe_area": False,
                    "no_element_gap": False,
                    "lower_half_coverage": False,
                    "foreground_lower_half_p25": False,
                    "foreground_coverage": False,
                    "foreground_bbox_height": False,
                    "foreground_strip_rate": False,
                    "foreground_bbox_aspect": False,
                    "foreground_balance_x": False,
                    "alignment": False,
                    "sparse_beat_rate": False,
                    "react_variant_count": False,
                    "react_variant_mix": False,
                    "react_variant_run": False,
                    "react_variant_adjacent_repeat": False,
                    "scene_signature_count": False,
                    "scene_signature_mix": False,
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
    raw_total = float(score.get("total", 0.0))
    score["raw_total"] = round(raw_total, 2)
    score["total"] = round(raw_total, 2) if gate["pass"] else 0.0
    score["gate_penalty_applied"] = not gate["pass"]

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
