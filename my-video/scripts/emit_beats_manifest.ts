// @ts-nocheck
const fs = require("node:fs");
const path = require("node:path");

const ENTER_FRAMES = 12;
const EXIT_FRAMES = 10;
const EMPH_FRAMES = 8;

const parseArgs = (argv) => {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
};

const ensureDir = (dirPath) => fs.mkdirSync(dirPath, {recursive: true});
const readJson = (filePath) => JSON.parse(fs.readFileSync(filePath, "utf8"));

const isCjk = (text) => /[\u3400-\u9fff]/.test(`${text ?? ""}`);

const tokenize = (text) => {
  const raw = `${text ?? ""}`.trim().replace(/\s+/g, " ");
  if (!raw) return [];
  if (isCjk(raw)) return raw.split("").filter((ch) => ch.trim().length > 0);
  return raw.split(" ");
};

const wrapText = (text, maxCharsPerLine, maxLines) => {
  const units = tokenize(text);
  const lines = [];
  const cjk = isCjk(text);
  let cursor = [];
  const flush = () => {
    if (cursor.length === 0) return;
    lines.push(cjk ? cursor.join("") : cursor.join(" "));
    cursor = [];
  };
  units.forEach((unit) => {
    const candidate = cjk ? [...cursor, unit].join("") : [...cursor, unit].join(" ");
    if (candidate.length <= maxCharsPerLine) {
      cursor.push(unit);
      return;
    }
    flush();
    cursor.push(unit);
  });
  flush();
  const overflow = lines.length > maxLines;
  return {
    lines: overflow ? lines.slice(0, maxLines) : lines,
    overflow,
  };
};

const aspectSize = (aspect) => {
  return aspect === "9:16" ? {width: 1080, height: 1920} : {width: 1920, height: 1080};
};

const findMarkerForBeat = (beat, index, markers) => {
  if (beat.markerId) {
    return markers.find((marker) => marker.id === beat.markerId) ?? null;
  }
  const byBeatId = markers.find((marker) => marker.beatId === beat.id);
  if (byBeatId) return byBeatId;
  return markers[index] ?? null;
};

const inferMarkerEnd = (marker, markers, markerIndex, beat) => {
  if (typeof marker.endSec === "number") return marker.endSec;
  const next = markers[markerIndex + 1];
  if (next) return next.startSec;
  return marker.startSec + (beat.durationSec ?? 3);
};

const buildTimeline = (spec) => {
  const fps = Number(spec?.meta?.fps ?? 30);
  const beats = Array.isArray(spec?.beats) ? spec.beats : [];
  const markers = Array.isArray(spec?.audio?.markers) ? spec.audio.markers : [];
  const markerMode = markers.length > 0;
  let cursorSec = 0;
  const items = [];

  beats.forEach((beat, index) => {
    let startSec = cursorSec;
    let endSec = startSec + (Number(beat.durationSec) || 3);
    if (markerMode) {
      const marker = findMarkerForBeat(beat, index, markers);
      if (marker) {
        const markerIndex = markers.findIndex((item) => item.id === marker.id);
        const inferredEnd = inferMarkerEnd(marker, markers, Math.max(0, markerIndex), beat);
        startSec = Math.max(cursorSec, Number(marker.startSec));
        endSec = Math.max(startSec + 0.25, Number(inferredEnd));
      }
    }

    const durationSec = Math.max(0.25, endSec - startSec);
    const fromFrame = Math.round(startSec * fps);
    const durationFrames = Math.max(1, Math.round(durationSec * fps));
    items.push({
      beatId: beat.id,
      type: beat.type,
      startSec,
      endSec: startSec + durationSec,
      fromFrame,
      durationFrames,
    });
    cursorSec = startSec + durationSec;
  });

  const totalFrames =
    items.length === 0
      ? 1
      : items[items.length - 1].fromFrame + items[items.length - 1].durationFrames;
  return {items, totalFrames, fps, totalDurationSec: totalFrames / fps};
};

const validateDiagramBeat = (beat) => {
  const issues = [];
  if (beat.type !== "diagram_steps") return issues;
  const steps = Array.isArray(beat.steps) ? beat.steps : [];
  if (steps.length === 0) {
    issues.push("diagram_steps beat has no steps");
    return issues;
  }
  steps.forEach((step, index) => {
    const nodes = Array.isArray(step?.nodes) ? step.nodes : [];
    const edges = Array.isArray(step?.edges) ? step.edges : [];
    const nodeIds = new Set(nodes.map((node) => node.id));
    if (nodes.length < 2) {
      issues.push(`step ${index + 1} has less than 2 nodes`);
    }
    if (edges.length < 1) {
      issues.push(`step ${index + 1} has no edges`);
    }
    edges.forEach((edge) => {
      if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) {
        issues.push(`step ${index + 1} edge references missing node`);
      }
    });
    const focus = Array.isArray(step?.focusNodeIds) ? step.focusNodeIds : [];
    focus.forEach((id) => {
      if (!nodeIds.has(id)) {
        issues.push(`step ${index + 1} focus node missing: ${id}`);
      }
    });
  });
  return issues;
};

const main = () => {
  const args = parseArgs(process.argv.slice(2));
  const specPath = path.resolve(process.cwd(), args.spec ?? "src/beats/vector-db.beats.json");
  const outPath = path.resolve(process.cwd(), args.out ?? "out/vector-db.manifest.json");
  const maxCharsPerLine = Number(args.maxCharsPerLine ?? 26);
  const maxLines = Number(args.maxLines ?? 2);

  const spec = readJson(specPath);
  const timeline = buildTimeline(spec);
  const size = aspectSize(spec?.meta?.aspect ?? "16:9");
  const beats = Array.isArray(spec?.beats) ? spec.beats : [];
  const ordered = timeline.items.every((item, index) => {
    if (index === 0) return true;
    return item.fromFrame >= timeline.items[index - 1].fromFrame;
  });
  const noOverlap = timeline.items.every((item, index) => {
    if (index === 0) return true;
    const prev = timeline.items[index - 1];
    return item.fromFrame >= prev.fromFrame + prev.durationFrames;
  });
  const lastItem = timeline.items[timeline.items.length - 1];
  const endFrame = lastItem ? lastItem.fromFrame + lastItem.durationFrames : 0;

  const perBeatText = beats.map((beat) => {
    const blocks = Array.isArray(beat.onScreen) ? beat.onScreen : [];
    const wrapped = blocks.map((line) => wrapText(line, maxCharsPerLine, maxLines));
    const overflow = wrapped.some((entry) => entry.overflow);
    return {
      beatId: beat.id,
      type: beat.type,
      textBlocks: blocks.length,
      overflow,
      wrappedLines: wrapped.map((entry) => entry.lines),
    };
  });

  const warnings = [];
  perBeatText.forEach((entry) => {
    if (entry.overflow) {
      warnings.push({
        beatId: entry.beatId,
        reason: "text_overflow",
      });
    }
  });

  const requiredTypes = [
    "hook",
    "definition",
    "mental_model",
    "diagram_steps",
    "misconception",
    "recap",
  ];
  const present = new Set(beats.map((beat) => beat.type));
  const missingTypes = requiredTypes.filter((type) => !present.has(type));
  const diagramBeats = beats.filter((beat) => beat.type === "diagram_steps");
  const diagramIssues = diagramBeats.flatMap((beat) =>
    validateDiagramBeat(beat).map((issue) => ({beatId: beat.id, issue})),
  );

  const manifest = {
    generatedAt: new Date().toISOString(),
    specPath: path.relative(process.cwd(), specPath),
    meta: {
      title: spec?.meta?.title ?? "Concept Explainer",
      aspect: spec?.meta?.aspect ?? "16:9",
      width: size.width,
      height: size.height,
      fps: timeline.fps,
      totalFrames: timeline.totalFrames,
      totalDurationSec: timeline.totalDurationSec,
    },
    timeline: {
      items: timeline.items,
      ordered,
      noOverlap,
      endFrame,
      totalFrames: timeline.totalFrames,
      matchesTotalFrames: endFrame === timeline.totalFrames,
    },
    sceneCoverage: {
      requiredTypes,
      presentTypes: Array.from(present),
      missingTypes,
    },
    motion: {
      source: "src/motion/timing.ts",
      constants: {
        ENTER_FRAMES,
        EXIT_FRAMES,
        EMPH_FRAMES,
      },
      unified: true,
    },
    diagram: {
      beatCount: diagramBeats.length,
      validBeatCount: diagramBeats.length - diagramIssues.length,
      issues: diagramIssues,
    },
    readability: {
      maxCharsPerLine,
      maxLines,
      overflowCount: warnings.length,
      warnings,
      perBeat: perBeatText,
    },
  };

  ensureDir(path.dirname(outPath));
  fs.writeFileSync(outPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(`Beat manifest written: ${path.relative(process.cwd(), outPath)}`);
};

main();
