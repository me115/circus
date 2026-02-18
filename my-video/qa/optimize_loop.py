from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from patcher import apply_patches_to_file, generate_patch_suggestions
from visual_feedback import compare_keyframes, create_failure_atlas, export_keyframes


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
    parser.add_argument("--target", type=float, default=70.0)
    parser.add_argument("--max_iter", type=int, default=10)
    parser.add_argument("--quality", default="src/config/quality.json")
    parser.add_argument("--stylekit", default="src/style/stylekit.json")
    parser.add_argument("--motionkit", default="src/style/motionkit.json")
    parser.add_argument("--video", default="out/video.mp4")
    parser.add_argument("--manifest", default="out/manifest.json")
    parser.add_argument("--report", default="out/report.json")
    parser.add_argument("--expected_text", default="qa/expected_script.txt")
    return parser.parse_args()


def _relative(path_obj: Path, root: Path) -> str:
    try:
        return str(path_obj.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path_obj)


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    quality_path = repo_root / args.quality
    stylekit_path = repo_root / args.stylekit
    motionkit_path = repo_root / args.motionkit
    spec_path = repo_root / args.spec

    if not quality_path.exists():
        print(f"Missing quality config: {quality_path}")
        return 1
    if not stylekit_path.exists():
        print(f"Missing stylekit config: {stylekit_path}")
        return 1
    if not motionkit_path.exists():
        print(f"Missing motionkit config: {motionkit_path}")
        return 1
    if not spec_path.exists():
        print(f"Missing spec file: {spec_path}")
        return 1

    out_dir = repo_root / "out"
    history_dir = out_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    working_spec = out_dir / "spec_working.json"
    shutil.copyfile(spec_path, working_spec)

    last_iter_video = None
    last_iter_manifest = None
    last_iter_report = None
    prev_keyframes: List[Dict[str, Any]] = []

    for iter_idx in range(1, args.max_iter + 1):
        print(f"\n=== Iteration {iter_idx}/{args.max_iter} ===")

        iter_spec = out_dir / f"spec_iter_{iter_idx}.json"
        iter_video = out_dir / f"video_iter_{iter_idx}.mp4"
        iter_manifest = out_dir / f"manifest_iter_{iter_idx}.json"
        iter_report = out_dir / f"report_iter_{iter_idx}.json"
        iter_history_dir = history_dir / f"iter_{iter_idx:02d}"
        if iter_history_dir.exists():
            shutil.rmtree(iter_history_dir, ignore_errors=True)
        iter_history_dir.mkdir(parents=True, exist_ok=True)

        # 1) storyboard normalizer
        normalize_cmd = [
            "node",
            "scripts/normalize_storyboard.ts",
            "--spec",
            _relative(working_spec, repo_root),
            "--quality",
            args.quality,
            "--out",
            _relative(iter_spec, repo_root),
        ]
        normalize_code = run_cmd(normalize_cmd, cwd=str(repo_root))
        if normalize_code != 0:
            print(f"Normalize failed in iteration {iter_idx}")
            return normalize_code

        # 2) render normalized spec
        render_cmd = [
            "node",
            "scripts/render_from_spec.ts",
            "--spec",
            _relative(iter_spec, repo_root),
            "--out",
            _relative(iter_video, repo_root),
            "--manifest",
            _relative(iter_manifest, repo_root),
            "--quality",
            args.quality,
        ]
        render_code = run_cmd(render_cmd, cwd=str(repo_root))
        if render_code != 0:
            print(f"Render failed in iteration {iter_idx}")
            return render_code

        # 3) evaluate
        eval_cmd = [
            "python3",
            "qa/evaluate_video.py",
            "--video",
            _relative(iter_video, repo_root),
            "--manifest",
            _relative(iter_manifest, repo_root),
            "--out",
            _relative(iter_report, repo_root),
            "--quality",
            args.quality,
            "--target",
            str(args.target),
        ]
        expected_text_path = repo_root / args.expected_text
        if expected_text_path.exists():
            eval_cmd.extend(["--expected_text", args.expected_text])

        eval_code = run_cmd(eval_cmd, cwd=str(repo_root))
        if not iter_report.exists():
            print("Evaluation did not produce report file")
            return max(1, eval_code)

        report = _load_json(iter_report)
        score = float(report.get("score", {}).get("total", 0.0))
        gate_pass = bool(report.get("gate", {}).get("pass", False))
        print(f"Iteration {iter_idx}: gate_pass={gate_pass}, score={score:.2f}")

        manifest_doc = _load_json(iter_manifest)
        keyframe_dir = iter_history_dir / "keyframes"
        keyframes = export_keyframes(str(iter_video), manifest_doc, str(keyframe_dir), max_frames=12)
        visual_regression = compare_keyframes(prev_keyframes, keyframes, ssim_fail_threshold=0.7)
        _save_json(iter_history_dir / "visual_regression.json", visual_regression)
        failure_atlas = create_failure_atlas(
            str(iter_video),
            manifest_doc,
            report,
            str(iter_history_dir / "failure_atlas.jpg"),
            max_tiles=12,
        )
        _save_json(iter_history_dir / "failure_atlas.json", failure_atlas)
        report["visual_feedback"] = {
            "keyframes": keyframes,
            "visual_regression": visual_regression,
            "failure_atlas": failure_atlas,
        }
        _save_json(iter_report, report)
        prev_keyframes = keyframes

        last_iter_video = iter_video
        last_iter_manifest = iter_manifest
        last_iter_report = iter_report

        # archive snapshot
        shutil.copyfile(iter_spec, iter_history_dir / "spec.json")
        shutil.copyfile(iter_manifest, iter_history_dir / "manifest.json")
        shutil.copyfile(iter_report, iter_history_dir / "report.json")
        shutil.copyfile(iter_video, iter_history_dir / "video.mp4")

        if gate_pass and score >= args.target:
            print("Target achieved. Stop loop.")
            break

        # 4) patch config/spec
        quality = _load_json(quality_path)
        normalized_spec = _load_json(iter_spec)
        patch_spec_path = _relative(working_spec, repo_root)
        patches = generate_patch_suggestions(
            report,
            quality,
            normalized_spec,
            quality_path=args.quality,
            spec_path=patch_spec_path,
        )
        _save_json(iter_history_dir / "patch_suggestions.json", {"patch_suggestions": patches})

        if not patches:
            print("No patches generated; stop loop.")
            break

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for patch in patches:
            grouped.setdefault(str(patch.get("target_file")), []).append(patch)

        apply_order = [
            args.quality,
            args.stylekit,
            args.motionkit,
        ]

        for target in apply_order:
            target_patches = grouped.get(target, [])
            if not target_patches:
                continue
            changed, _ = apply_patches_to_file(str(repo_root / target), target_patches)
            print(f"Applied {len(target_patches)} patches to {target} (changed={changed})")

        # sync normalized spec back into working spec as next iteration input
        shutil.copyfile(iter_spec, working_spec)
        # apply working-spec patches after config patches so next round uses latest config+spec
        extra_spec_patches = grouped.get(patch_spec_path, [])
        if extra_spec_patches:
            changed, _ = apply_patches_to_file(str(working_spec), extra_spec_patches)
            print(f"Applied {len(extra_spec_patches)} patches to {patch_spec_path} (changed={changed})")

    # materialize final outputs
    if last_iter_video and last_iter_video.exists():
        shutil.copyfile(last_iter_video, repo_root / args.video)
    if last_iter_manifest and last_iter_manifest.exists():
        shutil.copyfile(last_iter_manifest, repo_root / args.manifest)
    if last_iter_report and last_iter_report.exists():
        shutil.copyfile(last_iter_report, repo_root / args.report)

    if last_iter_report and last_iter_report.exists():
        final_report = _load_json(last_iter_report)
        final_gate = bool(final_report.get("gate", {}).get("pass", False))
        final_score = float(final_report.get("score", {}).get("total", 0.0))
        if final_gate and final_score >= args.target:
            return 0
        return int(final_report.get("exit_code", 2) or 2)

    return 2


if __name__ == "__main__":
    sys.exit(main())
