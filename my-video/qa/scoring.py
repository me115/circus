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
    structure = manifest_metrics.get("structure", {})
    diversity = manifest_metrics.get("diversity", {})
    highlight = manifest_metrics.get("highlight", {})
    density_metric = manifest_metrics.get("density_metric", {})
    motion_metric = manifest_metrics.get("motion_consistency_metric", {})
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
    max_low_info_run_sec_gate = float(limits.get("maxLowInfoRunSecGate", 1.5))
    low_info_run_ok = float(video_metrics.get("maxLowInfoRunSec", 0.0)) <= max_low_info_run_sec_gate

    fg_cov_p25 = float(
        video_metrics.get(
            "foregroundCoverageP25Enforced",
            video_metrics.get("foregroundCoverageP25", 0.0),
        )
    )
    min_fg_cov_gate = float(limits.get("minForegroundCoverageP25Gate", 0.015))
    foreground_coverage_ok = fg_cov_p25 >= min_fg_cov_gate
    beat_low_info_rate = float(video_metrics.get("beatLowInfoBeatRate", 1.0))
    max_beat_low_info_rate_gate = float(limits.get("maxBeatLowInfoRateGate", 0.2))
    beat_low_info_ok = beat_low_info_rate <= max_beat_low_info_rate_gate

    fg_bbox_h_p25 = float(video_metrics.get("foregroundBBoxHeightP25", 0.0))
    min_fg_bbox_h_p25_gate = float(limits.get("minForegroundBBoxHeightP25Gate", 0.22))
    foreground_bbox_height_ok = fg_bbox_h_p25 >= min_fg_bbox_h_p25_gate

    fg_strip_rate = float(video_metrics.get("foregroundStripRate", 0.0))
    max_fg_strip_rate_gate = float(limits.get("maxForegroundStripRateGate", 0.35))
    foreground_strip_ok = fg_strip_rate <= max_fg_strip_rate_gate

    fg_bbox_aspect_p75 = float(video_metrics.get("foregroundBBoxAspectP75", 0.0))
    max_fg_bbox_aspect_p75_gate = float(limits.get("maxForegroundBBoxAspectP75Gate", 5.5))
    foreground_aspect_ok = fg_bbox_aspect_p75 <= max_fg_bbox_aspect_p75_gate
    occupied_quadrants_p25 = float(video_metrics.get("occupiedQuadrantCountP25", 0.0))
    min_occupied_quadrants_gate = float(limits.get("minOccupiedQuadrantCountP25Gate", 2.0))
    occupied_quadrants_ok = occupied_quadrants_p25 >= min_occupied_quadrants_gate
    thin_long_low_content_rate = float(video_metrics.get("thinLongLowContentRate", 0.0))
    max_thin_long_low_content_rate_gate = float(
        limits.get("maxThinLongLowContentRateGate", 0.12)
    )
    thin_long_low_content_ok = thin_long_low_content_rate <= max_thin_long_low_content_rate_gate

    beat_coverage_map_layout = layout.get("beat_effective_coverage_map", {})
    beat_coverage_map_layout = (
        beat_coverage_map_layout if isinstance(beat_coverage_map_layout, dict) else {}
    )
    beat_coverage_map_video = video_metrics.get("beatForegroundCoverageP25", {})
    beat_coverage_map_video = (
        beat_coverage_map_video if isinstance(beat_coverage_map_video, dict) else {}
    )
    beat_coverage_map = beat_coverage_map_layout or beat_coverage_map_video
    beat_intents = manifest_metrics.get("beat_intents", {})
    beat_intents = beat_intents if isinstance(beat_intents, dict) else {}
    structural_intents = {"how_steps", "pipeline_flow", "pipeline_3", "problem_compare"}
    min_structural_beat_cov_gate = float(limits.get("minStructuralBeatCoverageP25Gate", 0.045))
    structural_low_ids = []
    structural_total = 0
    for beat_id, intent in beat_intents.items():
        if str(intent) not in structural_intents:
            continue
        cov = float(beat_coverage_map.get(str(beat_id), 0.0))
        structural_total += 1
        if cov < min_structural_beat_cov_gate:
            structural_low_ids.append(str(beat_id))
    structural_low_rate = float(len(structural_low_ids) / structural_total) if structural_total > 0 else 0.0
    max_structural_low_rate_gate = float(limits.get("maxStructuralLowCoverageBeatRateGate", 0.12))
    structural_beat_coverage_ok = structural_low_rate <= max_structural_low_rate_gate

    fg_center_x_dev = abs(float(video_metrics.get("foregroundCenterXPctMean", 0.5)) - 0.5)
    max_fg_center_x_dev_gate = float(limits.get("maxForegroundCenterXDeviationGate", 0.2))
    foreground_balance_x_ok = fg_center_x_dev <= max_fg_center_x_dev_gate

    alignment_score = float(layout.get("alignment_score", 0.0))
    min_alignment_gate = float(limits.get("minAlignmentScoreGate", 0.5))
    alignment_ok = alignment_score >= min_alignment_gate
    text_fill_ratio_p25 = float(layout.get("text_fill_ratio_p25", 0.0))
    min_text_fill_ratio_p25_gate = float(limits.get("minTextFillRatioP25Gate", 0.08))
    text_fill_ratio_ok = text_fill_ratio_p25 >= min_text_fill_ratio_p25_gate
    low_text_fill_block_rate = float(layout.get("low_text_fill_block_rate", 1.0))
    max_low_text_fill_block_rate_gate = float(
        limits.get("maxLowTextFillBlockRateGate", limits.get("maxLowTextFillBlockRate", 0.25))
    )
    low_text_fill_block_ok = low_text_fill_block_rate <= max_low_text_fill_block_rate_gate
    low_text_fill_beat_rate = float(layout.get("low_text_fill_beat_rate", 1.0))
    max_low_text_fill_beat_rate_gate = float(limits.get("maxLowTextFillBeatRateGate", 0.35))
    low_text_fill_beat_ok = low_text_fill_beat_rate <= max_low_text_fill_beat_rate_gate
    overlap_beat_rate = float(layout.get("overlap_beat_rate", 1.0))
    max_overlap_beat_rate_gate = float(
        limits.get("maxOverlapBeatRateGate", limits.get("maxOverlapBeatRate", 0.08))
    )
    overlap_beat_ok = overlap_beat_rate <= max_overlap_beat_rate_gate
    max_overlap_ratio = float(layout.get("max_overlap_ratio", 1.0))
    max_overlap_ratio_gate = float(
        limits.get("maxOverlapRatioGate", limits.get("maxOverlapRatio", 0.22))
    )
    overlap_ratio_ok = max_overlap_ratio <= max_overlap_ratio_gate
    severe_overlap_rate = float(layout.get("severe_overlap_beat_rate", 1.0))
    max_severe_overlap_beat_rate_gate = float(
        limits.get(
            "maxSevereOverlapBeatRateGate",
            limits.get("maxSevereOverlapBeatRate", 0.0),
        )
    )
    severe_overlap_ok = severe_overlap_rate <= max_severe_overlap_beat_rate_gate
    wrap_risk_beat_rate = float(layout.get("wrap_risk_beat_rate", 1.0))
    max_wrap_risk_beat_rate_gate = float(
        limits.get("maxWrapRiskBeatRateGate", limits.get("maxWrapRiskBeatRate", 0.1))
    )
    wrap_risk_ok = wrap_risk_beat_rate <= max_wrap_risk_beat_rate_gate

    sparse_beat_rate = float(layout.get("sparse_beat_rate", 1.0))
    max_sparse_beat_rate_gate = float(limits.get("maxSparseBeatRateGate", 0.5))
    sparse_beat_ok = sparse_beat_rate <= max_sparse_beat_rate_gate
    effective_cov_p25 = float(layout.get("effective_coverage_p25", 0.0))
    min_effective_cov_p25_gate = float(
        limits.get(
            "minEffectiveCoverageP25Gate",
            limits.get("minEffectiveCoverageP25", 0.26),
        )
    )
    effective_cov_p25_ok = effective_cov_p25 >= min_effective_cov_p25_gate
    weak_structure_beat_rate = float(structure.get("weak_structure_beat_rate", 1.0))
    max_weak_structure_beat_rate_gate = float(limits.get("maxWeakStructureBeatRateGate", 0.0))
    structure_integrity_ok = weak_structure_beat_rate <= max_weak_structure_beat_rate_gate
    short_structural_beat_count = int(structure.get("short_structural_beat_count", 0))
    structural_min_duration_ok = short_structural_beat_count == 0

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
    bad_line_break_rate = float(density_metric.get("bad_line_break_rate", 0.0))
    bad_line_break_count = int(density_metric.get("bad_line_break_count", 0) or 0)
    hook_bad_line_break_count = int(density_metric.get("hook_bad_line_break_count", 0) or 0)
    short_hold_beat_rate = float(density_metric.get("short_hold_beat_rate", 0.0))
    short_hold_beat_count = int(density_metric.get("short_hold_beat_count", 0) or 0)
    fragment_line_rate = float(density_metric.get("fragment_line_rate", 0.0))
    max_bad_line_break_rate_gate = float(limits.get("maxBadLineBreakRateGate", 0.18))
    max_bad_line_break_count_gate = int(limits.get("maxBadLineBreakCountGate", 1))
    max_hook_bad_line_break_count_gate = int(limits.get("maxHookBadLineBreakCountGate", 0))
    max_short_hold_beat_rate_gate = float(limits.get("maxShortHoldBeatRateGate", 0.12))
    max_short_hold_beat_count_gate = int(limits.get("maxShortHoldBeatCountGate", 1))
    max_fragment_line_rate_gate = float(limits.get("maxFragmentLineRateGate", 0.1))
    line_break_quality_ok = (
        bad_line_break_rate <= max_bad_line_break_rate_gate
        and bad_line_break_count <= max_bad_line_break_count_gate
        and hook_bad_line_break_count <= max_hook_bad_line_break_count_gate
    )
    text_hold_duration_ok = (
        short_hold_beat_rate <= max_short_hold_beat_rate_gate
        and short_hold_beat_count <= max_short_hold_beat_count_gate
    )
    fragment_line_quality_ok = fragment_line_rate <= max_fragment_line_rate_gate
    bad_highlight_beat_rate = float(highlight.get("bad_highlight_beat_rate", 0.0))
    max_bad_highlight_beat_rate_gate = float(limits.get("maxBadHighlightBeatRateGate", 0.0))
    highlight_quality_ok = bad_highlight_beat_rate <= max_bad_highlight_beat_rate_gate
    backdrop_preset_count = int(motion_metric.get("backdrop_preset_count", 0))
    max_backdrop_preset_count_gate = int(
        limits.get("maxBackdropPresetCountGate", limits.get("maxBackdropPresetCount", 1))
    )
    backdrop_preset_count_ok = backdrop_preset_count <= max_backdrop_preset_count_gate
    backdrop_switch_rate = float(motion_metric.get("backdrop_switch_rate", 0.0))
    max_backdrop_switch_rate_gate = float(
        limits.get("maxBackdropSwitchRateGate", limits.get("maxBackdropSwitchRate", 0.2))
    )
    backdrop_switch_ok = backdrop_switch_rate <= max_backdrop_switch_rate_gate
    backdrop_max_intensity_jump = float(motion_metric.get("backdrop_max_intensity_jump", 0.0))
    max_backdrop_intensity_jump_gate = float(
        limits.get(
            "maxBackdropIntensityJumpGate",
            limits.get("maxBackdropIntensityJump", 0.16),
        )
    )
    backdrop_intensity_jump_ok = (
        backdrop_max_intensity_jump <= max_backdrop_intensity_jump_gate
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
        "low_info_run": bool(low_info_run_ok),
        "lower_half_coverage": bool(lower_half_ok),
        "foreground_lower_half_p25": bool(foreground_lower_half_p25_ok),
        "foreground_coverage": bool(foreground_coverage_ok),
        "beat_low_info_rate": bool(beat_low_info_ok),
        "foreground_bbox_height": bool(foreground_bbox_height_ok),
        "foreground_strip_rate": bool(foreground_strip_ok),
        "foreground_bbox_aspect": bool(foreground_aspect_ok),
        "occupied_quadrants": bool(occupied_quadrants_ok),
        "thin_long_low_content": bool(thin_long_low_content_ok),
        "structural_beat_coverage": bool(structural_beat_coverage_ok),
        "foreground_balance_x": bool(foreground_balance_x_ok),
        "alignment": bool(alignment_ok),
        "text_fill_ratio_p25": bool(text_fill_ratio_ok),
        "low_text_fill_block_rate": bool(low_text_fill_block_ok),
        "low_text_fill_beat_rate": bool(low_text_fill_beat_ok),
        "overlap_beat_rate": bool(overlap_beat_ok),
        "max_overlap_ratio": bool(overlap_ratio_ok),
        "severe_overlap_beat_rate": bool(severe_overlap_ok),
        "wrap_risk_beat_rate": bool(wrap_risk_ok),
        "sparse_beat_rate": bool(sparse_beat_ok),
        "effective_coverage_p25": bool(effective_cov_p25_ok),
        "line_break_quality": bool(line_break_quality_ok),
        "text_hold_duration": bool(text_hold_duration_ok),
        "fragment_line_quality": bool(fragment_line_quality_ok),
        "highlight_quality": bool(highlight_quality_ok),
        "backdrop_preset_count": bool(backdrop_preset_count_ok),
        "backdrop_switch_rate": bool(backdrop_switch_ok),
        "backdrop_intensity_jump": bool(backdrop_intensity_jump_ok),
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


def _upper_bound_positive_score(value: float, max_allowed: float) -> float:
    safe_allowed = max(float(max_allowed), 1e-6)
    if value <= safe_allowed:
        return 1.0
    return max(0.0, 1.0 - (value - safe_allowed) / safe_allowed)


def _score_composition(
    video_metrics: Dict[str, Any], manifest_metrics: Dict[str, Any], quality: Dict[str, Any]
) -> float:
    layout = manifest_metrics.get("layout", {})
    structure = manifest_metrics.get("structure", {})
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
    text_fill_ratio_p25 = float(layout.get("text_fill_ratio_p25", 0.0))
    min_text_fill_ratio_p25 = float(limits.get("minTextFillRatioP25", 0.1))
    text_fill_ratio_score = min(1.0, text_fill_ratio_p25 / max(min_text_fill_ratio_p25, 1e-6))
    low_text_fill_block_rate = float(layout.get("low_text_fill_block_rate", 1.0))
    max_low_text_fill_block_rate = float(
        limits.get("maxLowTextFillBlockRate", limits.get("maxLowTextFillBlockRateGate", 0.25))
    )
    low_text_fill_block_score = _upper_bound_score(
        low_text_fill_block_rate, max_low_text_fill_block_rate
    )
    low_text_fill_beat_rate = float(layout.get("low_text_fill_beat_rate", 1.0))
    max_low_text_fill_beat_rate = float(limits.get("maxLowTextFillBeatRate", 0.25))
    low_text_fill_beat_score = _upper_bound_score(
        low_text_fill_beat_rate, max_low_text_fill_beat_rate
    )
    overlap_beat_rate = float(layout.get("overlap_beat_rate", 1.0))
    max_overlap_beat_rate = float(limits.get("maxOverlapBeatRate", 0.08))
    overlap_beat_score = _upper_bound_score(overlap_beat_rate, max_overlap_beat_rate)
    max_overlap_ratio = float(layout.get("max_overlap_ratio", 1.0))
    max_overlap_ratio_limit = float(limits.get("maxOverlapRatio", 0.22))
    overlap_ratio_score = _upper_bound_score(max_overlap_ratio, max_overlap_ratio_limit)
    severe_overlap_rate = float(layout.get("severe_overlap_beat_rate", 1.0))
    max_severe_overlap_rate = float(limits.get("maxSevereOverlapBeatRate", 0.0))
    severe_overlap_score = _upper_bound_score(severe_overlap_rate, max_severe_overlap_rate)
    wrap_risk_beat_rate = float(layout.get("wrap_risk_beat_rate", 1.0))
    max_wrap_risk_beat_rate = float(limits.get("maxWrapRiskBeatRate", 0.1))
    wrap_risk_score = _upper_bound_score(wrap_risk_beat_rate, max_wrap_risk_beat_rate)

    fg_cov_p25 = float(
        video_metrics.get(
            "foregroundCoverageP25Enforced",
            video_metrics.get("foregroundCoverageP25", 0.0),
        )
    )
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
    beat_low_info_rate = float(video_metrics.get("beatLowInfoBeatRate", 1.0))
    max_beat_low_info_rate = float(limits.get("maxBeatLowInfoRate", 0.12))
    beat_low_info_score = _upper_bound_score(beat_low_info_rate, max_beat_low_info_rate)
    max_low_info_run_sec = float(video_metrics.get("maxLowInfoRunSec", 0.0))
    max_low_info_run_sec_target = float(limits.get("maxLowInfoRunSec", 1.5))
    low_info_run_score = _upper_bound_positive_score(
        max_low_info_run_sec, max_low_info_run_sec_target
    )
    occupied_quadrants_p25 = float(video_metrics.get("occupiedQuadrantCountP25", 0.0))
    min_occupied_quadrants = float(limits.get("minOccupiedQuadrantCountP25", 2.0))
    occupied_quadrants_score = min(1.0, occupied_quadrants_p25 / max(min_occupied_quadrants, 1e-6))
    thin_long_low_content_rate = float(video_metrics.get("thinLongLowContentRate", 0.0))
    max_thin_long_low_content_rate = float(limits.get("maxThinLongLowContentRate", 0.08))
    thin_long_low_content_score = _upper_bound_score(
        thin_long_low_content_rate, max_thin_long_low_content_rate
    )
    weak_structure_beat_rate = float(structure.get("weak_structure_beat_rate", 1.0))
    max_weak_structure_beat_rate = float(limits.get("maxWeakStructureBeatRate", 0.06))
    structure_integrity_score = _upper_bound_score(
        weak_structure_beat_rate, max_weak_structure_beat_rate
    )

    return _clamp(
        100.0
        * (
            0.01 * coverage_score
            + 0.02 * balance_score
            + 0.02 * balance_x_score
            + 0.07 * readable_score
            + 0.06 * lower_half_score
            + 0.04 * coverage_ratio_score
            + 0.08 * effective_cov_p25_score
            + 0.07 * sparse_score
            + 0.08 * alignment_quality_score
            + 0.08 * foreground_coverage_score
            + 0.05 * foreground_lower_half_score
            + 0.04 * foreground_balance_x_score
            + 0.08 * foreground_bbox_height_score
            + 0.04 * foreground_strip_score
            + 0.05 * beat_low_info_score
            + 0.06 * low_info_run_score
            + 0.05 * occupied_quadrants_score
            + 0.03 * thin_long_low_content_score
            + 0.03 * structure_integrity_score
            + 0.016 * text_fill_ratio_score
            + 0.01 * low_text_fill_beat_score
            + 0.006 * low_text_fill_block_score
            + 0.01 * overlap_beat_score
            + 0.008 * overlap_ratio_score
            + 0.007 * severe_overlap_score
            + 0.007 * wrap_risk_score
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

    narrative_metric = manifest_metrics.get("narrative_metric", {})
    density_metric = manifest_metrics.get("density_metric", {})
    motion_consistency_metric = manifest_metrics.get("motion_consistency_metric", {})
    composition_score = _score_composition(video_metrics, manifest_metrics, quality)
    motion_diversity_score = _score_motion(manifest_metrics, quality)

    density_base = float(density_metric.get("score", 0.0))
    motion_base = float(motion_consistency_metric.get("score", 0.0))

    breakdown = {
        "narrative": float(narrative_metric.get("score", 0.0)),
        "density": _clamp(0.55 * density_base + 0.45 * composition_score),
        "motion_consistency": _clamp(0.65 * motion_base + 0.35 * motion_diversity_score),
        "rhythm": _score_rhythm(manifest_metrics, quality),
        "audio": _score_audio(audio_metrics, quality),
        "visual_stability": _score_stability(video_metrics, quality),
    }

    weight_map = {
        "narrative": float(weights.get("narrative", 20.0)),
        "density": float(weights.get("density", 20.0)),
        "motion_consistency": float(
            weights.get("motion_consistency", weights.get("motion", 20.0))
        ),
        "rhythm": float(weights.get("rhythm", 20.0)),
        "audio": float(weights.get("audio", 10.0)),
        "visual_stability": float(weights.get("stability", 10.0)),
    }

    weight_sum = sum(weight_map.values()) or 1.0
    total = sum(breakdown[k] * weight_map[k] for k in breakdown) / weight_sum

    return {
        "total": round(_clamp(total), 2),
        "breakdown": {k: round(v, 2) for k, v in breakdown.items()},
    }
