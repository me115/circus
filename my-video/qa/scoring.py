from __future__ import annotations

from typing import Any, Dict


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def gate_checks(
    video_metrics: Dict[str, Any],
    audio_metrics: Dict[str, Any],
    manifest_metrics: Dict[str, Any],
    quality: Dict[str, Any],
) -> Dict[str, Any]:
    video_cfg = quality.get("video", {})
    audio_cfg = quality.get("audio", {})

    width_ok = int(video_metrics.get("width", 0)) == int(video_cfg.get("width", 1920))
    height_ok = int(video_metrics.get("height", 0)) == int(video_cfg.get("height", 1080))
    fps_ok = abs(float(video_metrics.get("fps", 0.0)) - float(video_cfg.get("fps", 30.0))) <= 0.5
    duration_ok = (
        abs(float(video_metrics.get("durationSec", 0.0)) - float(video_cfg.get("durationSec", 60.0)))
        <= float(video_cfg.get("durationTolSec", 1.0))
    )
    black_ok = float(video_metrics.get("blackFrameRatio", 1.0)) < 0.01

    tp = audio_metrics.get("input_tp_db")
    lufs = audio_metrics.get("input_i_lufs")

    tp_ok = tp is not None and float(tp) <= float(audio_cfg.get("maxTruePeakDbTP", -1.0))
    lufs_ok = (
        lufs is not None
        and float(audio_cfg.get("minLUFS", -18.0))
        <= float(lufs)
        <= float(audio_cfg.get("maxLUFS", -14.0))
    )

    safe_ok = int(manifest_metrics.get("safe", {}).get("violations", 1)) == 0

    checks = {
        "resolution": bool(width_ok and height_ok),
        "fps": bool(fps_ok),
        "duration": bool(duration_ok),
        "black_frame_ratio": bool(black_ok),
        "audio_true_peak": bool(tp_ok),
        "audio_lufs": bool(lufs_ok),
        "safe_area": bool(safe_ok),
    }

    return {
        "pass": all(checks.values()),
        "checks": checks,
    }


def _score_rhythm(manifest_metrics: Dict[str, Any], quality: Dict[str, Any]) -> float:
    rhythm_cfg = quality.get("rhythm", {})
    stats = manifest_metrics.get("beat", {})
    pct = float(stats.get("pct_in_range", 0.0))
    std = float(stats.get("std", 99.0))
    mean = float(stats.get("mean", 0.0))
    target = float(rhythm_cfg.get("targetBeatSec", 3.0))

    std_component = 1.0 - min(std / 1.2, 1.0)
    mean_component = 1.0 - min(abs(mean - target) / max(target, 0.001), 1.0)

    return _clamp(100.0 * (0.65 * pct + 0.2 * std_component + 0.15 * mean_component))


def _score_text(manifest_metrics: Dict[str, Any]) -> float:
    text = manifest_metrics.get("text", {})
    safe = manifest_metrics.get("safe", {})

    char_hit = float(text.get("char_hit_rate", 0.0))
    line_hit = float(text.get("line_hit_rate", 0.0))
    safe_rate = 1.0 - float(safe.get("rate", 1.0))

    return _clamp(100.0 * (0.4 * char_hit + 0.4 * line_hit + 0.2 * safe_rate))


def _score_motion(manifest_metrics: Dict[str, Any], quality: Dict[str, Any]) -> float:
    limits = quality.get("limits", {})
    diversity = manifest_metrics.get("diversity", {})

    transition_count = int(diversity.get("transition_type_count", 0))
    motion_count = int(diversity.get("motion_recipe_count", 0))

    max_transition = int(limits.get("maxTransitionTypes", 2))
    max_motion = int(limits.get("maxMotionRecipes", 3))

    penalty = max(0, transition_count - max_transition) * 18
    penalty += max(0, motion_count - max_motion) * 18

    return _clamp(100.0 - penalty)


def _score_audio(audio_metrics: Dict[str, Any], quality: Dict[str, Any]) -> float:
    audio_cfg = quality.get("audio", {})
    lufs = audio_metrics.get("input_i_lufs")
    tp = audio_metrics.get("input_tp_db")

    if lufs is None or tp is None:
        return 0.0

    target_lufs = float(audio_cfg.get("targetLUFS", -16.0))
    lufs_diff = abs(float(lufs) - target_lufs)
    lufs_score = _clamp(100.0 - lufs_diff * 20.0)

    tp_limit = float(audio_cfg.get("maxTruePeakDbTP", -1.0))
    if float(tp) <= tp_limit:
        tp_score = 100.0
    else:
        tp_score = _clamp(100.0 - (float(tp) - tp_limit) * 100.0)

    return _clamp(0.7 * lufs_score + 0.3 * tp_score)


def _score_stability(video_metrics: Dict[str, Any], quality: Dict[str, Any]) -> float:
    threshold = float(quality.get("flicker", {}).get("maxP95DeltaLuma", 18.0))
    p95 = float(video_metrics.get("p95DeltaLuma", 0.0))
    penalty = max(0.0, p95 - threshold) * 4.0
    return _clamp(100.0 - penalty)


def compute_score(
    video_metrics: Dict[str, Any],
    audio_metrics: Dict[str, Any],
    manifest_metrics: Dict[str, Any],
    quality: Dict[str, Any],
) -> Dict[str, Any]:
    weights = quality.get("weights", {})

    breakdown = {
        "rhythm": _score_rhythm(manifest_metrics, quality),
        "text": _score_text(manifest_metrics),
        "motion_consistency": _score_motion(manifest_metrics, quality),
        "audio": _score_audio(audio_metrics, quality),
        "visual_stability": _score_stability(video_metrics, quality),
    }

    weight_map = {
        "rhythm": float(weights.get("rhythm", 25.0)),
        "text": float(weights.get("text", 20.0)),
        "motion_consistency": float(weights.get("motion", 20.0)),
        "audio": float(weights.get("audio", 15.0)),
        "visual_stability": float(weights.get("stability", 20.0)),
    }

    weight_sum = sum(weight_map.values()) or 1.0
    total = sum(breakdown[k] * weight_map[k] for k in breakdown) / weight_sum

    return {
        "total": round(_clamp(total), 2),
        "breakdown": {k: round(v, 2) for k, v in breakdown.items()},
    }
