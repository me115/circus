from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from patcher import apply_patches_to_file, generate_patch_suggestions


def run_cmd(cmd: List[str], cwd: str) -> int:
    proc = subprocess.run(cmd, cwd=cwd)
    return proc.returncode


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render -> evaluate -> patch loop")
    parser.add_argument("--spec", default="src/specs/skill.timeline.json")
    parser.add_argument("--target", type=float, default=60.0)
    parser.add_argument("--max_iter", type=int, default=10)
    parser.add_argument("--quality", default="src/config/quality.json")
    parser.add_argument("--video", default="out/video.mp4")
    parser.add_argument("--manifest", default="out/manifest.json")
    parser.add_argument("--report", default="out/report.json")
    parser.add_argument("--expected_text", default="qa/expected_script.txt")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    quality_path = repo_root / args.quality
    spec_path = repo_root / args.spec
    report_path = repo_root / args.report
    history_dir = repo_root / "out" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    if not quality_path.exists():
        print(f"Missing quality config: {quality_path}")
        return 1

    if not spec_path.exists():
        print(f"Missing spec file: {spec_path}")
        return 1

    for iter_idx in range(1, args.max_iter + 1):
        print(f"\n=== Iteration {iter_idx}/{args.max_iter} ===")

        render_cmd = [
            "node",
            "scripts/render_from_spec.ts",
            "--spec",
            args.spec,
            "--out",
            args.video,
        ]
        render_code = run_cmd(render_cmd, cwd=str(repo_root))
        if render_code != 0:
            print(f"Render failed in iteration {iter_idx}")
            return render_code

        eval_cmd = [
            "python3",
            "qa/evaluate_video.py",
            "--video",
            args.video,
            "--manifest",
            args.manifest,
            "--out",
            args.report,
            "--quality",
            args.quality,
            "--target",
            str(args.target),
        ]
        if (repo_root / args.expected_text).exists():
            eval_cmd.extend(["--expected_text", args.expected_text])

        eval_code = run_cmd(eval_cmd, cwd=str(repo_root))
        if not report_path.exists():
            print("Evaluation did not produce report.json")
            return max(1, eval_code)

        report = _load_json(report_path)

        hist_report = history_dir / f"report_iter_{iter_idx}.json"
        _save_json(hist_report, report)

        score = float(report.get("score", {}).get("total", 0.0))
        gate_pass = bool(report.get("gate", {}).get("pass", False))
        exit_code = int(report.get("exit_code", eval_code if eval_code else 2))
        print(f"Iteration {iter_idx}: gate_pass={gate_pass}, score={score:.2f}")

        if gate_pass and score >= args.target:
            print("Target achieved. Stop loop.")
            return 0

        if exit_code == 3 and not gate_pass:
            checks = report.get("gate", {}).get("checks", {})
            if checks.get("ffmpeg_tools") is False:
                print("Gate failed due to missing ffmpeg/ffprobe. Install dependencies and rerun.")
                return 3

        quality = _load_json(quality_path)
        spec = _load_json(spec_path)
        patches = generate_patch_suggestions(
            report,
            quality,
            spec,
            quality_path=str(args.quality),
            spec_path=str(args.spec),
        )

        patch_archive = history_dir / f"patch_iter_{iter_idx}.json"
        _save_json(patch_archive, {"patch_suggestions": patches})

        spec_patches = [p for p in patches if p.get("target_file") == str(args.spec)]

        if not spec_patches:
            print("No applicable spec patches; stop loop.")
            return report.get("exit_code", 2)

        changed, _ = apply_patches_to_file(str(spec_path), spec_patches)
        print(f"Applied {len(spec_patches)} spec patches (changed={changed}).")

    print("Max iterations reached without meeting target.")
    final_report = _load_json(report_path) if report_path.exists() else {}
    return int(final_report.get("exit_code", 2) or 2)


if __name__ == "__main__":
    sys.exit(main())
