from __future__ import annotations

import json
import statistics
from typing import Any, Dict, List, Optional


def load_manifest(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_area_check(
    text_blocks: List[Dict[str, Any]], margins: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    violations = [tb for tb in text_blocks if bool(tb.get("safeMarginViolation"))]
    return {
        "violations": len(violations),
        "total": len(text_blocks),
        "rate": (len(violations) / len(text_blocks)) if text_blocks else 0.0,
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


def diversity_stats(manifest: Dict[str, Any]) -> Dict[str, Any]:
    summary = manifest.get("effectsSummary") or {}
    transition_types = list(summary.get("transitionTypesUsed") or [])
    motion_recipes = list(summary.get("motionRecipesUsed") or [])

    return {
        "transition_types": transition_types,
        "transition_type_count": len(transition_types),
        "motion_recipes": motion_recipes,
        "motion_recipe_count": len(motion_recipes),
    }


def text_stats(manifest: Dict[str, Any], limits: Dict[str, Any]) -> Dict[str, Any]:
    beats = manifest.get("beats") or []
    blocks = manifest.get("textBlocks") or []

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
