from __future__ import annotations

from typing import Any, Dict, List


def evaluate_motion_consistency(manifest: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
    limits = quality.get("limits", {}) if isinstance(quality, dict) else {}
    motion_summary = manifest.get("motionSummary", {}) if isinstance(manifest, dict) else {}
    effects_summary = manifest.get("effectsSummary", {}) if isinstance(manifest, dict) else {}
    beats = manifest.get("beats", []) if isinstance(manifest, dict) else []

    transition_types = motion_summary.get("transitionTypesUsed") or []
    motion_recipes = motion_summary.get("motionRecipesUsed") or []
    beatcut = motion_summary.get("beatCut") or {}
    component_counts = (
        effects_summary.get("componentTypeCounts")
        if isinstance(effects_summary.get("componentTypeCounts"), dict)
        else {}
    )

    transition_count = len([t for t in transition_types if str(t).strip()])
    motion_count = len([m for m in motion_recipes if str(m).strip()])
    component_type_count = len([k for k in component_counts.keys() if str(k).strip()])
    component_total = float(sum(int(v) for v in component_counts.values())) if component_counts else 0.0
    dominant_component_share = (
        float(max(component_counts.values()) / component_total)
        if component_counts and component_total > 0
        else 1.0
    )

    max_transition_types = int(limits.get("maxTransitionTypes", 2) or 2)
    max_motion_recipes = int(limits.get("maxMotionRecipes", 3) or 3)
    max_flash_opacity = float(limits.get("maxBeatCutFlashOpacity", 0.1) or 0.1)
    min_component_types = int(limits.get("minComponentTypes", 4) or 4)
    max_dominant_component_share = float(limits.get("maxDominantComponentShare", 0.62) or 0.62)
    max_backdrop_preset_count = int(limits.get("maxBackdropPresetCount", 1) or 1)
    max_backdrop_switch_rate = float(limits.get("maxBackdropSwitchRate", 0.12) or 0.12)
    max_backdrop_intensity_jump = float(limits.get("maxBackdropIntensityJump", 0.12) or 0.12)
    flash_opacity = float(beatcut.get("flashOpacity", quality.get("beatCut", {}).get("flashOpacity", 0.08)) or 0.08)

    adjacent_repeat_rate = 0.0
    backdrop_switch_rate = 0.0
    backdrop_preset_count = 0
    backdrop_max_intensity_jump = 0.0
    backdrop_avg_intensity_jump = 0.0
    if isinstance(beats, list) and len(beats) > 1:
        sigs: List[str] = []
        backdrop_presets: List[str] = []
        backdrop_intensities: List[float] = []
        for beat in beats:
            layers = beat.get("layerTypes") if isinstance(beat, dict) else []
            react = beat.get("reactContents") if isinstance(beat, dict) else []
            layer_sig = "+".join([str(x).strip() for x in layers if str(x).strip()]) if isinstance(layers, list) else ""
            react_sig = "+".join([str(x).strip() for x in react if str(x).strip()]) if isinstance(react, list) else ""
            sigs.append(f"{layer_sig}::{react_sig}")
            preset = str(beat.get("backdropPreset") or "gemini").strip() or "gemini"
            backdrop_presets.append(preset)
            try:
                backdrop_intensities.append(float(beat.get("backdropIntensity", 0.8) or 0.8))
            except (TypeError, ValueError):
                backdrop_intensities.append(0.8)
        same = 0
        total_pairs = 0
        backdrop_switches = 0
        backdrop_jumps: List[float] = []
        for idx in range(1, len(sigs)):
            total_pairs += 1
            if sigs[idx] == sigs[idx - 1]:
                same += 1
            if backdrop_presets[idx] != backdrop_presets[idx - 1]:
                backdrop_switches += 1
            backdrop_jumps.append(abs(backdrop_intensities[idx] - backdrop_intensities[idx - 1]))
        adjacent_repeat_rate = float(same / total_pairs) if total_pairs > 0 else 0.0
        backdrop_switch_rate = float(backdrop_switches / total_pairs) if total_pairs > 0 else 0.0
        backdrop_preset_count = len({preset for preset in backdrop_presets if preset})
        backdrop_max_intensity_jump = max(backdrop_jumps) if backdrop_jumps else 0.0
        backdrop_avg_intensity_jump = (
            float(sum(backdrop_jumps) / len(backdrop_jumps)) if backdrop_jumps else 0.0
        )
    elif isinstance(beats, list) and len(beats) == 1:
        single_preset = str(beats[0].get("backdropPreset") or "gemini").strip() or "gemini"
        backdrop_preset_count = 1 if single_preset else 0

    max_adjacent_scene_repeat = float(limits.get("maxAdjacentSceneSignatureRepeatRate", 0.2) or 0.2)

    fail_reasons: List[str] = []
    if transition_count > max_transition_types:
        fail_reasons.append(f"transition types {transition_count}>{max_transition_types}")
    if motion_count > max_motion_recipes:
        fail_reasons.append(f"motion recipes {motion_count}>{max_motion_recipes}")
    if flash_opacity > max_flash_opacity:
        fail_reasons.append(f"beatcut flashOpacity {flash_opacity:.3f}>{max_flash_opacity:.3f}")
    if component_type_count < min_component_types:
        fail_reasons.append(f"component types {component_type_count}<{min_component_types}")
    if dominant_component_share > max_dominant_component_share:
        fail_reasons.append(
            f"dominant component share {dominant_component_share:.2f}>{max_dominant_component_share:.2f}"
        )
    if adjacent_repeat_rate > max_adjacent_scene_repeat:
        fail_reasons.append(
            f"adjacent scene repeat {adjacent_repeat_rate:.2f}>{max_adjacent_scene_repeat:.2f}"
        )
    if backdrop_preset_count > max_backdrop_preset_count:
        fail_reasons.append(
            f"backdrop preset count {backdrop_preset_count}>{max_backdrop_preset_count}"
        )
    if backdrop_switch_rate > max_backdrop_switch_rate:
        fail_reasons.append(
            f"backdrop switch rate {backdrop_switch_rate:.2f}>{max_backdrop_switch_rate:.2f}"
        )
    if backdrop_max_intensity_jump > max_backdrop_intensity_jump:
        fail_reasons.append(
            f"backdrop intensity jump {backdrop_max_intensity_jump:.2f}>{max_backdrop_intensity_jump:.2f}"
        )

    score = 100.0
    if transition_count > max_transition_types:
        score -= min(40.0, (transition_count - max_transition_types) * 20.0)
    if motion_count > max_motion_recipes:
        score -= min(35.0, (motion_count - max_motion_recipes) * 17.0)
    if flash_opacity > max_flash_opacity:
        score -= min(25.0, (flash_opacity - max_flash_opacity) * 240.0)
    if component_type_count < min_component_types:
        score -= min(20.0, (min_component_types - component_type_count) * 7.0)
    if dominant_component_share > max_dominant_component_share:
        score -= min(25.0, (dominant_component_share - max_dominant_component_share) * 120.0)
    if adjacent_repeat_rate > max_adjacent_scene_repeat:
        score -= min(20.0, (adjacent_repeat_rate - max_adjacent_scene_repeat) * 110.0)
    if backdrop_preset_count > max_backdrop_preset_count:
        score -= min(22.0, (backdrop_preset_count - max_backdrop_preset_count) * 18.0)
    if backdrop_switch_rate > max_backdrop_switch_rate:
        score -= min(18.0, (backdrop_switch_rate - max_backdrop_switch_rate) * 90.0)
    if backdrop_max_intensity_jump > max_backdrop_intensity_jump:
        score -= min(14.0, (backdrop_max_intensity_jump - max_backdrop_intensity_jump) * 85.0)

    score = max(0.0, min(100.0, score))

    return {
        "score": score,
        "transition_types": transition_types,
        "motion_recipes": motion_recipes,
        "transition_count": transition_count,
        "motion_count": motion_count,
        "flash_opacity": flash_opacity,
        "component_type_count": component_type_count,
        "dominant_component_share": dominant_component_share,
        "adjacent_scene_repeat_rate": adjacent_repeat_rate,
        "backdrop_preset_count": backdrop_preset_count,
        "backdrop_switch_rate": backdrop_switch_rate,
        "backdrop_max_intensity_jump": backdrop_max_intensity_jump,
        "backdrop_avg_intensity_jump": backdrop_avg_intensity_jump,
        "fail_reasons": fail_reasons,
    }
