# QA Pipeline (Video Quality + Auto-Iteration)

## Prerequisites

1. Python 3.9+
2. `ffmpeg` and `ffprobe` in PATH
3. Node.js + npm

On macOS (Homebrew):

```bash
brew install ffmpeg
```

Create Python venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r qa/requirements.txt
```

## Commands

Render from timeline spec (also emits manifest first):

```bash
npm run render:skill
```

Evaluate rendered output:

```bash
npm run qa:eval
```

Run optimization loop (`render -> evaluate -> patch quality config -> rerender`):

```bash
npm run qa:loop
```

Current loop policy:

- Gate thresholds in `src/config/quality.json` are treated as locked.
- Auto-patches target `src/specs/skill.timeline.json` only (rhythm/storyboard/layout/audio-bed volume).
- Scoring is now design-heavy: composition + motion consistency carry most weight.

## Files

- `scripts/emit_manifest.ts`: spec + quality -> `out/manifest.json`
- `scripts/render_from_spec.ts`: SSR render to `out/video.mp4`
- `qa/evaluate_video.py`: produce `out/report.json`
- `qa/patcher.py`: generate/apply JSON patch suggestions
- `qa/optimize_loop.py`: iterative optimization loop

## report.json structure

- `gate`: hard checks and pass/fail
- `score`: total(0-100) and weighted breakdown
- `metrics.video`: fps/duration/black frame ratio/flicker proxy
- `metrics.audio`: LUFS/True Peak/LRA
- `metrics.manifest`: rhythm/text/safe-area/frame-bounds/diversity stats
- `metrics.manifest.layout`: composition coverage, visual center balance, estimated font readability, lower-half usage
- `metrics.manifest.no_element_gap`: max no-element gap from timeline metadata
- `metrics.video.maxNoElementGapSecVideo`: max no-element gap from sampled frame activity (hard gate with manifest gap)
- `metrics.manifest.diversity`: transition/motion/component-type diversity and repetition ratio
- `metrics.video.foregroundCoverage*`: sampled foreground occupancy (for "too empty" detection)
- `metrics.video.foregroundCenterXPctMean`: left/right visual center bias (for horizontal balance)
- `metrics.manifest.layout.alignment_score`: bbox alignment quality (for PPT-like neatness)
- `metrics.manifest.layout.sparse_beat_rate`: low-occupancy beat ratio (for anti-sparse pacing)

## Design Intent

- `60` should mean "usable with minor/no edits", not just technically valid render.
- High scores now require:
  - sufficient foreground occupancy (avoid huge empty canvas)
  - balanced left/right visual center
  - lower sparse-beat ratio
  - non-monotone transition/motion usage
- `metrics.asr`: optional whisper CER (`skipped=true` when whisper missing)
- `suggestions.patch_suggestions`: machine-readable patches
- `exit_code`:
  - `0`: gate passed and score >= target
  - `2`: gate passed but score below target
  - `3`: gate failed

## ffmpeg detection behavior

`qa/evaluate_video.py` validates `ffmpeg` + `ffprobe` before running. If missing,
it writes a report with `exit_code=3` and a clear error message.
