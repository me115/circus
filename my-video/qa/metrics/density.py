from __future__ import annotations

from typing import Any, Dict, List, Optional


TRAILING_STOPWORDS = {
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
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def evaluate_density(
    manifest: Dict[str, Any],
    quality: Dict[str, Any],
    layout_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    limits = quality.get("limits", {}) if isinstance(quality, dict) else {}
    max_words_per_line = int(limits.get("maxWordsPerLine", 7) or 7)
    max_lines = int(limits.get("maxLines", 2) or 2)
    min_component_coverage = float(limits.get("minComponentCoverage", 0.24) or 0.24)
    min_beat_coverage = float(limits.get("minBeatEffectiveCoverage", 0.2) or 0.2)
    min_effective_coverage_p25 = float(limits.get("minEffectiveCoverageP25", 0.26) or 0.26)
    min_lower_half_coverage = float(limits.get("minLowerHalfCoverage", 0.24) or 0.24)
    max_widow_words = int(limits.get("maxWidowWords", 2) or 2)
    max_line_word_imbalance = int(limits.get("maxLineWordImbalance", 4) or 4)
    max_bad_line_break_rate = float(limits.get("maxBadLineBreakRate", 0.12) or 0.12)
    max_hook_widow_words = int(limits.get("maxHookWidowWords", max_widow_words) or max_widow_words)
    max_hook_line_word_imbalance = int(
        limits.get("maxHookLineWordImbalance", max(2, max_line_word_imbalance - 1))
        or max(2, max_line_word_imbalance - 1)
    )
    min_text_beat_sec = float(limits.get("minTextBeatSec", 2.2) or 2.2)
    min_words_for_text_beat_sec = int(limits.get("minWordsForTextBeatSec", 5) or 5)
    max_words_per_sec = float(limits.get("maxWordsPerSec", 4.0) or 4.0)
    max_short_hold_beat_rate = float(limits.get("maxShortHoldBeatRate", 0.1) or 0.1)
    max_fragment_line_rate = float(limits.get("maxFragmentLineRate", 0.08) or 0.08)

    per_beat: List[Dict[str, Any]] = []
    density = manifest.get("density", {}) if isinstance(manifest, dict) else {}
    raw_beats = density.get("perBeat", []) if isinstance(density, dict) else []
    if isinstance(raw_beats, list):
        per_beat = [item for item in raw_beats if isinstance(item, dict)]

    if not per_beat:
        return {
            "score": 0.0,
            "overflow_count": 0,
            "total_beats": 0,
            "max_words_per_line": max_words_per_line,
            "max_lines": max_lines,
            "fail_reasons": ["density.perBeat missing"],
            "overflow_beats": [],
        }

    overflow_beats: List[str] = []
    long_line_beats: List[str] = []
    line_count_beats: List[str] = []
    bad_line_break_beats: List[str] = []
    widow_line_beats: List[str] = []
    imbalance_line_beats: List[str] = []
    hook_bad_line_break_beats: List[str] = []
    short_hold_beats: List[str] = []
    fast_words_per_sec_beats: List[str] = []
    fragment_line_beats: List[str] = []
    beats_raw = manifest.get("beats", []) if isinstance(manifest, dict) else []
    beat_intent_map = {
        str(item.get("id") or ""): str(item.get("intent") or "").lower()
        for item in beats_raw
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    beat_duration_map = {}
    for item in beats_raw:
        if not isinstance(item, dict):
            continue
        beat_id = str(item.get("id") or "").strip()
        if not beat_id:
            continue
        try:
            t0 = float(item.get("t0", 0.0) or 0.0)
            t1 = float(item.get("t1", t0) or t0)
        except (TypeError, ValueError):
            t0, t1 = 0.0, 0.0
        beat_duration_map[beat_id] = max(0.0, t1 - t0)

    for item in per_beat:
        beat_id = str(item.get("beatId") or "")
        words = int(item.get("words") or 0)
        lines = int(item.get("lines") or 1)
        beat_max_words_per_line = int(item.get("maxWordsPerLine") or max_words_per_line)
        beat_max_lines = int(item.get("maxLines") or max_lines)
        overflow = bool(item.get("overflow"))
        words_per_line = float(words / max(lines, 1))

        if overflow:
            overflow_beats.append(beat_id)
        if words_per_line > beat_max_words_per_line:
            long_line_beats.append(beat_id)
        if lines > beat_max_lines:
            line_count_beats.append(beat_id)
        beat_duration = float(beat_duration_map.get(beat_id, 0.0))
        if words >= min_words_for_text_beat_sec and beat_duration > 0:
            if beat_duration < min_text_beat_sec:
                short_hold_beats.append(beat_id)
            if float(words / max(beat_duration, 1e-6)) > max_words_per_sec:
                fast_words_per_sec_beats.append(beat_id)
        raw_text = str(item.get("text") or "")
        raw_words = [token.strip(".,;:!?\"'()[]{}").lower() for token in raw_text.split(" ") if token.strip()]
        likely_truncated = overflow or words > (beat_max_words_per_line * beat_max_lines)
        if likely_truncated and raw_words and raw_words[-1] in TRAILING_STOPWORDS:
            fragment_line_beats.append(beat_id)
        wrapped_lines_raw = item.get("wrappedLines")
        wrapped_lines = wrapped_lines_raw if isinstance(wrapped_lines_raw, list) else []
        line_word_counts = [
            len([w for w in str(line).split(" ") if w.strip()])
            for line in wrapped_lines
            if str(line).strip()
        ]
        intent = beat_intent_map.get(beat_id, "")
        is_hook = "hook" in intent
        if len(line_word_counts) >= 2:
            min_words = min(line_word_counts)
            max_words = max(line_word_counts)
            last_words = line_word_counts[-1]
            has_widow = words > beat_max_words_per_line and last_words <= max_widow_words
            has_imbalance = (max_words - min_words) > max_line_word_imbalance
            hook_has_widow = is_hook and last_words <= max_hook_widow_words
            hook_has_imbalance = is_hook and (max_words - min_words) > max_hook_line_word_imbalance
            if has_widow:
                widow_line_beats.append(beat_id)
            if has_imbalance:
                imbalance_line_beats.append(beat_id)
            if has_widow or has_imbalance:
                bad_line_break_beats.append(beat_id)
            if hook_has_widow or hook_has_imbalance:
                hook_bad_line_break_beats.append(beat_id)

    total = len(per_beat)
    overflow_count = len(set(overflow_beats))
    long_line_count = len(set(long_line_beats))
    line_count_violations = len(set(line_count_beats))
    bad_line_break_count = len(set(bad_line_break_beats))
    widow_line_count = len(set(widow_line_beats))
    imbalance_line_count = len(set(imbalance_line_beats))
    hook_bad_line_break_count = len(set(hook_bad_line_break_beats))
    short_hold_beat_count = len(set(short_hold_beats))
    fast_words_per_sec_count = len(set(fast_words_per_sec_beats))
    fragment_line_count = len(set(fragment_line_beats))

    fail_reasons: List[str] = []
    if overflow_count > 0:
        fail_reasons.append(f"{overflow_count} beats overflow text density")
    if long_line_count > 0:
        fail_reasons.append(f"{long_line_count} beats exceed words-per-line")
    if line_count_violations > 0:
        fail_reasons.append(f"{line_count_violations} beats exceed max lines")
    if bad_line_break_count > 0:
        fail_reasons.append(f"{bad_line_break_count} beats have awkward line breaks")
    if hook_bad_line_break_count > 0:
        fail_reasons.append(f"{hook_bad_line_break_count} hook beats have awkward line breaks")
    if short_hold_beat_count > 0:
        fail_reasons.append(f"{short_hold_beat_count} beats too short for reading")
    if fast_words_per_sec_count > 0:
        fail_reasons.append(f"{fast_words_per_sec_count} beats too dense in time")
    if fragment_line_count > 0:
        fail_reasons.append(f"{fragment_line_count} beats end with fragment stopwords")

    overflow_rate = overflow_count / max(total, 1)
    long_line_rate = long_line_count / max(total, 1)
    line_rate = line_count_violations / max(total, 1)
    bad_line_break_rate = bad_line_break_count / max(total, 1)
    short_hold_beat_rate = short_hold_beat_count / max(total, 1)
    fragment_line_rate = fragment_line_count / max(total, 1)

    meta = manifest.get("meta", {}) if isinstance(manifest, dict) else {}
    width = int(meta.get("width") or 1080)
    height = int(meta.get("height") or 1920)
    frame_area = float(max(1, width * height))
    blocks = manifest.get("textBlocks", []) if isinstance(manifest, dict) else []
    beat_coverage: Dict[str, float] = {}
    lower_half_area = 0.0
    total_block_area = 0.0
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
            bx = float(bbox.get("x", 0) or 0)
            by = float(bbox.get("y", 0) or 0)
            bw = float(bbox.get("w", 0) or 0)
            bh = float(bbox.get("h", 0) or 0)
            if bw <= 0 or bh <= 0:
                continue
            area = max(0.0, bw * bh)
            total_block_area += area
            beat_id = str(block.get("beatId") or "")
            if beat_id:
                beat_coverage[beat_id] = beat_coverage.get(beat_id, 0.0) + area

            top = by
            bottom = by + bh
            lower_start = height * 0.5
            if bottom > lower_start:
                overlap_top = max(top, lower_start)
                overlap_h = max(0.0, bottom - overlap_top)
                lower_half_area += overlap_h * bw

    beat_ids = [str(item.get("beatId") or "") for item in per_beat]
    beat_cov_values = [beat_coverage.get(beat_id, 0.0) / frame_area for beat_id in beat_ids]
    coverage_mean = float(sum(beat_cov_values) / max(len(beat_cov_values), 1))
    sparse_beats = [
        beat_id
        for beat_id in beat_ids
        if (beat_coverage.get(beat_id, 0.0) / frame_area) < min_beat_coverage
    ]
    sparse_rate = float(len(set(sparse_beats)) / max(len(beat_ids), 1))
    lower_half_ratio = float(lower_half_area / max(total_block_area, 1.0))

    layout_metrics = layout_metrics or {}
    layout_sparse_rate = float(layout_metrics.get("sparse_beat_rate", sparse_rate) or sparse_rate)
    layout_effective_cov_p25 = float(
        layout_metrics.get("effective_coverage_p25", coverage_mean) or coverage_mean
    )
    layout_sparse_ids_raw = layout_metrics.get("sparse_beat_ids")
    layout_sparse_ids = (
        [str(item) for item in layout_sparse_ids_raw if str(item).strip()]
        if isinstance(layout_sparse_ids_raw, list)
        else []
    )
    sparse_rate = max(sparse_rate, layout_sparse_rate)
    if layout_sparse_ids:
        sparse_beats = sorted(set(sparse_beats).union(layout_sparse_ids))

    if coverage_mean < min_component_coverage:
        fail_reasons.append(
            f"coverage mean {coverage_mean:.2f} < minComponentCoverage {min_component_coverage:.2f}"
        )
    if layout_effective_cov_p25 < min_effective_coverage_p25:
        fail_reasons.append(
            f"effective coverage p25 {layout_effective_cov_p25:.2f} < minEffectiveCoverageP25 {min_effective_coverage_p25:.2f}"
        )
    if lower_half_ratio < min_lower_half_coverage:
        fail_reasons.append(
            f"lower-half coverage {lower_half_ratio:.2f} < minLowerHalfCoverage {min_lower_half_coverage:.2f}"
        )
    if sparse_rate > 0.0:
        fail_reasons.append(f"sparse beats {len(set(sparse_beats))}/{len(beat_ids)}")
    if bad_line_break_rate > max_bad_line_break_rate:
        fail_reasons.append(
            f"bad line-break rate {bad_line_break_rate:.2f} > maxBadLineBreakRate {max_bad_line_break_rate:.2f}"
        )
    if short_hold_beat_rate > max_short_hold_beat_rate:
        fail_reasons.append(
            f"short-hold beat rate {short_hold_beat_rate:.2f} > maxShortHoldBeatRate {max_short_hold_beat_rate:.2f}"
        )
    if fragment_line_rate > max_fragment_line_rate:
        fail_reasons.append(
            f"fragment line rate {fragment_line_rate:.2f} > maxFragmentLineRate {max_fragment_line_rate:.2f}"
        )

    score = 100.0 - overflow_rate * 45.0 - long_line_rate * 25.0 - line_rate * 10.0
    score -= min(22.0, bad_line_break_rate * 70.0)
    score -= min(20.0, short_hold_beat_rate * 70.0)
    score -= min(14.0, fragment_line_rate * 70.0)
    if coverage_mean < min_component_coverage:
        score -= min(20.0, (min_component_coverage - coverage_mean) * 120.0)
    if layout_effective_cov_p25 < min_effective_coverage_p25:
        score -= min(20.0, (min_effective_coverage_p25 - layout_effective_cov_p25) * 120.0)
    if lower_half_ratio < min_lower_half_coverage:
        score -= min(15.0, (min_lower_half_coverage - lower_half_ratio) * 90.0)
    score -= min(25.0, sparse_rate * 55.0)
    score = max(0.0, min(100.0, score))

    return {
        "score": score,
        "overflow_count": overflow_count,
        "total_beats": total,
        "max_words_per_line": max_words_per_line,
        "max_lines": max_lines,
        "coverage_mean": coverage_mean,
        "effective_coverage_p25": layout_effective_cov_p25,
        "sparse_beat_rate": sparse_rate,
        "sparse_beats": sorted(set(sparse_beats)),
        "lower_half_coverage_ratio": lower_half_ratio,
        "bad_line_break_count": bad_line_break_count,
        "bad_line_break_rate": bad_line_break_rate,
        "bad_line_break_beats": sorted(set(bad_line_break_beats)),
        "hook_bad_line_break_count": hook_bad_line_break_count,
        "hook_bad_line_break_beats": sorted(set(hook_bad_line_break_beats)),
        "short_hold_beat_count": short_hold_beat_count,
        "short_hold_beat_rate": short_hold_beat_rate,
        "short_hold_beats": sorted(set(short_hold_beats)),
        "fast_words_per_sec_count": fast_words_per_sec_count,
        "fast_words_per_sec_beats": sorted(set(fast_words_per_sec_beats)),
        "fragment_line_count": fragment_line_count,
        "fragment_line_rate": fragment_line_rate,
        "fragment_line_beats": sorted(set(fragment_line_beats)),
        "widow_line_count": widow_line_count,
        "imbalance_line_count": imbalance_line_count,
        "fail_reasons": fail_reasons,
        "overflow_beats": sorted(
            {
                *overflow_beats,
                *long_line_beats,
                *line_count_beats,
                *bad_line_break_beats,
                *short_hold_beats,
                *fast_words_per_sec_beats,
                *fragment_line_beats,
            }
        ),
    }
