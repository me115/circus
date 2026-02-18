from __future__ import annotations

import json
import math
import statistics
from typing import Any, Dict, List, Optional


def load_manifest(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_area_check(
    text_blocks: List[Dict[str, Any]], margins: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    eligible = [tb for tb in text_blocks if bool(tb.get("isTextLayer", True))]
    violations = [tb for tb in eligible if bool(tb.get("safeMarginViolation"))]
    return {
        "violations": len(violations),
        "total": len(eligible),
        "rate": (len(violations) / len(eligible)) if eligible else 0.0,
    }


def frame_bounds_check(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    violations = [tb for tb in blocks if bool(tb.get("frameOverflow"))]
    return {
        "violations": len(violations),
        "total": len(blocks),
        "rate": (len(violations) / len(blocks)) if blocks else 0.0,
    }


def beat_duration_stats(
    beats: List[Dict[str, Any]],
    min_sec: float = 2.5,
    max_sec: float = 4.0,
) -> Dict[str, Any]:
    durations = [max(0.0, float(b.get("t1", 0.0)) - float(b.get("t0", 0.0))) for b in beats]

    if not durations:
        return {
            "mean": 0.0,
            "std": 0.0,
            "pct_in_range": 0.0,
            "durations": [],
            "count": 0,
        }

    in_range = [d for d in durations if min_sec <= d <= max_sec]
    return {
        "mean": float(statistics.mean(durations)),
        "std": float(statistics.pstdev(durations)),
        "pct_in_range": float(len(in_range) / len(durations)),
        "durations": durations,
        "count": len(durations),
    }


def _dominant_share_from_counts(
    counts: Any, fallback_unique_count: int = 0
) -> tuple[int, float]:
    if isinstance(counts, dict):
        values: List[int] = []
        for value in counts.values():
            try:
                values.append(max(0, int(value)))
            except (TypeError, ValueError):
                continue
        total = int(sum(values))
        if total > 0 and values:
            return total, float(max(values) / total)

    if fallback_unique_count > 0:
        return fallback_unique_count, float(1.0 / max(1, fallback_unique_count))
    return 0, 1.0


def _sequence_run_stats(values: List[str]) -> tuple[int, float]:
    cleaned = [v for v in values if v]
    if not cleaned:
        return 0, 0.0

    max_run = 1
    cur_run = 1
    adjacent_pairs = 0
    adjacent_same = 0

    for i in range(1, len(cleaned)):
        adjacent_pairs += 1
        if cleaned[i] == cleaned[i - 1]:
            adjacent_same += 1
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 1

    repeat_rate = float(adjacent_same / adjacent_pairs) if adjacent_pairs > 0 else 0.0
    return max_run, repeat_rate


def diversity_stats(manifest: Dict[str, Any]) -> Dict[str, Any]:
    summary = manifest.get("effectsSummary") or {}
    beats = manifest.get("beats") or []
    transition_types = list(summary.get("transitionTypesUsed") or [])
    transition_counts = summary.get("transitionTypeCounts") or {}
    motion_recipes = list(summary.get("motionRecipesUsed") or [])
    motion_counts = summary.get("motionRecipeCounts") or {}
    component_types = list(summary.get("componentTypesUsed") or [])
    component_counts = summary.get("componentTypeCounts") or {}
    react_variants = list(summary.get("reactVariantsUsed") or [])
    react_counts = summary.get("reactVariantCounts") or {}
    unsupported = list(summary.get("unsupportedLayerTypes") or [])

    total_transitions, dominant_transition_share = _dominant_share_from_counts(
        transition_counts, fallback_unique_count=len(transition_types)
    )
    total_motions, dominant_motion_share = _dominant_share_from_counts(
        motion_counts, fallback_unique_count=len(motion_recipes)
    )
    total_components, dominant_component_share = _dominant_share_from_counts(
        component_counts, fallback_unique_count=len(component_types)
    )
    total_react_variants, dominant_react_variant_share = _dominant_share_from_counts(
        react_counts, fallback_unique_count=len(react_variants)
    )
    react_sequence = []
    scene_signatures = []
    for beat in beats:
        raw = beat.get("reactContents")
        if isinstance(raw, list) and raw:
            first = str(raw[0]).strip()
            react_sequence.append(first)
        else:
            react_sequence.append("")
        layer_types_raw = beat.get("layerTypes")
        layer_types = []
        if isinstance(layer_types_raw, list):
            layer_types = [str(item).strip() for item in layer_types_raw if str(item).strip()]
        react_all = []
        if isinstance(raw, list):
            react_all = [str(item).strip() for item in raw if str(item).strip()]
        if layer_types or react_all:
            signature = f"{'+'.join(layer_types)}::{'+'.join(react_all)}"
            scene_signatures.append(signature)
        else:
            scene_signatures.append("")

    scene_signature_counts: Dict[str, int] = {}
    for signature in scene_signatures:
        if not signature:
            continue
        scene_signature_counts[signature] = scene_signature_counts.get(signature, 0) + 1

    scene_signature_variants = list(scene_signature_counts.keys())
    total_scene_signatures, dominant_scene_signature_share = _dominant_share_from_counts(
        scene_signature_counts, fallback_unique_count=len(scene_signature_variants)
    )
    max_consecutive_react_variant_run, adjacent_react_variant_repeat_rate = _sequence_run_stats(
        react_sequence
    )
    max_consecutive_scene_signature_run, adjacent_scene_signature_repeat_rate = _sequence_run_stats(
        scene_signatures
    )

    return {
        "transition_types": transition_types,
        "transition_type_count": len(transition_types),
        "transition_type_counts": transition_counts,
        "dominant_transition_share": dominant_transition_share,
        "total_transition_instances": total_transitions,
        "motion_recipes": motion_recipes,
        "motion_recipe_count": len(motion_recipes),
        "motion_recipe_counts": motion_counts,
        "dominant_motion_share": dominant_motion_share,
        "total_motion_instances": total_motions,
        "component_types": component_types,
        "component_type_count": len(component_types),
        "component_type_counts": component_counts,
        "react_variants": react_variants,
        "react_variant_count": len(react_variants),
        "react_variant_counts": react_counts,
        "dominant_react_variant_share": dominant_react_variant_share,
        "total_react_variant_instances": total_react_variants,
        "max_consecutive_react_variant_run": max_consecutive_react_variant_run,
        "adjacent_react_variant_repeat_rate": adjacent_react_variant_repeat_rate,
        "scene_signatures": scene_signature_variants,
        "scene_signature_count": len(scene_signature_variants),
        "scene_signature_counts": scene_signature_counts,
        "dominant_scene_signature_share": dominant_scene_signature_share,
        "total_scene_signature_instances": total_scene_signatures,
        "max_consecutive_scene_signature_run": max_consecutive_scene_signature_run,
        "adjacent_scene_signature_repeat_rate": adjacent_scene_signature_repeat_rate,
        "unsupported_layer_types": unsupported,
        "unsupported_layer_type_count": len(unsupported),
        "dominant_component_share": dominant_component_share,
        "total_component_instances": total_components,
    }


def structure_stats(manifest: Dict[str, Any], limits: Dict[str, Any]) -> Dict[str, Any]:
    beats = manifest.get("beats") or []
    if not beats:
        return {
            "checked_beat_count": 0,
            "weak_structure_beat_count": 0,
            "weak_structure_beat_rate": 0.0,
            "weak_structure_beat_ids": [],
            "short_structural_beat_count": 0,
            "short_structural_beat_ids": [],
            "min_structural_beat_sec": float(limits.get("minStructuralBeatSec", 1.2)),
        }

    structural_types = {
        "MediaFrame",
        "PromptAnswerCard",
        "HeroTitle",
        "LogoOutro",
        "BeforeAfter",
        "Stepper3",
        "Callout",
    }
    text_overlay_types = {"KineticWords", "LowerThird"}
    skip_intents = {"hook", "outro"}
    min_structural_beat_sec = float(limits.get("minStructuralBeatSec", 1.2))

    weak_ids: List[str] = []
    short_structural_ids: List[str] = []
    checked = 0

    for beat in beats:
        beat_id = str(beat.get("id") or "")
        intent = str(beat.get("intent") or "").lower()
        layer_types_raw = beat.get("layerTypes")
        layer_types = (
            [str(item).strip() for item in layer_types_raw if str(item).strip()]
            if isinstance(layer_types_raw, list)
            else []
        )

        if any(token in intent for token in skip_intents):
            continue

        checked += 1
        has_structural = any(layer_type in structural_types for layer_type in layer_types)
        has_text_overlay = any(layer_type in text_overlay_types for layer_type in layer_types)

        if (not has_structural) and has_text_overlay:
            weak_ids.append(beat_id)

        if has_structural:
            try:
                duration = max(0.0, float(beat.get("t1", 0.0) or 0.0) - float(beat.get("t0", 0.0) or 0.0))
            except (TypeError, ValueError):
                duration = 0.0
            if duration < min_structural_beat_sec:
                short_structural_ids.append(beat_id)

    weak_count = len(weak_ids)
    return {
        "checked_beat_count": checked,
        "weak_structure_beat_count": weak_count,
        "weak_structure_beat_rate": float(weak_count / checked) if checked > 0 else 0.0,
        "weak_structure_beat_ids": weak_ids,
        "short_structural_beat_count": len(short_structural_ids),
        "short_structural_beat_ids": short_structural_ids,
        "min_structural_beat_sec": min_structural_beat_sec,
    }


def no_element_gap_stats(manifest: Dict[str, Any], max_gap_sec: float = 3.0) -> Dict[str, Any]:
    beats = sorted((manifest.get("beats") or []), key=lambda b: float(b.get("t0", 0.0) or 0.0))
    meta = manifest.get("meta") or {}
    duration = float(meta.get("durationSec", 0.0) or 0.0)
    if duration <= 0:
        duration = max([float(b.get("t1", 0.0) or 0.0) for b in beats] + [0.0])

    intervals: List[List[float]] = []
    for beat in beats:
        try:
            t0 = max(0.0, float(beat.get("t0", 0.0) or 0.0))
            t1 = max(t0, float(beat.get("t1", t0) or t0))
        except (TypeError, ValueError):
            continue
        has_elements = bool(beat.get("hasRenderableElements"))
        if has_elements and t1 > t0:
            intervals.append([t0, t1])

    if not intervals:
        return {
            "max_no_element_gap_sec": duration,
            "gap_count": 1 if duration > 0 else 0,
            "violating_gap_count": 1 if duration > max_gap_sec else 0,
            "allowed_max_gap_sec": max_gap_sec,
            "pass": duration <= max_gap_sec,
        }

    intervals.sort(key=lambda x: x[0])
    merged: List[List[float]] = [intervals[0][:]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    gaps: List[float] = []
    cursor = 0.0
    for start, end in merged:
        if start > cursor:
            gaps.append(start - cursor)
        cursor = max(cursor, end)
    if duration > cursor:
        gaps.append(duration - cursor)

    max_gap = max(gaps) if gaps else 0.0
    violating_gap_count = sum(1 for gap in gaps if gap > max_gap_sec)
    return {
        "max_no_element_gap_sec": max_gap,
        "gap_count": len(gaps),
        "violating_gap_count": violating_gap_count,
        "allowed_max_gap_sec": max_gap_sec,
        "pass": violating_gap_count == 0,
    }


def highlight_stats(manifest: Dict[str, Any], limits: Dict[str, Any]) -> Dict[str, Any]:
    beats = manifest.get("beats") or []
    if not beats:
        return {
            "highlighted_word_count": 0,
            "highlighted_beat_count": 0,
            "stopword_highlight_count": 0,
            "stopword_highlight_rate": 0.0,
            "bad_highlight_beat_count": 0,
            "bad_highlight_beat_rate": 0.0,
            "bad_highlight_beat_ids": [],
        }

    stopwords = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "with",
    }
    min_len = int(limits.get("minHighlightWordLen", 3) or 3)
    highlighted_word_count = 0
    highlighted_beat_count = 0
    stopword_highlight_count = 0
    bad_highlight_beat_ids: List[str] = []

    for beat in beats:
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("id") or "")
        highlights_raw = beat.get("highlightedWords")
        highlights = (
            [str(item).strip() for item in highlights_raw if str(item).strip()]
            if isinstance(highlights_raw, list)
            else []
        )
        if not highlights:
            continue
        highlighted_beat_count += 1
        beat_has_bad = False
        for token in highlights:
            cleaned = token.strip(".,;:!?\"'()[]{}").lower()
            if not cleaned:
                continue
            highlighted_word_count += 1
            if len(cleaned) < min_len or cleaned in stopwords:
                stopword_highlight_count += 1
                beat_has_bad = True
        if beat_has_bad:
            bad_highlight_beat_ids.append(beat_id)

    stopword_highlight_rate = (
        float(stopword_highlight_count / highlighted_word_count)
        if highlighted_word_count > 0
        else 0.0
    )
    bad_highlight_beat_rate = (
        float(len(bad_highlight_beat_ids) / highlighted_beat_count)
        if highlighted_beat_count > 0
        else 0.0
    )
    return {
        "highlighted_word_count": highlighted_word_count,
        "highlighted_beat_count": highlighted_beat_count,
        "stopword_highlight_count": stopword_highlight_count,
        "stopword_highlight_rate": stopword_highlight_rate,
        "bad_highlight_beat_count": len(bad_highlight_beat_ids),
        "bad_highlight_beat_rate": bad_highlight_beat_rate,
        "bad_highlight_beat_ids": bad_highlight_beat_ids,
    }


def text_stats(manifest: Dict[str, Any], limits: Dict[str, Any]) -> Dict[str, Any]:
    beats = manifest.get("beats") or []
    blocks = [tb for tb in (manifest.get("textBlocks") or []) if bool(tb.get("isTextLayer", True))]

    max_chars = int(limits.get("maxCharsPerLine", 12))
    max_lines = int(limits.get("maxLines", 2))

    beat_by_id = {b.get("id"): b for b in beats}

    char_hits = 0
    line_hits = 0
    max_chars_per_line_seen = 0.0
    max_lines_seen = 0

    for block in blocks:
        beat = beat_by_id.get(block.get("beatId"), {})
        lines_count = int(beat.get("linesCount", 1) or 1)
        chars = int(block.get("chars", 0) or 0)
        chars_per_line = chars / max(1, lines_count)

        max_chars_per_line_seen = max(max_chars_per_line_seen, chars_per_line)
        max_lines_seen = max(max_lines_seen, lines_count)

        if chars_per_line <= max_chars:
            char_hits += 1
        if lines_count <= max_lines:
            line_hits += 1

    total = len(blocks)
    return {
        "total_blocks": total,
        "char_hit_rate": (char_hits / total) if total else 0.0,
        "line_hit_rate": (line_hits / total) if total else 0.0,
        "max_chars_per_line_seen": max_chars_per_line_seen,
        "max_lines_seen": max_lines_seen,
    }


def storyboard_stats(manifest: Dict[str, Any]) -> Dict[str, Any]:
    beats = manifest.get("beats") or []
    if not beats:
        return {
            "middle_low_energy_rate": 0.0,
            "middle_count": 0,
        }

    duration = max(float(b.get("t1", 0.0)) for b in beats) if beats else 0.0
    mid_start = duration * 0.35
    mid_end = duration * 0.75
    low_energy_modes = {"lowerThird", "outro"}

    middle = [
        b
        for b in beats
        if float(b.get("t0", 0.0)) >= mid_start and float(b.get("t1", 0.0)) <= mid_end
    ]
    low_energy = [
        b for b in middle if str(b.get("renderMode", "")).strip() in low_energy_modes
    ]

    return {
        "middle_low_energy_rate": (len(low_energy) / len(middle)) if middle else 0.0,
        "middle_count": len(middle),
    }


def _coverage_score(value: float, min_cov: float, max_cov: float) -> float:
    if min_cov <= value <= max_cov:
        return 1.0
    if value < min_cov:
        return max(0.0, value / max(min_cov, 1e-6))
    return max(0.0, max_cov / max(value, 1e-6))


def _percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    if len(arr) == 1:
        return float(arr[0])
    q = max(0.0, min(1.0, q))
    idx = (len(arr) - 1) * q
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(arr[lo])
    frac = idx - lo
    return float(arr[lo] * (1.0 - frac) + arr[hi] * frac)


def _effective_area_weight(layer_type: str, limits: Dict[str, Any]) -> float:
    defaults = {
        "MediaFrame": 0.62,
        "HeroTitle": 0.5,
        "LowerThird": 0.3,
        "KineticWords": 0.24,
        "PromptAnswerCard": 0.72,
        "LogoOutro": 0.64,
        "BeforeAfter": 0.32,
        "Stepper3": 0.24,
        "Callout": 0.44,
    }
    key = f"effectiveWeight{layer_type}"
    fallback = defaults.get(layer_type, 0.5)
    try:
        return float(limits.get(key, fallback))
    except (TypeError, ValueError):
        return float(fallback)


def _aligned_bbox_pair(
    bbox_a: Dict[str, float], bbox_b: Dict[str, float], tol_x: float, tol_y: float
) -> bool:
    ax = float(bbox_a.get("x", 0.0))
    ay = float(bbox_a.get("y", 0.0))
    aw = float(bbox_a.get("w", 0.0))
    ah = float(bbox_a.get("h", 0.0))
    bx = float(bbox_b.get("x", 0.0))
    by = float(bbox_b.get("y", 0.0))
    bw = float(bbox_b.get("w", 0.0))
    bh = float(bbox_b.get("h", 0.0))

    return any(
        [
            abs(ax - bx) <= tol_x,
            abs((ax + aw * 0.5) - (bx + bw * 0.5)) <= tol_x,
            abs((ax + aw) - (bx + bw)) <= tol_x,
            abs(ay - by) <= tol_y,
            abs((ay + ah * 0.5) - (by + bh * 0.5)) <= tol_y,
            abs((ay + ah) - (by + bh)) <= tol_y,
        ]
    )


def _bbox_overlap_ratio(bbox_a: Dict[str, float], bbox_b: Dict[str, float]) -> float:
    ax = float(bbox_a.get("x", 0.0))
    ay = float(bbox_a.get("y", 0.0))
    aw = float(bbox_a.get("w", 0.0))
    ah = float(bbox_a.get("h", 0.0))
    bx = float(bbox_b.get("x", 0.0))
    by = float(bbox_b.get("y", 0.0))
    bw = float(bbox_b.get("w", 0.0))
    bh = float(bbox_b.get("h", 0.0))
    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        return 0.0

    ix1 = max(ax, bx)
    iy1 = max(ay, by)
    ix2 = min(ax + aw, bx + bw)
    iy2 = min(ay + ah, by + bh)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    return float(inter / max(min(aw * ah, bw * bh), 1e-6))


def layout_stats(manifest: Dict[str, Any], limits: Dict[str, Any]) -> Dict[str, Any]:
    blocks = manifest.get("textBlocks") or []
    meta = manifest.get("meta") or {}

    width = float(meta.get("width", 1920) or 1920)
    height = float(meta.get("height", 1080) or 1080)
    frame_area = max(1.0, width * height)

    min_cov = float(limits.get("minContentCoverage", 0.22))
    max_cov = float(limits.get("maxContentCoverage", 0.72))
    target_center = float(limits.get("targetVisualCenterYPct", 0.52))
    max_center_dev = float(limits.get("maxVisualCenterDeviationPct", 0.18))
    target_center_x = float(limits.get("targetVisualCenterXPct", 0.5))
    max_center_dev_x = float(limits.get("maxVisualCenterDeviationXPct", 0.16))
    min_font = float(limits.get("minReadableFontPx", 22))
    min_beat_effective_cov = float(limits.get("minBeatEffectiveCoverage", 0.2))
    min_text_fill_ratio = float(limits.get("minTextFillRatio", 0.1))
    min_text_fill_ratio_p25 = float(limits.get("minTextFillRatioP25", 0.08))
    overlap_ratio_threshold = float(limits.get("overlapRatioThreshold", 0.08))
    severe_overlap_ratio_threshold = float(limits.get("severeOverlapRatioThreshold", 0.2))
    wrap_risk_line_multiplier = float(limits.get("wrapRiskLineMultiplier", 1.0))
    max_lines_default = int(limits.get("maxLines", 2) or 2)
    align_tol_x = width * float(limits.get("alignmentToleranceXPct", 0.02))
    align_tol_y = height * float(limits.get("alignmentToleranceYPct", 0.02))

    if not blocks:
        return {
            "block_count": 0,
            "coverage_ratio": 0.0,
            "beat_coverage_p25": 0.0,
            "beat_coverage_min": 0.0,
            "effective_coverage_ratio": 0.0,
            "effective_coverage_p25": 0.0,
            "effective_coverage_min": 0.0,
            "sparse_beat_rate": 1.0,
            "visual_center_y_pct": 0.0,
            "visual_center_x_pct": 0.0,
            "center_deviation": 1.0,
            "center_x_deviation": 1.0,
            "coverage_score": 0.0,
            "balance_score": 0.0,
            "balance_x_score": 0.0,
            "alignment_score": 0.0,
            "multi_block_beat_count": 0,
            "min_estimated_font_px": 0.0,
            "avg_estimated_font_px": 0.0,
            "readable_font_rate": 0.0,
            "lower_half_coverage_ratio": 0.0,
            "text_fill_ratio_mean": 0.0,
            "text_fill_ratio_p25": 0.0,
            "low_text_fill_block_rate": 1.0,
            "low_text_fill_beat_rate": 1.0,
            "low_text_fill_beat_ids": [],
            "overlap_pair_rate": 0.0,
            "overlap_beat_rate": 0.0,
            "overlap_beat_ids": [],
            "max_overlap_ratio": 0.0,
            "severe_overlap_beat_rate": 0.0,
            "severe_overlap_beat_ids": [],
            "wrap_risk_block_rate": 0.0,
            "wrap_risk_beat_rate": 0.0,
            "wrap_risk_beat_ids": [],
        }

    areas: List[float] = []
    weighted_centers_y: List[float] = []
    weighted_centers_x: List[float] = []
    lower_half_area = 0.0
    font_values: List[float] = []
    text_fill_values: List[float] = []
    beat_area: Dict[str, float] = {}
    beat_effective_area: Dict[str, float] = {}
    beat_text_fill_values: Dict[str, List[float]] = {}
    beat_bboxes: Dict[str, List[Dict[str, float]]] = {}
    beat_blocks: Dict[str, List[Dict[str, Any]]] = {}

    for block in blocks:
        bbox = block.get("bbox") or {}
        w = max(0.0, float(bbox.get("w", 0.0) or 0.0))
        h = max(0.0, float(bbox.get("h", 0.0) or 0.0))
        x = float(bbox.get("x", 0.0) or 0.0)
        y = float(bbox.get("y", 0.0) or 0.0)
        area = w * h
        if area <= 0:
            continue

        cx = x + w * 0.5
        cy = y + h * 0.5
        areas.append(area)
        weighted_centers_x.append(cx * area)
        weighted_centers_y.append(cy * area)
        beat_id = str(block.get("beatId") or "")
        if beat_id:
            beat_area[beat_id] = beat_area.get(beat_id, 0.0) + area
            layer_type = str(block.get("layerType") or "")
            weighted_area = area * _effective_area_weight(layer_type, limits)
            beat_effective_area[beat_id] = beat_effective_area.get(beat_id, 0.0) + weighted_area
            beat_bboxes.setdefault(beat_id, []).append(
                {
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                }
            )
            beat_blocks.setdefault(beat_id, []).append(block)
        lower_half_top = height * 0.5
        overlap_h = max(0.0, min(y + h, height) - max(y, lower_half_top))
        lower_half_area += w * overlap_h

        est_font = block.get("estimatedFontPx")
        if bool(block.get("isTextLayer", True)) and est_font is not None:
            try:
                est_font_value = float(est_font)
                font_values.append(est_font_value)
                chars = max(0.0, float(block.get("chars", 0) or 0))
                # Ignore extremely short labels when computing text-fill;
                # they are handled by coverage/structure metrics and otherwise create false positives.
                min_chars_for_fill = float(limits.get("minCharsForTextFill", 24))
                if chars >= min_chars_for_fill and w > 0 and h > 0:
                    avg_char_width = est_font_value * 0.52
                    line_height = est_font_value * 1.2
                    estimated_text_area = chars * avg_char_width * line_height * 0.54
                    fill_ratio = max(0.0, min(1.0, estimated_text_area / max(area, 1e-6)))
                    text_fill_values.append(fill_ratio)
                    if beat_id:
                        beat_text_fill_values.setdefault(beat_id, []).append(fill_ratio)
            except (TypeError, ValueError):
                pass

    total_area = float(sum(areas))
    if beat_area:
        per_beat_cov = [min(1.0, area / frame_area) for area in beat_area.values()]
        coverage_ratio = float(statistics.mean(per_beat_cov))
        beat_coverage_p25 = _percentile(per_beat_cov, 0.25)
        beat_coverage_min = min(per_beat_cov) if per_beat_cov else 0.0
    else:
        coverage_ratio = min(1.0, total_area / frame_area)
        beat_coverage_p25 = coverage_ratio
        beat_coverage_min = coverage_ratio

    beat_effective_coverage_map: Dict[str, float] = {}
    if beat_effective_area:
        beat_effective_coverage_map = {
            beat_id: min(1.0, area / frame_area) for beat_id, area in beat_effective_area.items()
        }
        per_beat_effective_cov = [
            beat_effective_coverage_map[beat_id] for beat_id in beat_effective_area.keys()
        ]
        effective_coverage_ratio = float(statistics.mean(per_beat_effective_cov))
        effective_coverage_p25 = _percentile(per_beat_effective_cov, 0.25)
        effective_coverage_min = min(per_beat_effective_cov) if per_beat_effective_cov else 0.0
        sparse_beat_ids = [
            beat_id
            for beat_id, cov in beat_effective_coverage_map.items()
            if cov < min_beat_effective_cov
        ]
        sparse_beats = len(sparse_beat_ids)
        sparse_beat_rate = float(sparse_beats / len(per_beat_effective_cov))
    else:
        effective_coverage_ratio = 0.0
        effective_coverage_p25 = 0.0
        effective_coverage_min = 0.0
        sparse_beat_ids = []
        sparse_beat_rate = 1.0

    visual_center_x = (sum(weighted_centers_x) / total_area) if total_area > 0 else 0.0
    visual_center_x_pct = visual_center_x / max(width, 1.0)
    visual_center_y = (sum(weighted_centers_y) / total_area) if total_area > 0 else 0.0
    visual_center_y_pct = visual_center_y / max(height, 1.0)
    center_deviation = abs(visual_center_y_pct - target_center)
    center_x_deviation = abs(visual_center_x_pct - target_center_x)
    balance_score = max(0.0, 1.0 - (center_deviation / max(max_center_dev, 1e-6)))
    balance_x_score = max(0.0, 1.0 - (center_x_deviation / max(max_center_dev_x, 1e-6)))
    coverage_score = _coverage_score(coverage_ratio, min_cov, max_cov)

    aligned_pairs = 0
    total_pairs = 0
    multi_block_beat_count = 0
    for beat_boxes in beat_bboxes.values():
        if len(beat_boxes) < 2:
            continue
        multi_block_beat_count += 1
        for i in range(len(beat_boxes)):
            for j in range(i + 1, len(beat_boxes)):
                total_pairs += 1
                if _aligned_bbox_pair(beat_boxes[i], beat_boxes[j], align_tol_x, align_tol_y):
                    aligned_pairs += 1
    alignment_score = float(aligned_pairs / total_pairs) if total_pairs > 0 else 0.5

    min_est_font = min(font_values) if font_values else 0.0
    avg_est_font = statistics.mean(font_values) if font_values else 0.0
    readable_hits = sum(1 for v in font_values if v >= min_font)
    readable_font_rate = (readable_hits / len(font_values)) if font_values else 0.0
    text_fill_ratio_mean = float(statistics.mean(text_fill_values)) if text_fill_values else 0.0
    text_fill_ratio_p25 = _percentile(text_fill_values, 0.25) if text_fill_values else 0.0
    low_text_fill_block_rate = (
        float(sum(1 for value in text_fill_values if value < min_text_fill_ratio) / len(text_fill_values))
        if text_fill_values
        else 1.0
    )
    beat_text_fill_avg = {
        beat_id: float(statistics.mean(values))
        for beat_id, values in beat_text_fill_values.items()
        if values
    }
    low_text_fill_beat_ids = [
        beat_id
        for beat_id, fill_ratio in beat_text_fill_avg.items()
        if fill_ratio < min_text_fill_ratio_p25
    ]
    low_text_fill_beat_rate = (
        float(len(low_text_fill_beat_ids) / len(beat_text_fill_avg)) if beat_text_fill_avg else 1.0
    )

    overlap_pairs = 0
    overlap_pairs_total = 0
    overlap_beat_ids: List[str] = []
    severe_overlap_beat_ids: List[str] = []
    max_overlap_ratio = 0.0
    text_like_types = {"LowerThird", "KineticWords", "HeroTitle"}
    structural_types = {"BeforeAfter", "Stepper3", "PromptAnswerCard", "Callout"}
    for beat_id, boxes in beat_bboxes.items():
        beat_items = beat_blocks.get(beat_id, [])
        beat_has_overlap = False
        beat_has_severe = False
        if len(boxes) < 2 or len(beat_items) < 2:
            continue
        for i in range(len(beat_items)):
            for j in range(i + 1, len(beat_items)):
                type_i = str(beat_items[i].get("layerType") or "")
                type_j = str(beat_items[j].get("layerType") or "")
                high_priority_pair = (
                    (type_i in text_like_types and type_j in structural_types)
                    or (type_j in text_like_types and type_i in structural_types)
                    or (type_i in structural_types and type_j in structural_types)
                )
                if not high_priority_pair:
                    continue
                overlap_pairs_total += 1
                ratio = _bbox_overlap_ratio(boxes[i], boxes[j])
                max_overlap_ratio = max(max_overlap_ratio, ratio)
                if ratio >= overlap_ratio_threshold:
                    overlap_pairs += 1
                    beat_has_overlap = True
                if ratio >= severe_overlap_ratio_threshold:
                    beat_has_severe = True
        if beat_has_overlap:
            overlap_beat_ids.append(beat_id)
        if beat_has_severe:
            severe_overlap_beat_ids.append(beat_id)
    overlap_pair_rate = (
        float(overlap_pairs / overlap_pairs_total) if overlap_pairs_total > 0 else 0.0
    )
    overlap_beat_rate = (
        float(len(overlap_beat_ids) / len(beat_bboxes)) if beat_bboxes else 0.0
    )
    severe_overlap_beat_rate = (
        float(len(severe_overlap_beat_ids) / len(beat_bboxes)) if beat_bboxes else 0.0
    )

    wrap_risk_block_hits = 0
    wrap_risk_beat_ids: List[str] = []
    text_block_count = 0
    for beat_id, beat_items in beat_blocks.items():
        beat_has_wrap_risk = False
        for block in beat_items:
            if not bool(block.get("isTextLayer", True)):
                continue
            text_block_count += 1
            chars = float(block.get("chars", 0) or 0)
            font_px = float(block.get("estimatedFontPx", 0) or 0)
            bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
            bbox_w = float(bbox.get("w", 0) or 0)
            if chars <= 0 or font_px <= 0 or bbox_w <= 0:
                continue
            capacity_chars_per_line = bbox_w / max(font_px * 0.52, 1e-6)
            est_lines = chars / max(capacity_chars_per_line, 1e-6)
            max_lines = int(block.get("maxLines") or max_lines_default)
            planned_lines = int(block.get("plannedLines") or 0)
            if planned_lines > 0 and planned_lines <= max_lines:
                continue
            if est_lines > max_lines * wrap_risk_line_multiplier:
                wrap_risk_block_hits += 1
                beat_has_wrap_risk = True
        if beat_has_wrap_risk:
            wrap_risk_beat_ids.append(beat_id)
    wrap_risk_block_rate = (
        float(wrap_risk_block_hits / text_block_count) if text_block_count > 0 else 0.0
    )
    wrap_risk_beat_rate = (
        float(len(wrap_risk_beat_ids) / len(beat_blocks)) if beat_blocks else 0.0
    )

    return {
        "block_count": len(blocks),
        "coverage_ratio": coverage_ratio,
        "beat_coverage_p25": beat_coverage_p25,
        "beat_coverage_min": beat_coverage_min,
        "effective_coverage_ratio": effective_coverage_ratio,
        "effective_coverage_p25": effective_coverage_p25,
        "effective_coverage_min": effective_coverage_min,
        "beat_effective_coverage_map": beat_effective_coverage_map,
        "sparse_beat_rate": sparse_beat_rate,
        "sparse_beat_ids": sparse_beat_ids,
        "visual_center_x_pct": visual_center_x_pct,
        "visual_center_y_pct": visual_center_y_pct,
        "center_deviation": center_deviation,
        "center_x_deviation": center_x_deviation,
        "coverage_score": coverage_score,
        "balance_score": balance_score,
        "balance_x_score": balance_x_score,
        "alignment_score": alignment_score,
        "multi_block_beat_count": multi_block_beat_count,
        "min_estimated_font_px": min_est_font,
        "avg_estimated_font_px": avg_est_font,
        "readable_font_rate": readable_font_rate,
        "lower_half_coverage_ratio": (lower_half_area / total_area) if total_area > 0 else 0.0,
        "text_fill_ratio_mean": text_fill_ratio_mean,
        "text_fill_ratio_p25": text_fill_ratio_p25,
        "low_text_fill_block_rate": low_text_fill_block_rate,
        "low_text_fill_beat_rate": low_text_fill_beat_rate,
        "low_text_fill_beat_ids": low_text_fill_beat_ids,
        "overlap_pair_rate": overlap_pair_rate,
        "overlap_beat_rate": overlap_beat_rate,
        "overlap_beat_ids": overlap_beat_ids,
        "max_overlap_ratio": max_overlap_ratio,
        "severe_overlap_beat_rate": severe_overlap_beat_rate,
        "severe_overlap_beat_ids": severe_overlap_beat_ids,
        "wrap_risk_block_rate": wrap_risk_block_rate,
        "wrap_risk_beat_rate": wrap_risk_beat_rate,
        "wrap_risk_beat_ids": wrap_risk_beat_ids,
    }
