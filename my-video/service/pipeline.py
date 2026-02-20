from __future__ import annotations

import json
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from .prompts import SPEC_SYSTEM_PROMPT, build_spec_user_prompt
from .providers import build_llm_client, build_tts_client
from .settings import ServiceSettings


class PipelineRequest(BaseModel):
    topic: str = "What is a vector database?"
    audience: str = "General audience"
    tone: str = "Easy, friendly, fast-paced"
    language: str = "en"
    duration_sec: int = 60
    ratio: Literal["16:9", "9:16"] = "16:9"
    mode: Literal["render_only", "render_and_eval", "optimize"] = "optimize"
    target_score: float = 70.0
    max_iter: int = 8
    use_llm: bool = True
    enable_tts: bool = False
    quality_path: Optional[str] = None
    spec: Optional[Dict[str, Any]] = None
    expected_script: Optional[str] = None


class PipelineResult(BaseModel):
    status: Literal["completed", "failed"]
    exit_code: int = 0
    error: str = ""
    video_path: Optional[str] = None
    manifest_path: Optional[str] = None
    report_path: Optional[str] = None
    spec_path: Optional[str] = None
    expected_script_path: Optional[str] = None
    score_total: Optional[float] = None
    gate_pass: Optional[bool] = None
    traceback: Optional[str] = None


def _ratio_to_resolution(ratio: str) -> tuple[int, int]:
    if ratio == "9:16":
        return 1080, 1920
    return 1920, 1080


def _default_quality_for_ratio(settings: ServiceSettings, ratio: str) -> Path:
    if ratio == "16:9":
        return settings.abs_path(settings.runtime.quality_169_path)
    return settings.abs_path(settings.runtime.default_quality_path)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sanitize_beats(beats: list[Dict[str, Any]], duration_sec: int) -> list[Dict[str, Any]]:
    cleaned: list[Dict[str, Any]] = []
    for idx, beat in enumerate(beats):
        if not isinstance(beat, dict):
            continue
        t0 = float(beat.get("t0", idx * 4))
        t1 = float(beat.get("t1", t0 + 4))
        intent = str(beat.get("intent", "definition_card")).strip() or "definition_card"
        line = str(beat.get("line", "")).strip()
        if not line:
            continue
        cleaned.append(
            {
                "id": str(beat.get("id", f"b{idx + 1:02d}")),
                "t0": round(max(0.0, t0), 3),
                "t1": round(min(float(duration_sec), max(t0 + 0.5, t1)), 3),
                "intent": intent,
                "line": line,
            }
        )
    cleaned = sorted(cleaned, key=lambda b: float(b.get("t0", 0.0)))
    return cleaned


def _build_spec_from_default(settings: ServiceSettings, req: PipelineRequest) -> Dict[str, Any]:
    base = _load_json(settings.abs_path(settings.runtime.default_spec_path))
    width, height = _ratio_to_resolution(req.ratio)
    base_meta = base.get("meta") if isinstance(base.get("meta"), dict) else {}
    base_meta.update(
        {
            "title": req.topic,
            "width": width,
            "height": height,
            "fps": 30,
            "duration_sec": req.duration_sec,
            "durationSec": req.duration_sec,
            "style_preset": "apple_keynote_169" if req.ratio == "16:9" else "xhs_minimal_tech",
        }
    )
    base["meta"] = base_meta
    beats = base.get("beats")
    if isinstance(beats, list):
        base["beats"] = _sanitize_beats(beats, req.duration_sec)
    return base


def _build_spec_from_llm(
    settings: ServiceSettings, req: PipelineRequest
) -> tuple[Dict[str, Any], str]:
    llm = build_llm_client(settings.llm)
    if not llm or not llm.is_enabled():
        fallback = _build_spec_from_default(settings, req)
        script = req.expected_script or ""
        return fallback, script

    payload = llm.chat_json(
        SPEC_SYSTEM_PROMPT,
        build_spec_user_prompt(
            topic=req.topic,
            audience=req.audience,
            tone=req.tone,
            duration_sec=req.duration_sec,
            ratio=req.ratio,
            language=req.language,
        ),
    )
    beats = payload.get("beats", [])
    script = str(payload.get("script", "")).strip()
    spec = _build_spec_from_default(settings, req)
    if isinstance(beats, list) and beats:
        spec["beats"] = _sanitize_beats(beats, req.duration_sec)
    return spec, script


def _apply_tts_if_enabled(
    settings: ServiceSettings,
    req: PipelineRequest,
    job_id: str,
    script_text: str,
    spec: Dict[str, Any],
) -> Dict[str, Any]:
    if not req.enable_tts:
        return spec
    tts = build_tts_client(settings.tts)
    if not tts or not tts.is_enabled():
        return spec
    if not script_text.strip():
        return spec
    out_file = settings.abs_path(settings.runtime.public_tts_dir) / f"{job_id}.wav"
    tts.synthesize(script_text, out_file)
    audio = spec.get("audio") if isinstance(spec.get("audio"), dict) else {}
    audio["src"] = f"tts/{job_id}.wav"
    audio["startSec"] = 0
    spec["audio"] = audio
    return spec


def _run_cmd(
    cmd: list[str], cwd: Path, log_path: Path, timeout_sec: int, allow_nonzero: bool = False
) -> int:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"$ {' '.join(cmd)}\n")
        if proc.stdout:
            f.write(proc.stdout)
            if not proc.stdout.endswith("\n"):
                f.write("\n")
        if proc.stderr:
            f.write(proc.stderr)
            if not proc.stderr.endswith("\n"):
                f.write("\n")
        f.write(f"[exit_code={proc.returncode}]\n\n")
    if proc.returncode != 0 and not allow_nonzero:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}")
    return proc.returncode


def run_pipeline(settings: ServiceSettings, job_id: str, req: PipelineRequest) -> PipelineResult:
    root = settings.repo_root()
    data_dir = settings.abs_path(settings.runtime.data_dir)
    job_dir = data_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "run.log"

    try:
        quality_path = (
            settings.abs_path(req.quality_path)
            if req.quality_path
            else _default_quality_for_ratio(settings, req.ratio)
        )
        if not quality_path.exists():
            raise FileNotFoundError(f"quality config not found: {quality_path}")

        script_text = (req.expected_script or "").strip()
        if req.spec is not None:
            spec = dict(req.spec)
        elif req.use_llm:
            spec, llm_script = _build_spec_from_llm(settings, req)
            if llm_script and not script_text:
                script_text = llm_script
        else:
            spec = _build_spec_from_default(settings, req)

        if req.spec is not None and not script_text:
            script_text = ""

        spec = _apply_tts_if_enabled(settings, req, job_id, script_text, spec)
        spec_path = job_dir / "spec.json"
        _save_json(spec_path, spec)

        expected_script_path: Optional[Path] = None
        if script_text:
            expected_script_path = job_dir / "expected_script.txt"
            _save_text(expected_script_path, script_text + "\n")
        else:
            default_script = settings.abs_path(settings.runtime.expected_script_default)
            if default_script.exists():
                expected_script_path = default_script

        video_path = job_dir / "video.mp4"
        manifest_path = job_dir / "manifest.json"
        report_path = job_dir / "report.json"

        if req.mode in {"render_only", "render_and_eval"}:
            cmd = [
                "node",
                "scripts/render_from_spec.ts",
                "--spec",
                str(spec_path),
                "--out",
                str(video_path),
                "--manifest",
                str(manifest_path),
                "--quality",
                str(quality_path),
            ]
            _run_cmd(
                cmd, root, log_path, settings.runtime.command_timeout_sec, allow_nonzero=False
            )
            if req.mode == "render_and_eval":
                eval_cmd = [
                    "python3",
                    "qa/evaluate_video.py",
                    "--video",
                    str(video_path),
                    "--manifest",
                    str(manifest_path),
                    "--quality",
                    str(quality_path),
                    "--target",
                    str(req.target_score),
                    "--out",
                    str(report_path),
                ]
                if expected_script_path and expected_script_path.exists():
                    eval_cmd.extend(["--expected_text", str(expected_script_path)])
                _run_cmd(
                    eval_cmd,
                    root,
                    log_path,
                    settings.runtime.command_timeout_sec,
                    allow_nonzero=True,
                )
        else:
            optimize_cmd = [
                "python3",
                "qa/optimize_loop.py",
                "--spec",
                str(spec_path),
                "--target",
                str(req.target_score),
                "--max_iter",
                str(req.max_iter),
                "--quality",
                str(quality_path),
                "--video",
                str(video_path),
                "--manifest",
                str(manifest_path),
                "--report",
                str(report_path),
            ]
            if expected_script_path and expected_script_path.exists():
                optimize_cmd.extend(["--expected_text", str(expected_script_path)])
            _run_cmd(
                optimize_cmd,
                root,
                log_path,
                settings.runtime.command_timeout_sec,
                allow_nonzero=True,
            )

        score_total: Optional[float] = None
        gate_pass: Optional[bool] = None
        exit_code = 0
        if report_path.exists():
            report = _load_json(report_path)
            score_total = float(report.get("score", {}).get("total", 0.0))
            gate_pass = bool(report.get("gate", {}).get("pass", False))
            exit_code = int(report.get("exit_code", 0) or 0)

        return PipelineResult(
            status="completed",
            exit_code=exit_code,
            video_path=str(video_path),
            manifest_path=str(manifest_path if manifest_path.exists() else ""),
            report_path=str(report_path if report_path.exists() else ""),
            spec_path=str(spec_path),
            expected_script_path=str(expected_script_path) if expected_script_path else "",
            score_total=score_total,
            gate_pass=gate_pass,
        )
    except Exception as exc:  # pylint: disable=broad-except
        with (job_dir / "error.txt").open("w", encoding="utf-8") as f:
            f.write(str(exc))
            f.write("\n\n")
            f.write(traceback.format_exc())
        return PipelineResult(
            status="failed",
            exit_code=1,
            error=str(exc),
            traceback=traceback.format_exc(),
            spec_path=str(job_dir / "spec.json"),
        )

