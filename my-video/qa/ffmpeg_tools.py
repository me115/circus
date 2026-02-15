from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple


class FFmpegMissingError(RuntimeError):
    pass


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise FFmpegMissingError(
            f"{name} is required but was not found in PATH. "
            "Install ffmpeg/ffprobe first."
        )


def assert_ffmpeg_tools() -> None:
    _require_binary("ffmpeg")
    _require_binary("ffprobe")


def _parse_fps(rate: str) -> float:
    if not rate:
        return 0.0
    if "/" in rate:
        n, d = rate.split("/", 1)
        try:
            nn = float(n)
            dd = float(d)
            return nn / dd if dd != 0 else 0.0
        except ValueError:
            return 0.0
    try:
        return float(rate)
    except ValueError:
        return 0.0


def ffprobe_video(video_path: str) -> Dict[str, Any]:
    _require_binary("ffprobe")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration",
        "-show_entries",
        "format=duration",
        video_path,
    ]
    code, stdout, stderr = run_cmd(cmd)
    if code != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.strip()}")

    payload = json.loads(stdout)
    stream = (payload.get("streams") or [{}])[0]
    fmt = payload.get("format") or {}

    width = int(float(stream.get("width", 0) or 0))
    height = int(float(stream.get("height", 0) or 0))
    fps = _parse_fps(str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0"))
    duration = float(stream.get("duration") or fmt.get("duration") or 0.0)

    raw_nb_frames = stream.get("nb_frames")
    try:
        nb_frames = int(raw_nb_frames)
    except (TypeError, ValueError):
        nb_frames = int(round(duration * fps)) if duration > 0 and fps > 0 else 0

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "nb_frames": nb_frames,
    }


def _parse_loudnorm_json(stderr: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{\s*\"input_i\".*?\}", stderr, flags=re.S)
    if not match:
        return None

    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    def _to_float(key: str) -> Optional[float]:
        val = raw.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    return {
        "input_i_lufs": _to_float("input_i"),
        "input_tp_db": _to_float("input_tp"),
        "input_lra": _to_float("input_lra"),
        "input_thresh": _to_float("input_thresh"),
        "target_offset": _to_float("target_offset"),
        "source": "loudnorm",
    }


def _parse_ebur128(stderr: str) -> Dict[str, Any]:
    i_matches = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", stderr)
    peak_matches = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", stderr)
    lra_matches = re.findall(r"LRA:\s*(-?\d+(?:\.\d+)?)\s*LU", stderr)

    integrated = float(i_matches[-1]) if i_matches else None
    peak = float(peak_matches[-1]) if peak_matches else None
    lra = float(lra_matches[-1]) if lra_matches else None

    return {
        "input_i_lufs": integrated,
        "input_tp_db": peak,
        "input_lra": lra,
        "source": "ebur128",
    }


def ffmpeg_loudnorm_measure(video_path: str) -> Dict[str, Any]:
    _require_binary("ffmpeg")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        video_path,
        "-af",
        "loudnorm=I=-16:TP=-1.0:LRA=11:print_format=json",
        "-f",
        "null",
        "-",
    ]
    code, _stdout, stderr = run_cmd(cmd)
    if code == 0:
        parsed = _parse_loudnorm_json(stderr)
        if parsed is not None:
            return parsed

    fallback_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        video_path,
        "-filter_complex",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    fb_code, _fb_out, fb_err = run_cmd(fallback_cmd)
    if fb_code != 0:
        raise RuntimeError(f"ffmpeg loudness measure failed: {fb_err.strip()}")

    return _parse_ebur128(fb_err)
