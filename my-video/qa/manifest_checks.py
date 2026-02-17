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
        "MediaFrame": 0.58,
        "HeroTitle": 0.5,
        "LowerThird": 0.42,
        "KineticWords": 0.33,
        "PromptAnswerCard": 0.72,
        "LogoOutro": 0.64,
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
        }

    areas: List[float] = []
    weighted_centers_y: List[float] = []
    weighted_centers_x: List[float] = []
    lower_half_area = 0.0
    font_values: List[float] = []
    beat_area: Dict[str, float] = {}
    beat_effective_area: Dict[str, float] = {}
    beat_bboxes: Dict[str, List[Dict[str, float]]] = {}

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
        lower_half_top = height * 0.5
        overlap_h = max(0.0, min(y + h, height) - max(y, lower_half_top))
        lower_half_area += w * overlap_h

        est_font = block.get("estimatedFontPx")
        if bool(block.get("isTextLayer", True)) and est_font is not None:
            try:
                font_values.append(float(est_font))
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

    if beat_effective_area:
        per_beat_effective_cov = [
            min(1.0, area / frame_area) for area in beat_effective_area.values()
        ]
        effective_coverage_ratio = float(statistics.mean(per_beat_effective_cov))
        effective_coverage_p25 = _percentile(per_beat_effective_cov, 0.25)
        effective_coverage_min = min(per_beat_effective_cov) if per_beat_effective_cov else 0.0
        sparse_beats = sum(1 for v in per_beat_effective_cov if v < min_beat_effective_cov)
        sparse_beat_rate = float(sparse_beats / len(per_beat_effective_cov))
    else:
        effective_coverage_ratio = 0.0
        effective_coverage_p25 = 0.0
        effective_coverage_min = 0.0
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

    return {
        "block_count": len(blocks),
        "coverage_ratio": coverage_ratio,
        "beat_coverage_p25": beat_coverage_p25,
        "beat_coverage_min": beat_coverage_min,
        "effective_coverage_ratio": effective_coverage_ratio,
        "effective_coverage_p25": effective_coverage_p25,
        "effective_coverage_min": effective_coverage_min,
        "sparse_beat_rate": sparse_beat_rate,
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
    }
