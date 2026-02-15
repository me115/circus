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

    # 4) Motion diversity: keep recipes focused and consistent in spec.
    motion_count = int(_deep_get(manifest, "diversity", "motion_recipe_count", default=0) or 0)
    max_motion = int(_deep_get(quality, "limits", "maxMotionRecipes", default=3) or 3)
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
