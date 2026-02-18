from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np


def _ssim_gray(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_a = cv2.GaussianBlur(a, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(b, (11, 11), 1.5)
    mu_a2 = mu_a * mu_a
    mu_b2 = mu_b * mu_b
    mu_ab = mu_a * mu_b
    sigma_a2 = cv2.GaussianBlur(a * a, (11, 11), 1.5) - mu_a2
    sigma_b2 = cv2.GaussianBlur(b * b, (11, 11), 1.5) - mu_b2
    sigma_ab = cv2.GaussianBlur(a * b, (11, 11), 1.5) - mu_ab
    numerator = (2 * mu_ab + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a2 + mu_b2 + c1) * (sigma_a2 + sigma_b2 + c2)
    ssim_map = numerator / np.maximum(denominator, 1e-6)
    return float(np.clip(np.mean(ssim_map), 0.0, 1.0))


def _extract_frames(video_path: str, times_sec: List[float]) -> Dict[float, np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {}
    duration = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1.0))
    result: Dict[float, np.ndarray] = {}
    for t in times_sec:
        safe_t = max(0.0, min(float(t), max(0.0, duration - 1e-3)))
        cap.set(cv2.CAP_PROP_POS_MSEC, safe_t * 1000.0)
        ok, frame = cap.read()
        if ok and frame is not None:
            result[t] = frame
    cap.release()
    return result


def _pick_keyframe_times(manifest: Dict[str, Any], max_frames: int = 12) -> List[float]:
    meta = manifest.get("meta", {}) if isinstance(manifest, dict) else {}
    duration = float(meta.get("durationSec", 60.0) or 60.0)
    beats = manifest.get("beats", []) if isinstance(manifest, dict) else []
    candidates: List[float] = [0.0, max(0.0, duration * 0.5), max(0.0, duration - 0.4)]
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        t0 = float(beat.get("t0", 0.0) or 0.0)
        t1 = float(beat.get("t1", t0) or t0)
        if t1 <= t0:
            continue
        candidates.append(t0)
        candidates.append((t0 + t1) * 0.5)
    deduped = sorted({round(max(0.0, min(duration, t)), 2) for t in candidates})
    if len(deduped) <= max_frames:
        return deduped
    step = len(deduped) / max_frames
    return [deduped[min(len(deduped) - 1, int(i * step))] for i in range(max_frames)]


def export_keyframes(
    video_path: str,
    manifest: Dict[str, Any],
    out_dir: str,
    max_frames: int = 12,
) -> List[Dict[str, Any]]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    times = _pick_keyframe_times(manifest, max_frames=max_frames)
    frames = _extract_frames(video_path, times)
    exported: List[Dict[str, Any]] = []
    for idx, t in enumerate(times):
        frame = frames.get(t)
        if frame is None:
            continue
        file_path = out_path / f"kf_{idx:02d}_{int(t * 1000):05d}ms.jpg"
        cv2.imwrite(str(file_path), frame)
        exported.append({"timeSec": float(t), "path": str(file_path)})
    return exported


def compare_keyframes(
    previous_keyframes: List[Dict[str, Any]],
    current_keyframes: List[Dict[str, Any]],
    ssim_fail_threshold: float = 0.7,
) -> Dict[str, Any]:
    if not previous_keyframes or not current_keyframes:
        return {
            "compared_count": 0,
            "mean_ssim": 1.0,
            "regression_count": 0,
            "regressions": [],
            "ssim_fail_threshold": ssim_fail_threshold,
        }

    prev_paths = [item.get("path") for item in previous_keyframes if item.get("path")]
    curr_paths = [item.get("path") for item in current_keyframes if item.get("path")]
    pair_count = min(len(prev_paths), len(curr_paths))
    if pair_count <= 0:
        return {
            "compared_count": 0,
            "mean_ssim": 1.0,
            "regression_count": 0,
            "regressions": [],
            "ssim_fail_threshold": ssim_fail_threshold,
        }

    regressions: List[Dict[str, Any]] = []
    ssim_values: List[float] = []
    for idx in range(pair_count):
        prev_img = cv2.imread(str(prev_paths[idx]))
        curr_img = cv2.imread(str(curr_paths[idx]))
        if prev_img is None or curr_img is None:
            continue
        prev_gray = cv2.cvtColor(prev_img, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_img, cv2.COLOR_BGR2GRAY)
        score = _ssim_gray(prev_gray, curr_gray)
        ssim_values.append(score)
        if score < ssim_fail_threshold:
            regressions.append(
                {
                    "index": idx,
                    "prevPath": str(prev_paths[idx]),
                    "currPath": str(curr_paths[idx]),
                    "ssim": round(score, 4),
                }
            )

    mean_ssim = float(np.mean(ssim_values)) if ssim_values else 1.0
    return {
        "compared_count": len(ssim_values),
        "mean_ssim": round(mean_ssim, 4),
        "regression_count": len(regressions),
        "regressions": regressions,
        "ssim_fail_threshold": ssim_fail_threshold,
    }


def _collect_failure_beats(report: Dict[str, Any]) -> Dict[str, List[str]]:
    metrics = report.get("metrics", {}) if isinstance(report, dict) else {}
    manifest = metrics.get("manifest", {}) if isinstance(metrics, dict) else {}
    density = manifest.get("density_metric", {}) if isinstance(manifest, dict) else {}
    layout = manifest.get("layout", {}) if isinstance(manifest, dict) else {}
    video = metrics.get("video", {}) if isinstance(metrics, dict) else {}

    reasons_by_beat: Dict[str, List[str]] = {}

    def add_reasons(beat_ids: List[Any], reason: str) -> None:
        for raw in beat_ids or []:
            beat_id = str(raw).strip()
            if not beat_id:
                continue
            reasons_by_beat.setdefault(beat_id, [])
            if reason not in reasons_by_beat[beat_id]:
                reasons_by_beat[beat_id].append(reason)

    add_reasons(density.get("bad_line_break_beats", []), "line-break")
    add_reasons(density.get("overflow_beats", []), "density-overflow")
    add_reasons(layout.get("low_text_fill_beat_ids", []), "small-text-ratio")
    add_reasons(layout.get("sparse_beat_ids", []), "sparse-layout")
    add_reasons(layout.get("overlap_beat_ids", []), "overlap")
    add_reasons(layout.get("severe_overlap_beat_ids", []), "severe-overlap")
    add_reasons(layout.get("wrap_risk_beat_ids", []), "wrap-risk")
    add_reasons(video.get("beatLowInfoBeatIds", []), "low-info")
    return reasons_by_beat


def create_failure_atlas(
    video_path: str,
    manifest: Dict[str, Any],
    report: Dict[str, Any],
    out_path: str,
    max_tiles: int = 12,
) -> Dict[str, Any]:
    reasons_by_beat = _collect_failure_beats(report)
    beats = manifest.get("beats", []) if isinstance(manifest, dict) else []
    beat_time_map: Dict[str, float] = {}
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("id") or "").strip()
        if not beat_id:
            continue
        t0 = float(beat.get("t0", 0.0) or 0.0)
        t1 = float(beat.get("t1", t0) or t0)
        beat_time_map[beat_id] = (t0 + t1) * 0.5 if t1 >= t0 else t0

    targets: List[Tuple[str, float, List[str]]] = []
    for beat_id, reasons in reasons_by_beat.items():
        if beat_id not in beat_time_map:
            continue
        targets.append((beat_id, beat_time_map[beat_id], reasons))
    targets.sort(key=lambda item: item[1])
    targets = targets[:max_tiles]

    if not targets:
        return {
            "generated": False,
            "tile_count": 0,
            "path": out_path,
            "reasonsByBeat": reasons_by_beat,
        }

    times = [item[1] for item in targets]
    frames = _extract_frames(video_path, times)
    tiles: List[np.ndarray] = []
    for beat_id, t, reasons in targets:
        frame = frames.get(t)
        if frame is None:
            continue
        h, w = frame.shape[:2]
        target_w = 480
        target_h = int(round(h * (target_w / max(w, 1))))
        thumb = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
        panel = np.zeros((target_h + 64, target_w, 3), dtype=np.uint8)
        panel[:target_h, :, :] = thumb
        title = f"{beat_id}  t={t:.1f}s"
        desc = ",".join(reasons[:3])
        cv2.putText(panel, title, (10, target_h + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
        cv2.putText(panel, desc, (10, target_h + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 220, 255), 1)
        tiles.append(panel)

    if not tiles:
        return {
            "generated": False,
            "tile_count": 0,
            "path": out_path,
            "reasonsByBeat": reasons_by_beat,
        }

    cols = min(3, len(tiles))
    rows = int(math.ceil(len(tiles) / cols))
    tile_h = max(tile.shape[0] for tile in tiles)
    tile_w = max(tile.shape[1] for tile in tiles)
    canvas = np.zeros((rows * tile_h, cols * tile_w, 3), dtype=np.uint8)
    for idx, tile in enumerate(tiles):
        r = idx // cols
        c = idx % cols
        y0 = r * tile_h
        x0 = c * tile_w
        canvas[y0 : y0 + tile.shape[0], x0 : x0 + tile.shape[1], :] = tile

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_file), canvas)
    return {
        "generated": True,
        "tile_count": len(tiles),
        "path": str(out_file),
        "reasonsByBeat": reasons_by_beat,
    }
