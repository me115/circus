from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Patch = Dict[str, Any]


def _deep_get(obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _add_patch(
    patches: List[Patch],
    target_file: str,
    path: str,
    value: Any,
    reason: str,
    op: str = "replace",
) -> None:
    patches.append(
        {
            "target_file": target_file,
            "op": op,
            "path": path,
            "value": value,
            "reason": reason,
        }
    )


def _dedupe_patches(patches: List[Patch]) -> List[Patch]:
    seen = set()
    result: List[Patch] = []
    for patch in patches:
        key = (
            patch.get("target_file"),
            patch.get("path"),
            patch.get("op", "replace"),
            json.dumps(patch.get("value"), sort_keys=True),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(patch)
    return result


def _next_beat_id(beats: List[Dict[str, Any]]) -> str:
    nums: List[int] = []
    for beat in beats:
        bid = str(beat.get("id") or "")
        if bid.startswith("b") and bid[1:].isdigit():
            nums.append(int(bid[1:]))
    if not nums:
        return "b01"
    return f"b{max(nums) + 1:02d}"


def _truncate_line_by_words(line: str, max_words: int) -> str:
    words = [w for w in (line or "").replace("\n", " ").split(" ") if w.strip()]
    trailing_stopwords = {
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
    kept = words if len(words) <= max_words else words[:max_words]
    while len(kept) > 3:
        tail = kept[-1].strip(".,;:!?\"'()[]{}").lower()
        if tail not in trailing_stopwords:
            break
        kept = kept[:-1]
    return " ".join(kept).rstrip(".,;:!?") + "."


def _tighten_hook_line(line: str, max_words: int) -> str:
    text = (line or "").strip()
    lowered = text.lower()
    if "meaning" in lowered and "keyword" in lowered:
        candidate = "Search by meaning, not keywords."
        if len([w for w in candidate.split(" ") if w.strip()]) <= max_words:
            return candidate
    return _truncate_line_by_words(text, max_words)


def _split_overflow_beats(
    beats: List[Dict[str, Any]],
    overflow_ids: List[str],
    max_words: int,
    strict_line_break_ids: Optional[List[str]] = None,
    strict_max_words: Optional[int] = None,
) -> List[Dict[str, Any]]:
    if not beats:
        return beats

    overflow_set = set(overflow_ids)
    strict_set = set(strict_line_break_ids or [])
    strict_word_limit = int(strict_max_words or max_words)
    updated: List[Dict[str, Any]] = []
    for beat in beats:
        beat_id = str(beat.get("id") or "")
        line = str(beat.get("line") or beat.get("text") or "").strip()
        t0 = _safe_float(beat.get("t0"), 0.0)
        t1 = _safe_float(beat.get("t1"), t0)
        dur = max(0.2, t1 - t0)

        if beat_id not in overflow_set:
            updated.append(beat)
            continue

        words = [w for w in line.split() if w.strip()]
        if beat_id in strict_set and len(words) > strict_word_limit:
            intent = str(beat.get("intent") or "").lower()
            is_hook_intent = "hook" in intent
            if (not is_hook_intent) and dur >= 3.5 and len(words) >= strict_word_limit + 1:
                mid = t0 + dur / 2.0
                half = max(1, len(words) // 2)
                line_a = _truncate_line_by_words(" ".join(words[:half]), strict_word_limit)
                line_b = _truncate_line_by_words(" ".join(words[half:]), strict_word_limit)
                updated.append(
                    {
                        **beat,
                        "line": line_a,
                        "text": line_a,
                        "t0": round(t0, 3),
                        "t1": round(mid, 3),
                    }
                )
                updated.append(
                    {
                        **beat,
                        "id": f"{beat_id}_s2",
                        "line": line_b,
                        "text": line_b,
                        "t0": round(mid, 3),
                        "t1": round(t1, 3),
                    }
                )
            else:
                tightened = (
                    _tighten_hook_line(line, strict_word_limit)
                    if is_hook_intent
                    else _truncate_line_by_words(line, strict_word_limit)
                )
                updated.append(
                    {
                        **beat,
                        "line": tightened,
                        "text": tightened,
                    }
                )
            continue

        if dur >= 3.5 and len(words) > max_words:
            mid = t0 + dur / 2.0
            half = max(1, len(words) // 2)
            line_a = " ".join(words[:half])
            line_b = " ".join(words[half:])
            updated.append({
                **beat,
                "line": _truncate_line_by_words(line_a, max_words),
                "text": _truncate_line_by_words(line_a, max_words),
                "t0": round(t0, 3),
                "t1": round(mid, 3),
            })
            updated.append({
                **beat,
                "id": f"{beat_id}_s2",
                "line": _truncate_line_by_words(line_b, max_words),
                "text": _truncate_line_by_words(line_b, max_words),
                "t0": round(mid, 3),
                "t1": round(t1, 3),
            })
        else:
            shortened = _truncate_line_by_words(line, max_words)
            updated.append({
                **beat,
                "line": shortened,
                "text": shortened,
            })

    return updated


def _normalize_backdrops(
    beats: List[Dict[str, Any]],
    target_preset: str = "gemini",
    max_intensity_step: float = 0.08,
) -> List[Dict[str, Any]]:
    if not beats:
        return beats

    updated: List[Dict[str, Any]] = []
    prev_intensity = 0.82
    for beat in beats:
        beat_copy = dict(beat)
        scene = beat_copy.get("scene")
        scene = dict(scene) if isinstance(scene, dict) else {}
        backdrop = scene.get("backdrop")
        backdrop = dict(backdrop) if isinstance(backdrop, dict) else {}
        raw_intensity = _safe_float(backdrop.get("intensity"), prev_intensity)
        clamped = max(0.55, min(0.95, raw_intensity))
        if abs(clamped - prev_intensity) > max_intensity_step:
            clamped = prev_intensity + max_intensity_step if clamped > prev_intensity else prev_intensity - max_intensity_step
        clamped = max(0.55, min(0.95, clamped))
        prev_intensity = clamped
        scene["backdrop"] = {
            "preset": target_preset,
            "animate": True,
            "intensity": round(clamped, 3),
        }
        beat_copy["scene"] = scene
        updated.append(beat_copy)
    return updated


def _ensure_structure_sections(
    beats: List[Dict[str, Any]],
    missing_sections: List[str],
) -> List[Dict[str, Any]]:
    if not beats:
        return beats

    result = list(beats)
    next_id = _next_beat_id(result)

    def _push_with_new_id(payload: Dict[str, Any]) -> None:
        nonlocal next_id
        payload = dict(payload)
        payload["id"] = next_id
        result.append(payload)
        current = int(next_id[1:]) if next_id[1:].isdigit() else 1
        next_id = f"b{current + 1:02d}"

    if "hook" in missing_sections:
        _push_with_new_id(
            {
                "t0": 0.0,
                "t1": 4.0,
                "intent": "hook_title",
                "line": "Search by meaning, not just keywords.",
            }
        )

    if "example" in missing_sections:
        _push_with_new_id(
            {
                "t0": 40.0,
                "t1": 44.0,
                "intent": "example_prompt",
                "line": "Example: ask one question and retrieve the best docs.",
            }
        )

    if "recap" in missing_sections:
        _push_with_new_id(
            {
                "t0": 52.0,
                "t1": 56.0,
                "intent": "recap_slogan",
                "line": "Keywords find matches. Vectors find intent.",
            }
        )

    result.sort(key=lambda b: _safe_float(b.get("t0"), 0.0))
    return result


def generate_patch_suggestions(
    report: Dict[str, Any],
    quality: Dict[str, Any],
    spec: Dict[str, Any],
    quality_path: str = "src/config/quality.json",
    spec_path: str = "src/specs/skill.timeline.json",
) -> List[Patch]:
    patches: List[Patch] = []

    metrics = report.get("metrics", {}) if isinstance(report, dict) else {}
    manifest = metrics.get("manifest", {}) if isinstance(metrics.get("manifest"), dict) else {}
    video_metrics = metrics.get("video", {}) if isinstance(metrics.get("video"), dict) else {}
    audio = metrics.get("audio", {}) if isinstance(metrics.get("audio"), dict) else {}
    gate_checks = _deep_get(report, "gate", "checks", default={})
    gate_checks = gate_checks if isinstance(gate_checks, dict) else {}

    stylekit_path = "src/style/stylekit.json"
    motionkit_path = "src/style/motionkit.json"

    beats = list(spec.get("beats") or []) if isinstance(spec, dict) else []
    density_metric = manifest.get("density_metric", {}) if isinstance(manifest, dict) else {}
    narrative_metric = manifest.get("narrative_metric", {}) if isinstance(manifest, dict) else {}
    motion_metric = manifest.get("motion_consistency_metric", {}) if isinstance(manifest, dict) else {}
    layout_metric = manifest.get("layout", {}) if isinstance(manifest, dict) else {}

    # P0: 安全与合规
    safe_violations = int(_deep_get(manifest, "safe", "violations", default=0) or 0)
    video_w = _safe_float(_deep_get(quality, "video", "width", default=1920), 1920)
    video_h = _safe_float(_deep_get(quality, "video", "height", default=1080), 1080)
    is_portrait = video_h > video_w
    bottom_safe = 0.22 if is_portrait else 0.12
    if safe_violations > 0 or gate_checks.get("safe_area") is False:
        lower_third_y = 0.74 if is_portrait else 0.7
        _add_patch(
            patches,
            quality_path,
            "/layout/lowerThirdYPct",
            lower_third_y,
            "P0 safe-area violation: move lower-third upward.",
        )
        _add_patch(
            patches,
            quality_path,
            "/layout/kineticYPct",
            0.58,
            "P0 safe-area violation: move kinetic text upward.",
        )
        _add_patch(
            patches,
            stylekit_path,
            "/safeArea/bottomPct",
            bottom_safe,
            "P0 safe-area violation: keep stylekit bottom safe area consistent.",
        )
        _add_patch(
            patches,
            quality_path,
            "/safeArea/marginBottomPct",
            bottom_safe,
            "P0 safe-area violation: align QA safe area with stylekit.",
        )

    lufs = audio.get("input_i_lufs")
    min_lufs = _safe_float(_deep_get(quality, "audio", "minLUFS", default=-18.0), -18.0)
    max_lufs = _safe_float(_deep_get(quality, "audio", "maxLUFS", default=-14.0), -14.0)
    if lufs is not None:
        lufs_val = _safe_float(lufs, -16.0)
        if lufs_val < min_lufs or lufs_val > max_lufs:
            _add_patch(
                patches,
                quality_path,
                "/postAudioNormalize/enabled",
                True,
                "P0 loudness out of range: enable post loudnorm normalization.",
            )

    max_low_info_run = _safe_float(_deep_get(report, "metrics", "video", "maxLowInfoRunSec", default=0.0), 0.0)
    max_low_info_run_gate = _safe_float(_deep_get(quality, "limits", "maxLowInfoRunSecGate", default=1.5), 1.5)
    low_info_beat_ids = _deep_get(report, "metrics", "video", "beatLowInfoBeatIds", default=[])
    low_info_beat_ids = [str(bid) for bid in (low_info_beat_ids or []) if str(bid).strip()]
    if max_low_info_run > max_low_info_run_gate and beats:
        if low_info_beat_ids:
            patched_beats: List[Dict[str, Any]] = []
            target_ids = set(low_info_beat_ids)
            for beat in beats:
                beat_id = str(beat.get("id") or "")
                if beat_id in target_ids:
                    patched_beats.append({**beat, "intent": "pipeline_flow"})
                else:
                    patched_beats.append(beat)
            _add_patch(
                patches,
                spec_path,
                "/beats",
                patched_beats,
                "P0 low-info run detected: upgrade weak beats to pipeline_flow scenes.",
            )
        else:
            _add_patch(
                patches,
                quality_path,
                "/layout/mediaPadYPct",
                0.1,
                "P0 low-info run detected: enlarge media area vertically.",
            )

    beat_intents = _deep_get(manifest, "beat_intents", default={})
    beat_intents = beat_intents if isinstance(beat_intents, dict) else {}
    beat_cov_layout = layout_metric.get("beat_effective_coverage_map")
    beat_cov_layout = beat_cov_layout if isinstance(beat_cov_layout, dict) else {}
    beat_cov_video = video_metrics.get("beatForegroundCoverageP25")
    beat_cov_video = beat_cov_video if isinstance(beat_cov_video, dict) else {}
    beat_cov = beat_cov_layout or beat_cov_video
    min_structural_beat_cov_gate = _safe_float(
        _deep_get(quality, "limits", "minStructuralBeatCoverageP25Gate", default=0.045), 0.045
    )
    structural_intents = {"how_steps", "pipeline_flow", "pipeline_3", "problem_compare"}
    low_structural_ids: List[str] = []
    for beat_id, intent in beat_intents.items():
        if str(intent) not in structural_intents:
            continue
        cov = _safe_float(beat_cov.get(str(beat_id)), 0.0)
        if cov < min_structural_beat_cov_gate:
            low_structural_ids.append(str(beat_id))
    if low_structural_ids:
        _add_patch(
            patches,
            quality_path,
            "/layout/mediaPadYPct",
            0.1,
            "P0 structural coverage low: enlarge media container in Y axis.",
        )
        _add_patch(
            patches,
            quality_path,
            "/layout/cardWidthPct",
            0.68,
            "P0 structural coverage low: enlarge card width in landscape.",
        )
        if beats:
            replace_map = {
                "pipeline_flow": "how_steps",
                "pipeline_3": "how_steps",
            }
            low_set = set(low_structural_ids)
            patched_beats: List[Dict[str, Any]] = []
            for beat in beats:
                beat_id = str(beat.get("id") or "")
                intent = str(beat.get("intent") or "")
                if beat_id in low_set and intent in replace_map:
                    patched_beats.append({**beat, "intent": replace_map[intent]})
                else:
                    patched_beats.append(beat)
            _add_patch(
                patches,
                spec_path,
                "/beats",
                patched_beats,
                "P0 structural coverage low beats: switch to denser scene templates.",
            )

    sparse_rate = _safe_float(layout_metric.get("sparse_beat_rate"), 1.0)
    max_sparse_gate = _safe_float(
        _deep_get(quality, "limits", "maxSparseBeatRateGate", default=0.35), 0.35
    )
    effective_cov_p25 = _safe_float(layout_metric.get("effective_coverage_p25"), 0.0)
    min_effective_cov_gate = _safe_float(
        _deep_get(quality, "limits", "minEffectiveCoverageP25Gate", default=0.2), 0.2
    )
    sparse_beat_ids = density_metric.get("sparse_beats", []) if isinstance(density_metric, dict) else []
    sparse_beat_ids = [str(bid) for bid in sparse_beat_ids if str(bid).strip()]

    if (sparse_rate > max_sparse_gate or effective_cov_p25 < min_effective_cov_gate) and beats:
        _add_patch(
            patches,
            quality_path,
            "/layout/mediaPadYPct",
            0.1,
            "P0 sparse layout detected: increase media vertical footprint.",
        )
        _add_patch(
            patches,
            quality_path,
            "/layout/cardHeightPct",
            0.5,
            "P0 sparse layout detected: increase card height.",
        )
        if sparse_beat_ids:
            replace_map = {
                "pipeline_flow": "how_steps",
                "pipeline_3": "how_steps",
                "definition_card": "analogy_scene",
            }
            sparse_id_set = set(sparse_beat_ids)
            patched_beats: List[Dict[str, Any]] = []
            for beat in beats:
                beat_id = str(beat.get("id") or "")
                intent = str(beat.get("intent") or "")
                if beat_id in sparse_id_set and intent in replace_map:
                    patched_beats.append({**beat, "intent": replace_map[intent]})
                else:
                    patched_beats.append(beat)
            _add_patch(
                patches,
                spec_path,
                "/beats",
                patched_beats,
                "P0 sparse beats detected: switch weak intents to denser scene templates.",
            )

    text_fill_p25 = _safe_float(layout_metric.get("text_fill_ratio_p25"), 0.0)
    min_text_fill_p25_gate = _safe_float(
        _deep_get(quality, "limits", "minTextFillRatioP25Gate", default=0.08), 0.08
    )
    low_text_fill_beat_rate = _safe_float(layout_metric.get("low_text_fill_beat_rate"), 1.0)
    max_low_text_fill_beat_rate_gate = _safe_float(
        _deep_get(quality, "limits", "maxLowTextFillBeatRateGate", default=0.35), 0.35
    )
    low_text_fill_block_rate = _safe_float(layout_metric.get("low_text_fill_block_rate"), 1.0)
    max_low_text_fill_block_rate_gate = _safe_float(
        _deep_get(quality, "limits", "maxLowTextFillBlockRateGate", default=0.28), 0.28
    )
    low_text_fill_ids = layout_metric.get("low_text_fill_beat_ids", [])
    low_text_fill_ids = [str(bid) for bid in (low_text_fill_ids or []) if str(bid).strip()]
    if (
        text_fill_p25 < min_text_fill_p25_gate
        or low_text_fill_beat_rate > max_low_text_fill_beat_rate_gate
        or low_text_fill_block_rate > max_low_text_fill_block_rate_gate
    ):
        _add_patch(
            patches,
            stylekit_path,
            "/typography/title",
            {"$scale": 1.02},
            "P0 small text ratio: increase title size to improve component readability.",
        )
        _add_patch(
            patches,
            stylekit_path,
            "/typography/body",
            {"$scale": 1.03},
            "P0 small text ratio: increase body size to improve text fill.",
        )
        _add_patch(
            patches,
            quality_path,
            "/layout/cardHeightPct",
            0.28,
            "P0 low text fill: reduce card height in 16:9 to avoid oversized empty blocks.",
        )
        if low_text_fill_ids and beats:
            replace_map = {
                "definition_card": "analogy_scene",
            }
            low_fill_set = set(low_text_fill_ids)
            patched_beats: List[Dict[str, Any]] = []
            for beat in beats:
                beat_id = str(beat.get("id") or "")
                intent = str(beat.get("intent") or "")
                if beat_id in low_fill_set and intent in replace_map:
                    patched_beats.append({**beat, "intent": replace_map[intent]})
                else:
                    patched_beats.append(beat)
            _add_patch(
                patches,
                spec_path,
                "/beats",
                patched_beats,
                "P0 low text-fill beats: switch to denser scene templates.",
            )

    highlight_metric = manifest.get("highlight", {}) if isinstance(manifest, dict) else {}
    bad_highlight_ids = highlight_metric.get("bad_highlight_beat_ids", [])
    bad_highlight_ids = [str(bid) for bid in (bad_highlight_ids or []) if str(bid).strip()]
    if bad_highlight_ids and beats:
        replace_map = {
            "definition_card": "analogy_scene",
            "hook_title": "hook_title",
            "recap_slogan": "recap_slogan",
        }
        low_set = set(bad_highlight_ids)
        patched_beats: List[Dict[str, Any]] = []
        for beat in beats:
            beat_id = str(beat.get("id") or "")
            intent = str(beat.get("intent") or "")
            if beat_id in low_set and intent in replace_map:
                patched_beats.append({**beat, "intent": replace_map[intent]})
            else:
                patched_beats.append(beat)
        _add_patch(
            patches,
            spec_path,
            "/beats",
            patched_beats,
            "P0 highlight quality bad: switch risky beats to non-stopword highlight templates.",
        )

    overlap_beat_rate = _safe_float(layout_metric.get("overlap_beat_rate"), 0.0)
    max_overlap_beat_rate_gate = _safe_float(
        _deep_get(quality, "limits", "maxOverlapBeatRateGate", default=0.08), 0.08
    )
    severe_overlap_beat_rate = _safe_float(layout_metric.get("severe_overlap_beat_rate"), 0.0)
    max_severe_overlap_beat_rate_gate = _safe_float(
        _deep_get(quality, "limits", "maxSevereOverlapBeatRateGate", default=0.0), 0.0
    )
    wrap_risk_beat_rate = _safe_float(layout_metric.get("wrap_risk_beat_rate"), 0.0)
    max_wrap_risk_beat_rate_gate = _safe_float(
        _deep_get(quality, "limits", "maxWrapRiskBeatRateGate", default=0.14), 0.14
    )
    if (
        overlap_beat_rate > max_overlap_beat_rate_gate
        or severe_overlap_beat_rate > max_severe_overlap_beat_rate_gate
    ):
        _add_patch(
            patches,
            quality_path,
            "/layout/lowerThirdYPct",
            0.76,
            "P0 overlap risk: move lower-third further down in 16:9.",
        )
        _add_patch(
            patches,
            quality_path,
            "/layout/lowerThirdMaxWidthPct",
            0.7,
            "P0 overlap risk: increase lower-third width to reduce vertical stacking.",
        )
        _add_patch(
            patches,
            quality_path,
            "/layout/cardHeightPct",
            0.28,
            "P0 overlap risk: reduce tall card height to clear lower-third area.",
        )
    if wrap_risk_beat_rate > max_wrap_risk_beat_rate_gate:
        _add_patch(
            patches,
            stylekit_path,
            "/typography/body",
            {"$scale": 0.96},
            "P0 wrap risk: slightly reduce body font size to avoid aggressive line breaks.",
        )
        _add_patch(
            patches,
            quality_path,
            "/layout/lowerThirdMaxWidthPct",
            0.72,
            "P0 wrap risk: widen lower-third text area.",
        )

    # P1: 叙事结构
    missing_sections = narrative_metric.get("missing_sections", []) if isinstance(narrative_metric, dict) else []
    missing_sections = [str(s) for s in missing_sections if str(s).strip()]
    if missing_sections and beats:
        updated_beats = _ensure_structure_sections(beats, missing_sections)
        _add_patch(
            patches,
            spec_path,
            "/beats",
            updated_beats,
            f"P1 narrative missing sections: insert {', '.join(missing_sections)} beats.",
        )

    # P2: 信息密度
    overflow_ids = density_metric.get("overflow_beats", []) if isinstance(density_metric, dict) else []
    overflow_ids = [str(bid) for bid in overflow_ids if str(bid).strip()]
    bad_line_break_ids = (
        density_metric.get("bad_line_break_beats", []) if isinstance(density_metric, dict) else []
    )
    bad_line_break_ids = [str(bid) for bid in bad_line_break_ids if str(bid).strip()]
    if bad_line_break_ids:
        overflow_ids = sorted(set(overflow_ids).union(set(bad_line_break_ids)))
    if overflow_ids and beats:
        max_words = int(_deep_get(quality, "limits", "maxWordsPerLine", default=7) or 7)
        max_lines = int(_deep_get(quality, "limits", "maxLines", default=2) or 2)
        strict_limit = max(4, max_words - 1) if bad_line_break_ids else max_words
        updated = _split_overflow_beats(
            beats,
            overflow_ids,
            max_words * max_lines,
            strict_line_break_ids=bad_line_break_ids,
            strict_max_words=strict_limit,
        )
        _add_patch(
            patches,
            spec_path,
            "/beats",
            updated,
            "P2 density overflow: split long beats or shorten lines by words.",
        )

    short_hold_beat_rate = _safe_float(
        density_metric.get("short_hold_beat_rate") if isinstance(density_metric, dict) else 0.0,
        0.0,
    )
    max_short_hold_beat_rate_gate = _safe_float(
        _deep_get(quality, "limits", "maxShortHoldBeatRateGate", default=0.12), 0.12
    )
    if short_hold_beat_rate > max_short_hold_beat_rate_gate:
        _add_patch(
            patches,
            spec_path,
            "/meta/hookEnabled",
            False,
            "P2 text hold too short: disable overlay hook so first beat remains readable.",
        )
        _add_patch(
            patches,
            spec_path,
            "/meta/hookDurationSec",
            2.0,
            "P2 text hold too short: cap hook overlay duration.",
        )

    # P3: 动效一致性
    transition_count = int(motion_metric.get("transition_count", 0) or 0)
    motion_count = int(motion_metric.get("motion_count", 0) or 0)
    flash_opacity = _safe_float(motion_metric.get("flash_opacity"), 0.08)

    if transition_count > 2:
        _add_patch(
            patches,
            motionkit_path,
            "/recipes/transition/types",
            ["fade", "slide"],
            "P3 motion consistency: keep only fade/slide transitions.",
        )
        if beats:
            compact = []
            for idx, beat in enumerate(beats):
                compact.append({**beat, "transitionType": "fade" if idx % 2 == 0 else "slide"})
            _add_patch(
                patches,
                spec_path,
                "/beats",
                compact,
                "P3 motion consistency: enforce fade/slide alternation in beats.",
            )

    if motion_count > 3 and beats:
        compact = []
        seq = ["entrance", "emphasis", "transition"]
        for idx, beat in enumerate(beats):
            compact.append({**beat, "motionRecipe": seq[idx % len(seq)]})
        _add_patch(
            patches,
            spec_path,
            "/beats",
            compact,
            "P3 motion consistency: enforce 3 canonical motion recipes.",
        )

    if flash_opacity > 0.1:
        _add_patch(
            patches,
            quality_path,
            "/beatCut/flashOpacity",
            0.08,
            "P3 motion consistency: reduce beatCut flash opacity.",
        )
    backdrop_preset_count = int(motion_metric.get("backdrop_preset_count", 0) or 0)
    backdrop_switch_rate = _safe_float(motion_metric.get("backdrop_switch_rate"), 0.0)
    backdrop_intensity_jump = _safe_float(motion_metric.get("backdrop_max_intensity_jump"), 0.0)
    max_backdrop_preset_count = int(
        _deep_get(quality, "limits", "maxBackdropPresetCountGate", default=1) or 1
    )
    max_backdrop_switch_rate = _safe_float(
        _deep_get(quality, "limits", "maxBackdropSwitchRateGate", default=0.2), 0.2
    )
    max_backdrop_jump = _safe_float(
        _deep_get(quality, "limits", "maxBackdropIntensityJumpGate", default=0.16), 0.16
    )
    if (
        backdrop_preset_count > max_backdrop_preset_count
        or backdrop_switch_rate > max_backdrop_switch_rate
        or backdrop_intensity_jump > max_backdrop_jump
    ) and beats:
        _add_patch(
            patches,
            spec_path,
            "/beats",
            _normalize_backdrops(beats),
            "P3 backdrop consistency: unify preset and smooth intensity jumps.",
        )

    # P4: 节奏
    pct_in_range = _safe_float(_deep_get(manifest, "beat", "pct_in_range", default=1.0), 1.0)
    if pct_in_range < 0.8:
        _add_patch(
            patches,
            spec_path,
            "/generation/beatTargetSec",
            3.0,
            "P4 rhythm low hit-rate: set beatTargetSec=3.0.",
        )
        _add_patch(
            patches,
            spec_path,
            "/generation/splitStrategy",
            "balanced",
            "P4 rhythm low hit-rate: use balanced split strategy.",
        )

    return _dedupe_patches(patches)


def _decode_json_pointer(path: str) -> List[str]:
    if not path or path == "/":
        return []
    if not path.startswith("/"):
        raise ValueError(f"Invalid JSON pointer: {path}")
    return [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]


def _set_value(doc: Any, pointer: str, value: Any) -> None:
    keys = _decode_json_pointer(pointer)
    if not keys:
        raise ValueError("Refusing to replace root document")

    cur: Any = doc
    for key in keys[:-1]:
        if isinstance(cur, list):
            idx = int(key)
            while idx >= len(cur):
                cur.append({})
            cur = cur[idx]
            continue

        if key not in cur or not isinstance(cur[key], (dict, list)):
            cur[key] = {}
        cur = cur[key]

    last = keys[-1]
    if isinstance(cur, list):
        idx = int(last)
        while idx >= len(cur):
            cur.append(None)
        cur[idx] = value
    else:
        if isinstance(value, dict) and "$scale" in value and isinstance(cur.get(last), (int, float)):
            scaled = float(cur[last]) * float(value["$scale"])
            # Keep typography updates bounded so optimize loop does not blow up font sizes.
            if len(keys) >= 2 and keys[-2] == "typography":
                lo_hi = {
                    "hero": (72.0, 96.0),
                    "title": (64.0, 86.0),
                    "body": (42.0, 62.0),
                    "caption": (24.0, 40.0),
                }
                if last in lo_hi:
                    lo, hi = lo_hi[last]
                    scaled = max(lo, min(hi, scaled))
            cur[last] = scaled
        else:
            cur[last] = value


def apply_patches_to_document(doc: Dict[str, Any], patches: List[Patch]) -> Dict[str, Any]:
    patched = deepcopy(doc)
    for patch in patches:
        op = patch.get("op", "replace")
        if op not in {"replace", "add"}:
            continue
        _set_value(patched, patch["path"], patch.get("value"))
    return patched


def apply_patches_to_file(file_path: str, patches: List[Patch]) -> Tuple[bool, Dict[str, Any]]:
    if not patches:
        with open(file_path, "r", encoding="utf-8") as f:
            return False, json.load(f)

    with open(file_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    patched = apply_patches_to_document(doc, patches)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(patched, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True, patched


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and optionally apply QA patches")
    parser.add_argument("--report", required=True)
    parser.add_argument("--quality", default="src/config/quality.json")
    parser.add_argument("--spec", default="src/specs/skill.timeline.json")
    parser.add_argument("--out", default="out/patch_suggestions.json")
    parser.add_argument("--apply", action="store_true", help="Apply generated patches")
    args = parser.parse_args()

    with open(args.report, "r", encoding="utf-8") as f:
        report = json.load(f)
    with open(args.quality, "r", encoding="utf-8") as f:
        quality = json.load(f)
    with open(args.spec, "r", encoding="utf-8") as f:
        spec = json.load(f)

    patches = generate_patch_suggestions(report, quality, spec, args.quality, args.spec)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"patch_suggestions": patches}, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if args.apply and patches:
        by_file: Dict[str, List[Patch]] = {}
        for patch in patches:
            by_file.setdefault(patch["target_file"], []).append(patch)

        for target, target_patches in by_file.items():
            path_obj = Path(target)
            if not path_obj.exists():
                continue
            changed, _ = apply_patches_to_file(target, target_patches)
            print(f"Applied patches to {target}: {changed} ({len(target_patches)} ops)")

    print(f"Generated {len(patches)} patch suggestions")


if __name__ == "__main__":
    main()
