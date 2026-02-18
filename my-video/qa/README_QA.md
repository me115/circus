# QA Pipeline (Render + Evaluate + Optimize)

## Prerequisites

1. Node.js + npm
2. Python 3.9+
3. `ffmpeg` / `ffprobe` in PATH

Install Python deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r qa/requirements.txt
```

## One-shot Commands

Render from spec:

```bash
npm run render:skill -- --spec src/specs/vector_db.timeline.json --out out/video.mp4 --manifest out/manifest.json
```

Evaluate:

```bash
python3 qa/evaluate_video.py \
  --video out/video.mp4 \
  --manifest out/manifest.json \
  --quality src/config/quality.json \
  --expected_text qa/expected_script.txt \
  --out out/report.json
```

Run optimize loop:

```bash
python3 qa/optimize_loop.py \
  --spec src/specs/vector_db.timeline.json \
  --target 70 \
  --max_iter 10 \
  --quality src/config/quality.json
```

## Presets

Stricter 16:9 line-break quality is now built into `src/config/quality.json`.

Apple keynote style preset files:

- `src/style/presets/apple_keynote_169.stylekit.json`
- `src/style/presets/apple_keynote_169.motionkit.json`
- `src/config/quality_presets/apple_keynote_169.json`

To apply them as current defaults:

```bash
cp src/style/presets/apple_keynote_169.stylekit.json src/style/stylekit.json
cp src/style/presets/apple_keynote_169.motionkit.json src/style/motionkit.json
cp src/config/quality_presets/apple_keynote_169.json src/config/quality.json
```

## Iteration Order

`optimize_loop.py` runs this sequence per iteration:

1. `scripts/normalize_storyboard.ts` -> `out/spec_iter_k.json`
2. `scripts/render_from_spec.ts` -> `out/video_iter_k.mp4` + `out/manifest_iter_k.json`
3. `qa/evaluate_video.py` -> `out/report_iter_k.json`
4. `qa/patcher.py` logic:
   - P0: config/style safety fixes
   - P1: narrative section补齐
   - P2: density overflow拆分/缩句
   - P3: motion consistency收敛
   - P4: rhythm hints

Per-iteration visual diagnostics (new):

- keyframe export: `out/history/iter_XX/keyframes/*.jpg`
- keyframe regression: `out/history/iter_XX/visual_regression.json` (vs previous iteration)
- failure atlas: `out/history/iter_XX/failure_atlas.jpg` + `failure_atlas.json`

Each round is archived to `out/history/iter_XX/`:

- `spec.json`
- `manifest.json`
- `report.json`
- `video.mp4`
- `patch_suggestions.json`

## Metrics and Score

Hard gate (must pass):

- resolution / fps / duration
- black frame ratio
- audio true peak + LUFS
- layout bounds + safe area (0 violation)
- max no-element gap (`<= 3s`)
- low-info run / foreground occupancy / alignment checks
- effective coverage p25 / sparse beat rate (防止“组件过小+大面积留白”)
- line-break quality (widow/orphan/imbalance)
- hook line-break hard check (hook段出现单词独占行直接不通过)
- text hold duration (信息句停留过短会直接失败)
- fragment line quality (字幕残句，如以 by/the/to 结尾，直接扣分/可gate)
- text-fill ratio (防止“大卡片+小字体”)
- low text-fill block rate (防止“卡片很大但字很少”)
- overlap gates (组件/文字重叠直接拦截)
- wrap-risk gate (字体过大或文本容器过窄导致异常断行)
- highlight quality (高亮停用词如 the/and/to 会判为bad highlight)
- structural beat coverage (流程类组件过小+大片留白会触发失败)
- backdrop consistency (preset切换频率与强度跳变)

Weighted score (0-100):

- `narrative` (20)
- `density` (20)
- `motion_consistency` (20)
- `rhythm` (20)
- `audio` (10)
- `visual_stability` (10)

`density` combines subtitle density + composition occupancy + line-break quality.
`motion_consistency` combines transition/motion rules + component diversity/repetition + backdrop consistency.

## Report Fields

Key report fields:

- `gate.pass`
- `gate.checks`
- `score.raw_total`
- `score.total` (gate fail -> `0`)
- `metrics.manifest.narrative_metric`
- `metrics.manifest.density_metric`
- `metrics.manifest.motion_consistency_metric`
- `suggestions.patch_suggestions`

Exit codes:

- `0`: gate pass and score >= target
- `2`: gate pass but score below target
- `3`: gate fail
