from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


def _truncate_text(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text

    words = text.split()
    if not words:
        return text[:max_len].rstrip()

    acc: List[str] = []
    for word in words:
        tentative = " ".join([*acc, word]).strip()
        if len(tentative) > max_len:
            break
        acc.append(word)

    if not acc:
        return text[:max_len].rstrip()

    result = " ".join(acc).rstrip(".,;:!? ")
    if len(result) <= max_len:
        return result
    return result[:max_len].rstrip()


def _estimate_lines_count(text: str, max_chars_per_line: int) -> int:
    safe_max = max(1, int(max_chars_per_line))
    text_len = len((text or "").strip())
    if text_len <= 0:
        return 1
    return max(1, (text_len + safe_max - 1) // safe_max)


def _dedupe_patches(patches: List[Patch]) -> List[Patch]:
    seen = set()
    result: List[Patch] = []
    for patch in patches:
        key = (patch.get("target_file"), patch.get("path"), json.dumps(patch.get("value"), sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        result.append(patch)
    return result


def generate_patch_suggestions(
    report: Dict[str, Any],
    quality: Dict[str, Any],
    spec: Dict[str, Any],
    quality_path: str = "src/config/quality.json",
    spec_path: str = "src/specs/skill.timeline.json",
) -> List[Patch]:
    # Real-improvement mode: patch spec/layout/audio content only.
    patches: List[Patch] = []

    metrics = report.get("metrics", {})
    manifest = metrics.get("manifest", {})
    audio = metrics.get("audio", {})

    beats = list(spec.get("beats") or [])

    # 1) Safe area: move layout upward / inward (spec layout), never relax gate thresholds.
    safe_violations = int(_deep_get(manifest, "safe", "violations", default=0) or 0)
    frame_violations = int(_deep_get(manifest, "bounds", "violations", default=0) or 0)
    if safe_violations > 0:
        current_layout = spec.get("layout") or {}
        lower_y = _safe_float(current_layout.get("lowerThirdYPct"), 0.82)
        kinetic_y = _safe_float(current_layout.get("kineticYPct"), 0.76)
        card_y = _safe_float(current_layout.get("cardYPct"), 0.32)
        media_pad_y = _safe_float(current_layout.get("mediaPadYPct"), 0.13)

        target_lower = min(lower_y, 0.70)
        target_kinetic = min(kinetic_y, 0.64)
        target_card = min(card_y, 0.22)
        target_media_pad_y = max(media_pad_y, 0.16)

        if abs(target_lower - lower_y) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/lowerThirdYPct",
                round(target_lower, 4),
                "Safe-area gate failed: move lower-third upward in spec layout.",
            )

        if abs(target_kinetic - kinetic_y) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/kineticYPct",
                round(target_kinetic, 4),
                "Safe-area gate failed: move kinetic text band upward in spec layout.",
            )

        if abs(target_card - card_y) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/cardYPct",
                round(target_card, 4),
                "Safe-area gate failed: move prompt/answer card upward in spec layout.",
            )

        if abs(target_media_pad_y - media_pad_y) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/mediaPadYPct",
                round(target_media_pad_y, 4),
                "Safe-area gate failed: increase media vertical padding in spec layout.",
            )

    if frame_violations > 0:
        current_layout = spec.get("layout") or {}
        media_pad_x = _safe_float(current_layout.get("mediaPadXPct"), 0.085)
        media_pad_y = _safe_float(current_layout.get("mediaPadYPct"), 0.13)
        hero_w = _safe_float(current_layout.get("heroMaxWidthPct"), 0.78)
        card_w = _safe_float(current_layout.get("cardWidthPct"), 0.72)
        card_h = _safe_float(current_layout.get("cardHeightPct"), 0.44)

        _add_patch(
            patches,
            spec_path,
            "/layout/mediaPadXPct",
            round(min(0.14, media_pad_x + 0.02), 4),
            "Frame-bounds gate failed: increase horizontal padding to avoid overflow.",
        )
        _add_patch(
            patches,
            spec_path,
            "/layout/mediaPadYPct",
            round(min(0.18, media_pad_y + 0.02), 4),
            "Frame-bounds gate failed: increase vertical padding to avoid overflow.",
        )
        _add_patch(
            patches,
            spec_path,
            "/layout/heroMaxWidthPct",
            round(max(0.68, hero_w - 0.04), 4),
            "Frame-bounds gate failed: reduce hero width to keep components inside frame.",
        )
        _add_patch(
            patches,
            spec_path,
            "/layout/cardWidthPct",
            round(max(0.62, card_w - 0.04), 4),
            "Frame-bounds gate failed: reduce prompt card width to avoid clipping.",
        )
        _add_patch(
            patches,
            spec_path,
            "/layout/cardHeightPct",
            round(max(0.34, card_h - 0.03), 4),
            "Frame-bounds gate failed: reduce prompt card height to avoid clipping.",
        )

    no_element_gap = manifest.get("no_element_gap", {})
    no_element_violations = int(no_element_gap.get("violating_gap_count", 0) or 0)
    if no_element_violations > 0 and beats:
        default_layers = [
            {
                "type": "MediaFrame",
                "props": {
                    "kind": "react",
                    "reactContent": "SemanticOrbitBroll",
                    "fallbackReactContent": "PipelineBlocksBroll",
                },
            },
            {
                "type": "LowerThird",
                "props": {"title": "Visual beat", "source": "", "durationSec": 4, "align": "left"},
            },
        ]
        for idx, beat in enumerate(beats):
            scene = beat.get("scene") if isinstance(beat, dict) else {}
            scene = scene if isinstance(scene, dict) else {}
            layers = scene.get("layers")
            if isinstance(layers, list) and len(layers) > 0:
                continue
            _add_patch(
                patches,
                spec_path,
                f"/beats/{idx}/scene/layers",
                deepcopy(default_layers),
                "No-element gap gate failed: inject baseline visual layers to avoid blank timeline spans.",
                op="add",
            )

    # 2) Rhythm: adjust beat generation strategy in spec only.
    pct_in_range = _safe_float(_deep_get(manifest, "beat", "pct_in_range", default=1.0), 1.0)
    if pct_in_range < 0.8:
        _add_patch(
            patches,
            spec_path,
            "/generation/beatTargetSec",
            3.0,
            "Rhythm hit-rate is low: retarget beats around 3.0s in spec.",
        )
        _add_patch(
            patches,
            spec_path,
            "/generation/splitStrategy",
            "balanced",
            "Rhythm hit-rate is low: use balanced split strategy in spec.",
        )

    # 2.5) Composition balance/readability: adjust spec layout for better visual proportion.
    layout_metrics = manifest.get("layout", {})
    limits = quality.get("limits", {})
    coverage_ratio = _safe_float(layout_metrics.get("coverage_ratio"), 0.0)
    visual_center = _safe_float(layout_metrics.get("visual_center_y_pct"), 0.0)
    readable_font_rate = _safe_float(layout_metrics.get("readable_font_rate"), 1.0)
    lower_half_coverage = _safe_float(layout_metrics.get("lower_half_coverage_ratio"), 0.0)
    min_cov = _safe_float(limits.get("minContentCoverage"), 0.22)
    target_center = _safe_float(limits.get("targetVisualCenterYPct"), 0.52)
    max_center_dev = _safe_float(limits.get("maxVisualCenterDeviationPct"), 0.18)
    min_lower_half_coverage = max(
        _safe_float(limits.get("minLowerHalfCoverage"), 0.24),
        _safe_float(limits.get("minLowerHalfCoverageGate"), 0.24),
    )

    current_layout = spec.get("layout") or {}

    if coverage_ratio < min_cov:
        media_pad_x = _safe_float(current_layout.get("mediaPadXPct"), 0.085)
        media_pad_y = _safe_float(current_layout.get("mediaPadYPct"), 0.13)
        target_media_pad_x = max(0.05, media_pad_x - 0.015)
        target_media_pad_y = max(0.08, media_pad_y - 0.02)

        if abs(target_media_pad_x - media_pad_x) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/mediaPadXPct",
                round(target_media_pad_x, 4),
                "Content coverage is low: enlarge central content region horizontally.",
            )
        if abs(target_media_pad_y - media_pad_y) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/mediaPadYPct",
                round(target_media_pad_y, 4),
                "Content coverage is low: enlarge central content region vertically.",
            )

    if max_center_dev > 0:
        if visual_center < target_center - max_center_dev * 0.35:
            for key, base, upper in [
                ("heroYPct", 0.19, 0.3),
                ("cardYPct", 0.24, 0.34),
                ("kineticYPct", 0.66, 0.69),
                ("lowerThirdYPct", 0.71, 0.72),
            ]:
                cur = _safe_float(current_layout.get(key), base)
                nxt = min(upper, cur + 0.03)
                if abs(nxt - cur) > 1e-6:
                    _add_patch(
                        patches,
                        spec_path,
                        f"/layout/{key}",
                        round(nxt, 4),
                        "Visual center is too high: move foreground composition downward for balance.",
                    )
        elif visual_center > target_center + max_center_dev * 0.35:
            for key, base, lower in [
                ("heroYPct", 0.19, 0.1),
                ("cardYPct", 0.24, 0.14),
                ("kineticYPct", 0.66, 0.52),
                ("lowerThirdYPct", 0.71, 0.56),
            ]:
                cur = _safe_float(current_layout.get(key), base)
                nxt = max(lower, cur - 0.03)
                if abs(nxt - cur) > 1e-6:
                    _add_patch(
                        patches,
                        spec_path,
                        f"/layout/{key}",
                        round(nxt, 4),
                        "Visual center is too low: move foreground composition upward for balance.",
                    )

    if lower_half_coverage < min_lower_half_coverage and frame_violations == 0 and safe_violations == 0:
        for key, base, upper in [
            ("heroYPct", 0.19, 0.3),
            ("cardYPct", 0.24, 0.34),
            ("kineticYPct", 0.66, 0.69),
            ("lowerThirdYPct", 0.71, 0.72),
        ]:
            cur = _safe_float(current_layout.get(key), base)
            nxt = min(upper, cur + 0.035)
            if abs(nxt - cur) > 1e-6:
                _add_patch(
                    patches,
                    spec_path,
                    f"/layout/{key}",
                    round(nxt, 4),
                    "Lower-half content density is low: shift composition downward for better visual balance.",
                )

    if readable_font_rate < 0.85:
        hero_h = _safe_float(current_layout.get("heroHeightPct"), 0.36)
        card_h = _safe_float(current_layout.get("cardHeightPct"), 0.44)
        card_w = _safe_float(current_layout.get("cardWidthPct"), 0.72)
        target_hero_h = min(0.5, hero_h + 0.03)
        target_card_h = min(0.58, card_h + 0.04)
        target_card_w = min(0.84, card_w + 0.04)

        if abs(target_hero_h - hero_h) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/heroHeightPct",
                round(target_hero_h, 4),
                "Estimated text size is small: increase hero text area height.",
            )
        if abs(target_card_h - card_h) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/cardHeightPct",
                round(target_card_h, 4),
                "Estimated text size is small: increase prompt card height.",
            )
        if abs(target_card_w - card_w) > 1e-6:
            _add_patch(
                patches,
                spec_path,
                "/layout/cardWidthPct",
                round(target_card_w, 4),
                "Estimated text size is small: increase prompt card width.",
            )

    sparse_beat_rate = _safe_float(layout_metrics.get("sparse_beat_rate"), 0.0)
    max_sparse_beat_rate = _safe_float(limits.get("maxSparseBeatRate"), 0.18)
    if beats and sparse_beat_rate > max_sparse_beat_rate:
        injected = 0
        sparse_fill_variants = [
            "VectorMapBroll",
            "SearchIconBroll",
            "UseCasesIconsBroll",
            "SemanticOrbitBroll",
        ]
        for idx, beat in enumerate(beats):
            scene = beat.get("scene") if isinstance(beat, dict) else {}
            scene = scene if isinstance(scene, dict) else {}
            layers = scene.get("layers")
            if not isinstance(layers, list) or len(layers) != 1:
                continue
            only = layers[0] if isinstance(layers[0], dict) else {}
            layer_type = str(only.get("type") or "")
            if layer_type not in {"HeroTitle", "KineticWords", "PromptAnswerCard"}:
                continue
            _add_patch(
                patches,
                spec_path,
                f"/beats/{idx}/scene/layers/0",
                {
                    "type": "MediaFrame",
                    "props": {
                        "kind": "react",
                        "reactContent": sparse_fill_variants[injected % len(sparse_fill_variants)],
                        "fallbackReactContent": "PipelineBlocksBroll",
                    },
                },
                "Sparse beats are too many: inject a background visual layer behind text-only scenes.",
                op="add",
            )
            injected += 1
            if injected >= 3:
                break

    # 3) Middle-stage blankness: replace low-energy middle beats with richer modes.
    mid_low_energy_rate = _safe_float(
        _deep_get(manifest, "storyboard", "middle_low_energy_rate", default=0.0), 0.0
    )
    duration_sec = _safe_float(_deep_get(spec, "meta", "durationSec", default=60.0), 60.0)
    mid_start = duration_sec * 0.35
    mid_end = duration_sec * 0.75

    if beats and mid_low_energy_rate > 0.35:
        replacement_modes = ["media", "kinetic", "promptCard"]
        r_idx = 0
        for idx, beat in enumerate(beats):
            t0 = _safe_float(beat.get("t0"), 0.0)
            t1 = _safe_float(beat.get("t1"), 0.0)
            mode = str(beat.get("renderMode") or "")
            if t0 >= mid_start and t1 <= mid_end and mode in {"lowerThird", "outro"}:
                new_mode = replacement_modes[r_idx % len(replacement_modes)]
                new_transition = "slide" if r_idx % 2 == 0 else "fade"
                _add_patch(
                    patches,
                    spec_path,
                    f"/beats/{idx}/renderMode",
                    new_mode,
                    "Middle section looks low-energy: replace beat render mode with richer storyboard mode.",
                )
                _add_patch(
                    patches,
                    spec_path,
                    f"/beats/{idx}/transitionType",
                    new_transition,
                    "Middle section looks low-energy: alternate transitions for visual continuity.",
                )
                r_idx += 1

    # 4) Motion diversity: avoid both over-fragmentation and monotony.
    transition_count = int(_deep_get(manifest, "diversity", "transition_type_count", default=0) or 0)
    dominant_transition_share = _safe_float(
        _deep_get(manifest, "diversity", "dominant_transition_share", default=1.0), 1.0
    )
    min_transition = int(_deep_get(quality, "limits", "minTransitionTypes", default=1) or 1)
    max_dominant_transition = _safe_float(
        _deep_get(quality, "limits", "maxDominantTransitionShare", default=0.78), 0.78
    )
    if beats and (transition_count < min_transition or dominant_transition_share > max_dominant_transition):
        for idx, beat in enumerate(beats):
            target_transition = "slide" if idx % 2 == 0 else "fade"
            if str(beat.get("transitionType") or "fade") == target_transition:
                continue
            _add_patch(
                patches,
                spec_path,
                f"/beats/{idx}/transitionType",
                target_transition,
                "Transition variety is too low: alternate transitions to reduce visual monotony.",
            )

    motion_count = int(_deep_get(manifest, "diversity", "motion_recipe_count", default=0) or 0)
    dominant_motion_share = _safe_float(
        _deep_get(manifest, "diversity", "dominant_motion_share", default=1.0), 1.0
    )
    min_motion = int(_deep_get(quality, "limits", "minMotionRecipes", default=1) or 1)
    max_dominant_motion = _safe_float(
        _deep_get(quality, "limits", "maxDominantMotionShare", default=0.76), 0.76
    )
    max_motion = int(_deep_get(quality, "limits", "maxMotionRecipes", default=3) or 3)

    if beats and (motion_count < min_motion or dominant_motion_share > max_dominant_motion):
        for idx, beat in enumerate(beats):
            render_mode = str(beat.get("renderMode") or "").strip()
            target_motion = "kenburns" if render_mode == "media" and idx % 2 == 0 else "spring"
            if idx % 3 == 1:
                target_motion = "slide"
            if str(beat.get("motionRecipe") or "spring") == target_motion:
                continue
            _add_patch(
                patches,
                spec_path,
                f"/beats/{idx}/motionRecipe",
                target_motion,
                "Motion recipe variety is too low: diversify motion patterns across beats.",
            )

    if beats and motion_count > max_motion:
        keep_priority = {"slide": 1000, "kenburns": 900, "spring": 800, "pop": 700, "type": 600}
        freq: Dict[str, int] = {}
        for beat in beats:
            recipe = str(beat.get("motionRecipe") or "slide").strip() or "slide"
            freq[recipe] = freq.get(recipe, 0) + 1

        ranked = sorted(
            freq.keys(),
            key=lambda key: (freq.get(key, 0), keep_priority.get(key, 0)),
            reverse=True,
        )
        keep_set = set(ranked[:max_motion])

        for idx, beat in enumerate(beats):
            recipe = str(beat.get("motionRecipe") or "slide").strip() or "slide"
            if recipe in keep_set:
                continue

            render_mode = str(beat.get("renderMode") or "").strip()
            fallback = "kenburns" if render_mode == "media" and "kenburns" in keep_set else "slide"
            if fallback == recipe:
                continue

            _add_patch(
                patches,
                spec_path,
                f"/beats/{idx}/motionRecipe",
                fallback,
                "Motion recipe diversity is too high: converge on a smaller recipe set for consistency.",
            )

    component_type_count = int(_deep_get(manifest, "diversity", "component_type_count", default=0) or 0)
    dominant_component_share = _safe_float(
        _deep_get(manifest, "diversity", "dominant_component_share", default=1.0), 1.0
    )
    react_variant_count = int(_deep_get(manifest, "diversity", "react_variant_count", default=0) or 0)
    dominant_react_variant_share = _safe_float(
        _deep_get(manifest, "diversity", "dominant_react_variant_share", default=1.0), 1.0
    )
    max_consecutive_react_variant_run = int(
        _deep_get(manifest, "diversity", "max_consecutive_react_variant_run", default=0) or 0
    )
    adjacent_react_variant_repeat_rate = _safe_float(
        _deep_get(manifest, "diversity", "adjacent_react_variant_repeat_rate", default=0.0), 0.0
    )
    scene_signature_count = int(_deep_get(manifest, "diversity", "scene_signature_count", default=0) or 0)
    dominant_scene_signature_share = _safe_float(
        _deep_get(manifest, "diversity", "dominant_scene_signature_share", default=1.0), 1.0
    )
    min_component_types = int(_deep_get(quality, "limits", "minComponentTypes", default=4) or 4)
    min_react_variants = int(_deep_get(quality, "limits", "minReactVariants", default=6) or 6)
    min_scene_signatures = int(_deep_get(quality, "limits", "minSceneSignatures", default=8) or 8)
    max_dominant_share = _safe_float(
        _deep_get(quality, "limits", "maxDominantComponentShare", default=0.62), 0.62
    )
    max_dominant_react_share = _safe_float(
        _deep_get(quality, "limits", "maxDominantReactVariantShare", default=0.28), 0.28
    )
    max_react_run = int(_deep_get(quality, "limits", "maxConsecutiveReactVariantRun", default=3) or 3)
    max_adjacent_react_repeat_rate = _safe_float(
        _deep_get(quality, "limits", "maxAdjacentReactRepeatRate", default=0.3), 0.3
    )
    max_dominant_scene_signature_share = _safe_float(
        _deep_get(quality, "limits", "maxDominantSceneSignatureShare", default=0.24), 0.24
    )
    diversity_needs_fix = any(
        [
            component_type_count < min_component_types,
            dominant_component_share > max_dominant_share,
            react_variant_count < min_react_variants,
            dominant_react_variant_share > max_dominant_react_share,
            max_consecutive_react_variant_run > max_react_run,
            adjacent_react_variant_repeat_rate > max_adjacent_react_repeat_rate,
            scene_signature_count < min_scene_signatures,
            dominant_scene_signature_share > max_dominant_scene_signature_share,
        ]
    )
    if beats and diversity_needs_fix:
        variant_pool = [
            "KeywordVsMeaningBroll",
            "VectorMapBroll",
            "ChunksBroll",
            "EmbeddingsBroll",
            "StoreAndLinkBroll",
            "NearestNeighborsBroll",
            "UseCasesIconsBroll",
            "RetrieveThenAnswerBroll",
            "CatalogCardsBroll",
            "SearchIconBroll",
            "DashboardIconsBroll",
            "SemanticOrbitBroll",
        ]
        by_intent = {
            "problem": "KeywordVsMeaningBroll",
            "analogy": "VectorMapBroll",
            "step1": "ChunksBroll",
            "step2": "EmbeddingsBroll",
            "step3": "StoreAndLinkBroll",
            "nearest": "NearestNeighborsBroll",
            "query": "SemanticOrbitBroll",
            "example": "SearchIconBroll",
            "use": "UseCasesIconsBroll",
            "rag": "RetrieveThenAnswerBroll",
            "catalog": "CatalogCardsBroll",
        }

        media_slots: List[Tuple[int, int, str]] = []
        variant_counts: Dict[str, int] = {}
        for idx, beat in enumerate(beats):
            scene = beat.get("scene") if isinstance(beat, dict) else {}
            scene = scene if isinstance(scene, dict) else {}
            layers = scene.get("layers")
            if not isinstance(layers, list):
                continue
            intent_key = str(beat.get("intent") or "").lower()
            for layer_idx, layer in enumerate(layers):
                if not isinstance(layer, dict) or str(layer.get("type")) != "MediaFrame":
                    continue
                props = layer.get("props")
                if not isinstance(props, dict) or str(props.get("kind", "react")) != "react":
                    continue
                current = str(props.get("reactContent") or "").strip() or "PipelineBlocksBroll"
                media_slots.append((idx, layer_idx, current))
                variant_counts[current] = variant_counts.get(current, 0) + 1
                if intent_key and intent_key in by_intent:
                    continue

        if media_slots:
            overused = sorted(
                variant_counts.keys(),
                key=lambda key: variant_counts.get(key, 0),
                reverse=True,
            )
            patch_count = 0
            changed_slots = set()

            for variant in overused:
                if patch_count >= 10:
                    break
                count = variant_counts.get(variant, 0)
                if count <= 1:
                    continue
                slots = [slot for slot in media_slots if slot[2] == variant]
                # Keep the first usage and diversify the rest.
                for slot_idx, (beat_idx, layer_idx, _) in enumerate(slots):
                    if slot_idx == 0 or patch_count >= 10:
                        continue
                    if (beat_idx, layer_idx) in changed_slots:
                        continue
                    beat = beats[beat_idx]
                    intent = str(beat.get("intent") or "").lower()
                    preferred = None
                    for key, candidate in by_intent.items():
                        if key in intent:
                            preferred = candidate
                            break
                    choices = [preferred] if preferred else []
                    choices += [name for name in variant_pool if name not in {variant, preferred}]
                    target = next((name for name in choices if name and name != variant), None)
                    if not target:
                        continue
                    _add_patch(
                        patches,
                        spec_path,
                        f"/beats/{beat_idx}/scene/layers/{layer_idx}/props/reactContent",
                        target,
                        "Repeated visual variant detected: swap to a different react component for scene variety.",
                    )
                    changed_slots.add((beat_idx, layer_idx))
                    patch_count += 1

    # 5) Text readability: shorten overlong beat copy in spec.
    max_chars = int(_deep_get(quality, "limits", "maxCharsPerLine", default=12))
    max_lines = int(_deep_get(quality, "limits", "maxLines", default=2))
    line_hit_rate = _safe_float(_deep_get(manifest, "text", "line_hit_rate", default=1.0), 1.0)
    hard_limit = max_chars * max_lines

    if line_hit_rate < 0.9 and beats:
        for idx, beat in enumerate(beats):
            text = str(beat.get("text") or "")
            lines_count = _estimate_lines_count(text, max_chars)
            if lines_count <= max_lines and len(text.strip()) <= hard_limit:
                continue
            shortened = _truncate_text(text, hard_limit)
            if _estimate_lines_count(shortened, max_chars) > max_lines:
                shortened = shortened[:hard_limit].rstrip()
            if shortened != text:
                _add_patch(
                    patches,
                    spec_path,
                    f"/beats/{idx}/text",
                    shortened,
                    "Text density is high: shorten beat copy to improve per-screen readability.",
                )

    # 6) Audio loudness: tune content-side audio bed level in spec.
    lufs = audio.get("input_i_lufs")
    min_lufs = _safe_float(_deep_get(quality, "audio", "minLUFS", default=-18.0), -18.0)
    max_lufs = _safe_float(_deep_get(quality, "audio", "maxLUFS", default=-14.0), -14.0)

    current_volume = _safe_float(_deep_get(spec, "meta", "audioBedVolume", default=0.08), 0.08)
    current_layers = int(_deep_get(spec, "meta", "audioLayerCount", default=1) or 1)

    if lufs is not None:
        lufs_val = _safe_float(lufs, -30.0)
        if lufs_val < min_lufs:
            gain_factor = 10 ** ((min_lufs - lufs_val) / 20.0)
            target_volume = min(0.9, max(current_volume + 0.03, current_volume * gain_factor * 0.85))
            if abs(target_volume - current_volume) > 1e-6:
                _add_patch(
                    patches,
                    spec_path,
                    "/meta/audioBedVolume",
                    round(target_volume, 3),
                    "Integrated LUFS is too low: increase timeline audio bed volume in spec.",
                )
            elif current_layers < 4:
                _add_patch(
                    patches,
                    spec_path,
                    "/meta/audioLayerCount",
                    current_layers + 1,
                    "Integrated LUFS is too low at max bed volume: add another audio bed layer in spec.",
                )

        elif lufs_val > max_lufs:
            cut_factor = 10 ** ((lufs_val - max_lufs) / 20.0)
            target_volume = max(0.01, current_volume / max(cut_factor, 1.01) * 1.1)
            if abs(target_volume - current_volume) > 1e-6:
                _add_patch(
                    patches,
                    spec_path,
                    "/meta/audioBedVolume",
                    round(target_volume, 3),
                    "Integrated LUFS is too high: lower timeline audio bed volume in spec.",
                )
            elif current_layers > 1:
                _add_patch(
                    patches,
                    spec_path,
                    "/meta/audioLayerCount",
                    current_layers - 1,
                    "Integrated LUFS is too high at minimum volume delta: reduce audio bed layer count in spec.",
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
