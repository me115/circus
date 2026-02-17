// @ts-nocheck
const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_SPEC = "src/specs/skill.timeline.json";
const DEFAULT_QUALITY = "src/config/quality.json";
const DEFAULT_OUT = "out/manifest.json";

const DEFAULT_LAYOUT = {
  safePadding: 72,
  mediaPadXPct: 0.085,
  mediaPadYPct: 0.13,
  kineticYPct: 0.66,
  lowerThirdYPct: 0.71,
  cardYPct: 0.24,
  cardWidthPct: 0.72,
  cardHeightPct: 0.44,
  heroMaxWidthPct: 0.78,
  heroYPct: 0.19,
  heroHeightPct: 0.36,
};

const SUPPORTED_LAYER_TYPES = new Set([
  "HeroTitle",
  "MediaFrame",
  "LowerThird",
  "KineticWords",
  "PromptAnswerCard",
  "LogoOutro",
]);

const parseArgs = (argv) => {
  const args = {};

  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      continue;
    }

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

const ensureDir = (dirPath) => {
  fs.mkdirSync(dirPath, {recursive: true});
};

const readJson = (filePath) => {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
};

const toNumber = (value, fallback) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const estimateLinesCount = (textLen, maxCharsPerLine) => {
  if (textLen <= 0) {
    return 1;
  }

  return Math.max(1, Math.ceil(textLen / Math.max(1, maxCharsPerLine)));
};

const unique = (values) => {
  return [...new Set(values.filter((v) => v !== undefined && v !== null && `${v}`.trim().length > 0))];
};

const countBy = (values) => {
  return values.reduce((acc, value) => {
    const key = `${value}`;
    if (!key.trim()) {
      return acc;
    }
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
};

const getRenderMode = (beat) => {
  const explicit = beat?.renderMode ?? beat?.render_mode;
  if (explicit && explicit !== "remotion_only") {
    return explicit;
  }

  if (beat.renderMode) {
    return beat.renderMode;
  }

  const intent = `${beat.intent ?? ""}`.toLowerCase();
  if (intent.includes("hook")) return "hero";
  if (intent.includes("outro")) return "outro";
  if (intent.includes("cta")) return "lowerThird";
  if (intent.includes("proof")) return "promptCard";
  if (intent.includes("process")) return "media";
  return "kinetic";
};

const resolveLayout = (quality, spec) => {
  return {
    ...DEFAULT_LAYOUT,
    ...(quality?.layout ?? {}),
    ...(spec?.layout ?? {}),
  };
};

const bboxForMode = (mode, width, height, layout) => {
  const heroW = clamp(layout.heroMaxWidthPct, 0.4, 0.9);

  const templates = {
    hero: {
      x: (1 - heroW) / 2,
      y: clamp(layout.heroYPct, 0.06, 0.45),
      w: heroW,
      h: clamp(layout.heroHeightPct, 0.16, 0.5),
    },
    lowerThird: {
      x: 0.1,
      y: clamp(layout.lowerThirdYPct, 0.5, 0.9),
      w: 0.8,
      h: 0.13,
    },
    promptCard: {
      x: (1 - clamp(layout.cardWidthPct, 0.5, 0.9)) / 2,
      y: clamp(layout.cardYPct, 0.08, 0.5),
      w: clamp(layout.cardWidthPct, 0.5, 0.9),
      h: clamp(layout.cardHeightPct, 0.22, 0.6),
    },
    kinetic: {x: 0.1, y: clamp(layout.kineticYPct, 0.45, 0.9), w: 0.8, h: 0.16},
    media: {
      x: clamp(layout.mediaPadXPct, 0.03, 0.18),
      y: clamp(layout.mediaPadYPct, 0.03, 0.2),
      w: 1 - 2 * clamp(layout.mediaPadXPct, 0.03, 0.18),
      h: 1 - 2 * clamp(layout.mediaPadYPct, 0.03, 0.2),
    },
    outro: {
      x: (1 - heroW) / 2,
      y: clamp(layout.heroYPct, 0.06, 0.45),
      w: heroW,
      h: clamp(layout.heroHeightPct, 0.16, 0.5),
    },
  };

  const box = templates[mode] ?? templates.kinetic;

  return {
    x: Math.round(box.x * width),
    y: Math.round(box.y * height),
    w: Math.round(box.w * width),
    h: Math.round(box.h * height),
  };
};

const modeToLayerType = (mode) => {
  if (mode === "hero") return "HeroTitle";
  if (mode === "lowerThird") return "LowerThird";
  if (mode === "promptCard") return "PromptAnswerCard";
  if (mode === "media") return "MediaFrame";
  if (mode === "outro") return "LogoOutro";
  return "KineticWords";
};

const layerTypeToMode = (type) => {
  if (type === "HeroTitle") return "hero";
  if (type === "LowerThird") return "lowerThird";
  if (type === "PromptAnswerCard") return "promptCard";
  if (type === "MediaFrame") return "media";
  if (type === "LogoOutro") return "outro";
  return "kinetic";
};

const getBeatLayers = (beat, renderMode) => {
  const raw = beat?.scene?.layers;
  if (Array.isArray(raw) && raw.length > 0) {
    return raw
      .filter((layer) => layer && typeof layer === "object")
      .map((layer) => ({
        type: `${layer.type ?? "KineticWords"}`,
        props: typeof layer.props === "object" && layer.props !== null ? layer.props : {},
      }));
  }

  return [{type: modeToLayerType(renderMode), props: {}}];
};

const isRenderableLayer = (type) => SUPPORTED_LAYER_TYPES.has(`${type ?? ""}`);

const estimateFontPx = (layer, bbox, maxFont) => {
  const type = `${layer?.type ?? ""}`;
  const kind = `${layer?.props?.kind ?? ""}`;

  if (type === "HeroTitle") return clamp(Math.round(bbox.h * 0.18), 30, maxFont);
  if (type === "LowerThird") return clamp(Math.round(bbox.h * 0.2), 26, 72);
  if (type === "KineticWords") return clamp(Math.round(bbox.h * 0.22), 24, 68);
  if (type === "PromptAnswerCard") return clamp(Math.round(bbox.h * 0.13), 22, 56);
  if (type === "LogoOutro") return clamp(Math.round(bbox.h * 0.16), 28, 72);
  if (type === "MediaFrame" && kind === "react") return 24;
  return 20;
};

const getLayerCharCount = (layer, fallbackText) => {
  const type = `${layer?.type ?? ""}`;
  const props = layer?.props ?? {};
  const fallbackLen = `${fallbackText ?? ""}`.length;

  if (type === "KineticWords") {
    const words = Array.isArray(props.words) ? props.words : [];
    return Math.max(fallbackLen, `${words.join(" ")}`.length);
  }
  if (type === "LowerThird") {
    return Math.max(fallbackLen, `${props.title ?? ""}`.length);
  }
  if (type === "HeroTitle") {
    return Math.max(fallbackLen, `${props.title ?? ""} ${props.subtitle ?? ""}`.trim().length);
  }
  if (type === "PromptAnswerCard") {
    return Math.max(fallbackLen, `${props.prompt ?? ""} ${props.answer ?? ""}`.trim().length);
  }
  if (type === "LogoOutro") {
    return Math.max(fallbackLen, `${props.tagline ?? ""}`.length);
  }
  return fallbackLen;
};

const isSafeMarginViolation = (bbox, width, height, margins) => {
  const left = width * toNumber(margins.marginLeftPct, 0.07);
  const right = width * toNumber(margins.marginRightPct, 0.07);
  const top = height * toNumber(margins.marginTopPct, 0.08);
  const bottom = height * toNumber(margins.marginBottomPct, 0.15);

  if (bbox.x < left) return true;
  if (bbox.y < top) return true;
  if (bbox.x + bbox.w > width - right) return true;
  if (bbox.y + bbox.h > height - bottom) return true;

  return false;
};

const isFrameOverflow = (bbox, width, height) => {
  if (bbox.x < 0) return true;
  if (bbox.y < 0) return true;
  if (bbox.x + bbox.w > width) return true;
  if (bbox.y + bbox.h > height) return true;
  return false;
};

const main = () => {
  const args = parseArgs(process.argv.slice(2));

  const specPath = path.resolve(process.cwd(), args.spec ?? DEFAULT_SPEC);
  const qualityPath = path.resolve(process.cwd(), args.quality ?? DEFAULT_QUALITY);
  const outPath = path.resolve(process.cwd(), args.out ?? DEFAULT_OUT);

  if (!fs.existsSync(specPath)) {
    throw new Error(`Spec file not found: ${specPath}`);
  }

  if (!fs.existsSync(qualityPath)) {
    throw new Error(`Quality config not found: ${qualityPath}`);
  }

  const spec = readJson(specPath);
  const quality = readJson(qualityPath);
  const layout = resolveLayout(quality, spec);

  const fps = toNumber(spec?.meta?.fps, toNumber(quality?.video?.fps, 30));
  const width = toNumber(spec?.meta?.width, toNumber(quality?.video?.width, 1920));
  const height = toNumber(spec?.meta?.height, toNumber(quality?.video?.height, 1080));
  const durationSec = toNumber(
    spec?.meta?.durationSec ?? spec?.meta?.duration_sec,
    toNumber(quality?.video?.durationSec, 60),
  );
  const compositionId = spec?.meta?.compositionId ?? "SkillExplainer60";

  const maxCharsPerLine = toNumber(quality?.limits?.maxCharsPerLine, 12);
  const maxFont = toNumber(quality?.limits?.maxFont, 110);

  const beats = (spec?.beats ?? []).map((beat, index) => {
    const text = `${beat?.text ?? beat?.line ?? ""}`;
    const textLen = text.length;
    const renderMode = getRenderMode(beat);
    const layers = getBeatLayers(beat, renderMode);
    const layerTypes = layers.map((layer) => `${layer.type ?? ""}`);
    const renderableLayerCount = layers.filter((layer) => isRenderableLayer(layer.type)).length;
    const reactContents = layers
      .filter((layer) => `${layer?.type ?? ""}` === "MediaFrame")
      .map((layer) => `${layer?.props?.reactContent ?? ""}`.trim())
      .filter((name) => name.length > 0);

    return {
      id: beat?.id ?? `beat-${index + 1}`,
      t0: toNumber(beat?.t0, index * 3),
      t1: toNumber(beat?.t1, (index + 1) * 3),
      intent: beat?.intent ?? "unknown",
      textLen,
      linesCount: estimateLinesCount(textLen, maxCharsPerLine),
      renderMode,
      transitionType: beat?.transitionType ?? beat?.transition_type ?? "fade",
      motionRecipe: beat?.motionRecipe ?? beat?.motion_recipe ?? "spring",
      text,
      layers,
      layerTypes,
      reactContents,
      renderableLayerCount,
      hasRenderableElements: renderableLayerCount > 0,
    };
  });

  const textBlocks = beats.flatMap((beat, beatIndex) => {
    return beat.layers.map((layer, layerIndex) => {
      const mode = layerTypeToMode(layer.type);
      const bbox = bboxForMode(mode, width, height, layout);
      const safeMarginViolation = isSafeMarginViolation(bbox, width, height, quality?.safeArea ?? {});
      const frameOverflow = isFrameOverflow(bbox, width, height);
      const chars = getLayerCharCount(layer, beat.text);
      const estimatedFontPx = estimateFontPx(layer, bbox, maxFont);
      const isTextLayer = layer.type !== "MediaFrame";
      const renderableLayer = isRenderableLayer(layer.type);

      return {
        id: `tb-${beat.id}-${beatIndex + 1}-${layerIndex + 1}`,
        beatId: beat.id,
        type: mode,
        layerType: layer.type,
        renderableLayer,
        bbox,
        frameOverflow,
        safeMarginViolation: isTextLayer ? safeMarginViolation : false,
        isTextLayer,
        chars,
        estimatedFontPx,
      };
    });
  });

  const manifest = {
    meta: {
      fps,
      width,
      height,
      durationSec,
      compositionId,
      renderedAt: new Date().toISOString(),
    },
    specPath: path.relative(process.cwd(), specPath),
    beats: beats.map((beat) => ({
      id: beat.id,
      t0: beat.t0,
      t1: beat.t1,
      intent: beat.intent,
      textLen: beat.textLen,
      linesCount: beat.linesCount,
      renderMode: beat.renderMode,
      transitionType: beat.transitionType,
      motionRecipe: beat.motionRecipe,
      layerTypes: beat.layerTypes,
      reactContents: beat.reactContents,
      renderableLayerCount: beat.renderableLayerCount,
      hasRenderableElements: beat.hasRenderableElements,
    })),
    elementTimeline: beats.map((beat) => ({
      beatId: beat.id,
      t0: beat.t0,
      t1: beat.t1,
      hasRenderableElements: beat.hasRenderableElements,
    })),
    textBlocks,
    effectsSummary: {
      transitionTypesUsed: unique(beats.map((beat) => beat.transitionType)),
      transitionTypeCounts: countBy(beats.map((beat) => beat.transitionType)),
      motionRecipesUsed: unique(beats.map((beat) => beat.motionRecipe)),
      motionRecipeCounts: countBy(beats.map((beat) => beat.motionRecipe)),
      componentTypesUsed: unique(beats.flatMap((beat) => beat.layerTypes)),
      componentTypeCounts: countBy(beats.flatMap((beat) => beat.layerTypes)),
      reactVariantsUsed: unique(beats.flatMap((beat) => beat.reactContents)),
      reactVariantCounts: countBy(beats.flatMap((beat) => beat.reactContents)),
      unsupportedLayerTypes: unique(
        beats.flatMap((beat) => beat.layerTypes.filter((type) => !isRenderableLayer(type))),
      ),
      beatCut: {
        flashOpacity: toNumber(quality?.beatCut?.flashOpacity, 0.08),
        flashDurationFrames: toNumber(quality?.beatCut?.flashDurationFrames, 2),
      },
    },
  };

  ensureDir(path.dirname(outPath));
  fs.writeFileSync(outPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(`Manifest written: ${path.relative(process.cwd(), outPath)}`);
};

main();
