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
    bounds_ok = int(manifest_metrics.get("bounds", {}).get("violations", 1)) == 0
    layout = manifest_metrics.get("layout", {})
    diversity = manifest_metrics.get("diversity", {})
    limits = quality.get("limits", {})
    min_lower_half = float(
        limits.get("minLowerHalfCoverageGate", limits.get("minLowerHalfCoverage", 0.24))
    )
    lower_half_ratio = float(layout.get("lower_half_coverage_ratio", 0.0))
    lower_half_ok = lower_half_ratio >= min_lower_half
    fg_lower_half_p25 = float(video_metrics.get("foregroundLowerHalfRatioP25", 0.0))
    min_fg_lower_half_p25_gate = float(limits.get("minForegroundLowerHalfRatioP25Gate", 0.08))
    foreground_lower_half_p25_ok = fg_lower_half_p25 >= min_fg_lower_half_p25_gate

    no_element_gap = manifest_metrics.get("no_element_gap", {})
    max_no_element_gap = float(limits.get("maxNoElementGapSec", 3.0))
    no_element_gap_video = float(video_metrics.get("maxNoElementGapSecVideo", 0.0))
    no_element_gap_manifest_ok = bool(no_element_gap.get("pass", False))
    no_element_gap_ok = no_element_gap_manifest_ok and no_element_gap_video <= max_no_element_gap

    fg_cov_p25 = float(video_metrics.get("foregroundCoverageP25", 0.0))
    min_fg_cov_gate = float(limits.get("minForegroundCoverageP25Gate", 0.015))
    foreground_coverage_ok = fg_cov_p25 >= min_fg_cov_gate

    fg_bbox_h_p25 = float(video_metrics.get("foregroundBBoxHeightP25", 0.0))
    min_fg_bbox_h_p25_gate = float(limits.get("minForegroundBBoxHeightP25Gate", 0.22))
    foreground_bbox_height_ok = fg_bbox_h_p25 >= min_fg_bbox_h_p25_gate

    fg_strip_rate = float(video_metrics.get("foregroundStripRate", 0.0))
    max_fg_strip_rate_gate = float(limits.get("maxForegroundStripRateGate", 0.35))
    foreground_strip_ok = fg_strip_rate <= max_fg_strip_rate_gate

    fg_bbox_aspect_p75 = float(video_metrics.get("foregroundBBoxAspectP75", 0.0))
    max_fg_bbox_aspect_p75_gate = float(limits.get("maxForegroundBBoxAspectP75Gate", 5.5))
    foreground_aspect_ok = fg_bbox_aspect_p75 <= max_fg_bbox_aspect_p75_gate

    fg_center_x_dev = abs(float(video_metrics.get("foregroundCenterXPctMean", 0.5)) - 0.5)
    max_fg_center_x_dev_gate = float(limits.get("maxForegroundCenterXDeviationGate", 0.2))
    foreground_balance_x_ok = fg_center_x_dev <= max_fg_center_x_dev_gate

    alignment_score = float(layout.get("alignment_score", 0.0))
    min_alignment_gate = float(limits.get("minAlignmentScoreGate", 0.5))
    alignment_ok = alignment_score >= min_alignment_gate

    sparse_beat_rate = float(layout.get("sparse_beat_rate", 1.0))
    max_sparse_beat_rate_gate = float(limits.get("maxSparseBeatRateGate", 0.5))
    sparse_beat_ok = sparse_beat_rate <= max_sparse_beat_rate_gate

    react_variant_count = int(diversity.get("react_variant_count", 0))
    min_react_variants_gate = int(limits.get("minReactVariantsGate", limits.get("minReactVariants", 5)))
    react_variant_count_ok = react_variant_count >= min_react_variants_gate

    dominant_react_variant_share = float(diversity.get("dominant_react_variant_share", 1.0))
    max_dominant_react_variant_share_gate = float(
        limits.get(
            "maxDominantReactVariantShareGate",
            limits.get("maxDominantReactVariantShare", 0.34),
        )
    )
    react_variant_mix_ok = dominant_react_variant_share <= max_dominant_react_variant_share_gate

    max_consecutive_react_variant_run = int(diversity.get("max_consecutive_react_variant_run", 0))
    max_consecutive_react_variant_run_gate = int(
        limits.get(
            "maxConsecutiveReactVariantRunGate",
            limits.get("maxConsecutiveReactVariantRun", 3),
        )
    )
    react_variant_run_ok = max_consecutive_react_variant_run <= max_consecutive_react_variant_run_gate

    adjacent_react_variant_repeat_rate = float(diversity.get("adjacent_react_variant_repeat_rate", 0.0))
    max_adjacent_react_repeat_rate_gate = float(
        limits.get(
            "maxAdjacentReactRepeatRateGate",
            limits.get("maxAdjacentReactRepeatRate", 0.35),
        )
    )
    react_variant_adjacent_ok = (
        adjacent_react_variant_repeat_rate <= max_adjacent_react_repeat_rate_gate
    )

    scene_signature_count = int(diversity.get("scene_signature_count", 0))
    min_scene_signatures_gate = int(
        limits.get("minSceneSignaturesGate", limits.get("minSceneSignatures", 7))
    )
    scene_signature_count_ok = scene_signature_count >= min_scene_signatures_gate

    dominant_scene_signature_share = float(diversity.get("dominant_scene_signature_share", 1.0))
    max_dominant_scene_signature_share_gate = float(
        limits.get(
            "maxDominantSceneSignatureShareGate",
            limits.get("maxDominantSceneSignatureShare", 0.24),
        )
    )
    scene_signature_mix_ok = (
        dominant_scene_signature_share <= max_dominant_scene_signature_share_gate
    )

    checks = {
        "resolution": bool(width_ok and height_ok),
        "fps": bool(fps_ok),
        "duration": bool(duration_ok),
        "black_frame_ratio": bool(black_ok),
        "audio_true_peak": bool(tp_ok),
        "audio_lufs": bool(lufs_ok),
        "layout_bounds": bool(bounds_ok),
        "safe_area": bool(safe_ok),
        "no_element_gap": bool(no_element_gap_ok),
        "lower_half_coverage": bool(lower_half_ok),
        "foreground_lower_half_p25": bool(foreground_lower_half_p25_ok),
        "foreground_coverage": bool(foreground_coverage_ok),
        "foreground_bbox_height": bool(foreground_bbox_height_ok),
        "foreground_strip_rate": bool(foreground_strip_ok),
        "foreground_bbox_aspect": bool(foreground_aspect_ok),
        "foreground_balance_x": bool(foreground_balance_x_ok),
        "alignment": bool(alignment_ok),
        "sparse_beat_rate": bool(sparse_beat_ok),
        "react_variant_count": bool(react_variant_count_ok),
        "react_variant_mix": bool(react_variant_mix_ok),
        "react_variant_run": bool(react_variant_run_ok),
        "react_variant_adjacent_repeat": bool(react_variant_adjacent_ok),
        "scene_signature_count": bool(scene_signature_count_ok),
        "scene_signature_mix": bool(scene_signature_mix_ok),
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


def _band_score(count: int, min_count: int, max_count: int) -> float:
    if max_count < 1:
        return 1.0
    if count < min_count:
        return max(0.0, float(count / max(min_count, 1)))
    if count > max_count:
        return max(0.0, 1.0 - float(count - max_count) / max(max_count, 1))
    return 1.0


def _dominance_score(dominant_share: float, max_share: float) -> float:
    if dominant_share <= max_share:
        return 1.0
    return max(
        0.0,
        1.0 - (dominant_share - max_share) / max(1.0 - max_share, 1e-6),
    )


def _max_run_score(run_len: int, max_allowed: int) -> float:
    safe_allowed = max(1, int(max_allowed))
    if run_len <= safe_allowed:
        return 1.0
    return max(0.0, 1.0 - float(run_len - safe_allowed) / max(safe_allowed, 1))


def _upper_bound_score(value: float, max_allowed: float) -> float:
    safe_allowed = max(0.0, min(1.0, float(max_allowed)))
    if value <= safe_allowed:
        return 1.0
    return max(0.0, 1.0 - (value - safe_allowed) / max(1.0 - safe_allowed, 1e-6))


def _score_composition(
    video_metrics: Dict[str, Any], manifest_metrics: Dict[str, Any], quality: Dict[str, Any]
) -> float:
    layout = manifest_metrics.get("layout", {})
    limits = quality.get("limits", {})

    coverage_score = float(layout.get("coverage_score", 0.0))
    balance_score = float(layout.get("balance_score", 0.0))
    balance_x_score = float(layout.get("balance_x_score", 0.0))
    readable_font_rate = float(layout.get("readable_font_rate", 0.0))
    lower_half_ratio = float(layout.get("lower_half_coverage_ratio", 0.0))
    min_lower_half = float(limits.get("minLowerHalfCoverage", 0.24))
    lower_half_score = min(1.0, lower_half_ratio / max(min_lower_half, 1e-6))
    min_readable_rate = float(limits.get("minReadableFontRate", 0.78))
    readable_score = min(1.0, readable_font_rate / max(min_readable_rate, 1e-6))
    coverage_ratio = float(layout.get("coverage_ratio", 0.0))
    min_coverage = float(limits.get("minComponentCoverage", limits.get("minContentCoverage", 0.22)))
    coverage_ratio_score = min(1.0, coverage_ratio / max(min_coverage, 1e-6))
    effective_cov_p25 = float(layout.get("effective_coverage_p25", 0.0))
    min_effective_cov_p25 = float(limits.get("minEffectiveCoverageP25", 0.26))
    effective_cov_p25_score = min(1.0, effective_cov_p25 / max(min_effective_cov_p25, 1e-6))
    sparse_beat_rate = float(layout.get("sparse_beat_rate", 1.0))
    max_sparse_beat_rate = float(limits.get("maxSparseBeatRate", 0.18))
    sparse_score = max(0.0, 1.0 - sparse_beat_rate / max(max_sparse_beat_rate, 1e-6))
    alignment_score = float(layout.get("alignment_score", 0.0))
    min_alignment_score = float(limits.get("minAlignmentScore", 0.72))
    alignment_quality_score = min(1.0, alignment_score / max(min_alignment_score, 1e-6))

    fg_cov_p25 = float(video_metrics.get("foregroundCoverageP25", 0.0))
    min_fg_cov_p25 = float(limits.get("minForegroundCoverageP25", 0.045))
    foreground_coverage_score = min(1.0, fg_cov_p25 / max(min_fg_cov_p25, 1e-6))
    fg_lower_half_p25 = float(video_metrics.get("foregroundLowerHalfRatioP25", 0.0))
    min_fg_lower_half_p25 = float(
        limits.get("minForegroundLowerHalfRatioP25", limits.get("minForegroundLowerHalfRatioP25Gate", 0.1))
    )
    foreground_lower_half_score = min(1.0, fg_lower_half_p25 / max(min_fg_lower_half_p25, 1e-6))
    fg_center_x = float(video_metrics.get("foregroundCenterXPctMean", 0.5))
    max_fg_center_x_dev = float(limits.get("maxForegroundCenterXDeviation", 0.1))
    foreground_balance_x_score = max(
        0.0,
        1.0 - abs(fg_center_x - 0.5) / max(max_fg_center_x_dev, 1e-6),
    )
    fg_bbox_h_p25 = float(video_metrics.get("foregroundBBoxHeightP25", 0.0))
    min_fg_bbox_h_p25 = float(limits.get("minForegroundBBoxHeightP25", 0.32))
    foreground_bbox_height_score = min(1.0, fg_bbox_h_p25 / max(min_fg_bbox_h_p25, 1e-6))
    fg_strip_rate = float(video_metrics.get("foregroundStripRate", 0.0))
    max_fg_strip_rate = float(limits.get("maxForegroundStripRate", 0.22))
    foreground_strip_score = _upper_bound_score(fg_strip_rate, max_fg_strip_rate)

    return _clamp(
        100.0
        * (
            0.01 * coverage_score
            + 0.02 * balance_score
            + 0.02 * balance_x_score
            + 0.08 * readable_score
            + 0.09 * lower_half_score
            + 0.05 * coverage_ratio_score
            + 0.13 * effective_cov_p25_score
            + 0.11 * sparse_score
            + 0.1 * alignment_quality_score
            + 0.12 * foreground_coverage_score
            + 0.05 * foreground_lower_half_score
            + 0.04 * foreground_balance_x_score
            + 0.11 * foreground_bbox_height_score
            + 0.07 * foreground_strip_score
        )
    )


def _score_motion(manifest_metrics: Dict[str, Any], quality: Dict[str, Any]) -> float:
    limits = quality.get("limits", {})
    diversity = manifest_metrics.get("diversity", {})

    transition_count = int(diversity.get("transition_type_count", 0))
    motion_count = int(diversity.get("motion_recipe_count", 0))
    dominant_transition_share = float(diversity.get("dominant_transition_share", 1.0))
    dominant_motion_share = float(diversity.get("dominant_motion_share", 1.0))
    component_type_count = int(diversity.get("component_type_count", 0))
    dominant_component_share = float(diversity.get("dominant_component_share", 1.0))
    react_variant_count = int(diversity.get("react_variant_count", 0))
    dominant_react_variant_share = float(diversity.get("dominant_react_variant_share", 1.0))
    max_consecutive_react_variant_run = int(diversity.get("max_consecutive_react_variant_run", 0))
    adjacent_react_variant_repeat_rate = float(diversity.get("adjacent_react_variant_repeat_rate", 1.0))
    scene_signature_count = int(diversity.get("scene_signature_count", 0))
    dominant_scene_signature_share = float(diversity.get("dominant_scene_signature_share", 1.0))
    max_consecutive_scene_signature_run = int(diversity.get("max_consecutive_scene_signature_run", 0))
    adjacent_scene_signature_repeat_rate = float(
        diversity.get("adjacent_scene_signature_repeat_rate", 1.0)
    )

    min_transition = int(limits.get("minTransitionTypes", 2))
    max_transition = int(limits.get("maxTransitionTypes", 2))
    min_motion = int(limits.get("minMotionRecipes", 2))
    max_motion = int(limits.get("maxMotionRecipes", 3))
    min_component_types = int(limits.get("minComponentTypes", 4))
    min_react_variants = int(limits.get("minReactVariants", 6))
    min_scene_signatures = int(limits.get("minSceneSignatures", 8))
    max_dominant_share = float(limits.get("maxDominantComponentShare", 0.62))
    max_dominant_transition = float(limits.get("maxDominantTransitionShare", 0.78))
    max_dominant_motion = float(limits.get("maxDominantMotionShare", 0.76))
    max_dominant_react_variant_share = float(limits.get("maxDominantReactVariantShare", 0.28))
    max_consecutive_react_variant_run_limit = int(limits.get("maxConsecutiveReactVariantRun", 3))
    max_adjacent_react_repeat_rate = float(limits.get("maxAdjacentReactRepeatRate", 0.3))
    max_dominant_scene_signature_share = float(
        limits.get("maxDominantSceneSignatureShare", 0.24)
    )
    max_consecutive_scene_signature_run_limit = int(
        limits.get("maxConsecutiveSceneSignatureRun", 2)
    )
    max_adjacent_scene_signature_repeat_rate = float(
        limits.get("maxAdjacentSceneSignatureRepeatRate", 0.2)
    )
    unsupported_layers = int(diversity.get("unsupported_layer_type_count", 0))

    transition_score = _band_score(transition_count, min_transition, max_transition)
    motion_score = _band_score(motion_count, min_motion, max_motion)
    component_type_score = min(1.0, component_type_count / max(min_component_types, 1))
    repetition_score = _dominance_score(dominant_component_share, max_dominant_share)
    transition_mix_score = _dominance_score(dominant_transition_share, max_dominant_transition)
    motion_mix_score = _dominance_score(dominant_motion_share, max_dominant_motion)
    react_variant_score = min(1.0, react_variant_count / max(min_react_variants, 1))
    react_mix_score = _dominance_score(
        dominant_react_variant_share, max_dominant_react_variant_share
    )
    react_run_score = _max_run_score(
        max_consecutive_react_variant_run, max_consecutive_react_variant_run_limit
    )
    react_adjacent_repeat_score = _upper_bound_score(
        adjacent_react_variant_repeat_rate, max_adjacent_react_repeat_rate
    )
    scene_signature_score = min(1.0, scene_signature_count / max(min_scene_signatures, 1))
    scene_mix_score = _dominance_score(
        dominant_scene_signature_share, max_dominant_scene_signature_share
    )
    scene_run_score = _max_run_score(
        max_consecutive_scene_signature_run, max_consecutive_scene_signature_run_limit
    )
    scene_adjacent_repeat_score = _upper_bound_score(
        adjacent_scene_signature_repeat_rate, max_adjacent_scene_signature_repeat_rate
    )

    unsupported_penalty = min(0.35, unsupported_layers * 0.12)

    total = (
        0.1 * transition_score
        + 0.1 * motion_score
        + 0.08 * component_type_score
        + 0.05 * repetition_score
        + 0.12 * transition_mix_score
        + 0.12 * motion_mix_score
        + 0.12 * react_variant_score
        + 0.1 * react_mix_score
        + 0.05 * react_run_score
        + 0.05 * react_adjacent_repeat_score
        + 0.06 * scene_signature_score
        + 0.03 * scene_mix_score
        + 0.01 * scene_run_score
        + 0.01 * scene_adjacent_repeat_score
    )

    total = max(0.0, total - unsupported_penalty)
    return _clamp(100.0 * total)


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
        "composition": _score_composition(video_metrics, manifest_metrics, quality),
        "motion_consistency": _score_motion(manifest_metrics, quality),
        "audio": _score_audio(audio_metrics, quality),
        "visual_stability": _score_stability(video_metrics, quality),
    }

    weight_map = {
        "rhythm": float(weights.get("rhythm", 12.0)),
        "text": float(weights.get("text", 8.0)),
        "composition": float(weights.get("composition", 35.0)),
        "motion_consistency": float(weights.get("motion", 25.0)),
        "audio": float(weights.get("audio", 10.0)),
        "visual_stability": float(weights.get("stability", 10.0)),
    }

    weight_sum = sum(weight_map.values()) or 1.0
    total = sum(breakdown[k] * weight_map[k] for k in breakdown) / weight_sum

    return {
        "total": round(_clamp(total), 2),
        "breakdown": {k: round(v, 2) for k, v in breakdown.items()},
    }
