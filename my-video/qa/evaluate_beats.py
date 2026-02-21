from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _score_bool(ok: bool, weight: float) -> float:
    return weight if ok else 0.0


def evaluate(manifest: Dict[str, Any], video_path: Path, target: float) -> Dict[str, Any]:
    timeline = manifest.get("timeline", {}) if isinstance(manifest, dict) else {}
    scene_coverage = manifest.get("sceneCoverage", {}) if isinstance(manifest, dict) else {}
    motion = manifest.get("motion", {}) if isinstance(manifest, dict) else {}
    diagram = manifest.get("diagram", {}) if isinstance(manifest, dict) else {}
    readability = manifest.get("readability", {}) if isinstance(manifest, dict) else {}

    per_beat = readability.get("perBeat", []) if isinstance(readability, dict) else []
    per_beat = per_beat if isinstance(per_beat, list) else []

    checks = {
      "timeline_ordered": bool(timeline.get("ordered", False)),
      "timeline_no_overlap": bool(timeline.get("noOverlap", False)),
      "timeline_duration_match": bool(timeline.get("matchesTotalFrames", False)),
      "required_scenes_covered": len(scene_coverage.get("missingTypes", [])) == 0,
      "motion_unified": bool(motion.get("unified", False)),
      "diagram_steps_valid": len(diagram.get("issues", [])) == 0 and int(diagram.get("beatCount", 0)) > 0,
      "readability_overflow_zero": int(readability.get("overflowCount", 999)) == 0,
      "video_rendered": video_path.exists() and video_path.stat().st_size > 0,
    }

    hook_ok = any(
      str(item.get("type", "")) == "hook" and not bool(item.get("overflow", True))
      for item in per_beat
    )
    definition_ok = any(
      str(item.get("type", "")) == "definition" and not bool(item.get("overflow", True))
      for item in per_beat
    )
    recap_blocks = [
      int(item.get("textBlocks", 0))
      for item in per_beat
      if str(item.get("type", "")) == "recap"
    ]
    recap_ok = len(recap_blocks) > 0 and max(recap_blocks) >= 3

    checks["hook_readable"] = hook_ok
    checks["definition_readable"] = definition_ok
    checks["recap_three_bullets"] = recap_ok

    score = 0.0
    score += _score_bool(checks["timeline_ordered"], 12)
    score += _score_bool(checks["timeline_no_overlap"], 12)
    score += _score_bool(checks["timeline_duration_match"], 8)
    score += _score_bool(checks["required_scenes_covered"], 14)
    score += _score_bool(checks["motion_unified"], 8)
    score += _score_bool(checks["diagram_steps_valid"], 16)
    score += _score_bool(checks["readability_overflow_zero"], 12)
    score += _score_bool(checks["hook_readable"], 6)
    score += _score_bool(checks["definition_readable"], 6)
    score += _score_bool(checks["recap_three_bullets"], 4)
    score += _score_bool(checks["video_rendered"], 2)

    hard_gate_keys = [
      "timeline_ordered",
      "timeline_no_overlap",
      "timeline_duration_match",
      "required_scenes_covered",
      "motion_unified",
      "diagram_steps_valid",
      "readability_overflow_zero",
      "video_rendered",
    ]
    gate_pass = all(checks[key] for key in hard_gate_keys)
    pass_target = score >= target

    fail_reasons: List[str] = []
    for key, ok in checks.items():
      if not ok:
        fail_reasons.append(key)

    return {
      "gate": {
        "pass": gate_pass,
        "checks": checks,
      },
      "score": {
        "total": round(score, 2),
        "target": target,
      },
      "pass_target": pass_target,
      "exit_code": 0 if gate_pass and pass_target else 3,
      "fail_reasons": fail_reasons,
      "manifest_summary": {
        "timeline_items": len(timeline.get("items", [])) if isinstance(timeline.get("items"), list) else 0,
        "missing_scene_types": scene_coverage.get("missingTypes", []),
        "diagram_issues": diagram.get("issues", []),
        "readability_warnings": readability.get("warnings", []),
      },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate beat-driven concept video")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--target", type=float, default=80.0)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    video_path = Path(args.video).resolve()
    out_path = Path(args.out).resolve()

    manifest = _load_json(manifest_path)
    report = evaluate(manifest, video_path, args.target)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
      json.dump(report, f, ensure_ascii=False, indent=2)
      f.write("\n")

    print(f"gate.pass={report['gate']['pass']} score={report['score']['total']} target={args.target}")
    return int(report.get("exit_code", 3))


if __name__ == "__main__":
    raise SystemExit(main())
