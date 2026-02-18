// @ts-nocheck
const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_SPEC = 'src/specs/skill.timeline.json';
const DEFAULT_QUALITY = 'src/config/quality.json';
const DEFAULT_OUT = 'out/manifest.json';

const DEFAULT_LAYOUT = {
  safePadding: 72,
  mediaPadXPct: 0.085,
  mediaPadYPct: 0.13,
  kineticYPct: 0.58,
  lowerThirdYPct: 0.7,
  lowerThirdMaxWidthPct: 0.62,
  cardYPct: 0.24,
  cardWidthPct: 0.72,
  cardHeightPct: 0.44,
  heroMaxWidthPct: 0.78,
  heroYPct: 0.19,
  heroHeightPct: 0.36,
};

const SUPPORTED_LAYER_TYPES = new Set([
  'HeroTitle',
  'MediaFrame',
  'LowerThird',
  'KineticWords',
  'PromptAnswerCard',
  'LogoOutro',
  'BeforeAfter',
  'Stepper3',
  'Callout',
]);

const parseArgs = (argv) => {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
};

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const ensureDir = (p) => fs.mkdirSync(p, {recursive: true});
const toNumber = (v, f) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : f;
};
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

const unique = (values) => [...new Set(values.filter((v) => `${v ?? ''}`.trim().length > 0))];
const countBy = (values) =>
  values.reduce((acc, value) => {
    const key = `${value ?? ''}`.trim();
    if (!key) return acc;
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

const words = (text) =>
  `${text ?? ''}`
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean);

const HIGHLIGHT_STOPWORDS = new Set([
  'a',
  'an',
  'and',
  'as',
  'at',
  'by',
  'for',
  'from',
  'in',
  'into',
  'it',
  'of',
  'on',
  'or',
  'that',
  'the',
  'to',
  'with',
]);

const cleanWord = (word) => `${word ?? ''}`.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();

const isMeaningfulHighlightWord = (word) => {
  const cleaned = cleanWord(word);
  return cleaned.length >= 3 && !HIGHLIGHT_STOPWORDS.has(cleaned);
};

const extractHighlightedWords = (beat) => {
  const result = [];
  const beatWords = words(`${beat?.text ?? ''}`);
  const layers = Array.isArray(beat?.layers) ? beat.layers : [];
  for (const layer of layers) {
    if (`${layer?.type ?? ''}` !== 'KineticWords') continue;
    const props = layer?.props ?? {};
    const wsRaw = Array.isArray(props.words) ? props.words.map((w) => `${w}`) : beatWords;
    const ws = wsRaw.length > 0 ? wsRaw : beatWords;
    const emphasize = Array.isArray(props.emphasize) ? props.emphasize : [0];
    for (const idxRaw of emphasize) {
      const idx = Math.max(0, Math.min(ws.length - 1, Number(idxRaw)));
      const token = ws[idx];
      if (!isMeaningfulHighlightWord(token)) continue;
      result.push(cleanWord(token));
    }
  }
  return unique(result);
};

const maxWordsPerLineForBeat = (beat, quality, cookbook) => {
  const intent = `${beat.intent ?? ''}`.trim();
  const byIntent = cookbook?.intents?.[intent]?.constraints?.maxWordsPerLine;
  return toNumber(byIntent, toNumber(quality?.limits?.maxWordsPerLine, 7));
};

const maxLinesForBeat = (beat, quality, cookbook) => {
  const intent = `${beat.intent ?? ''}`.trim();
  const byIntent = cookbook?.intents?.[intent]?.constraints?.maxLines;
  return toNumber(byIntent, toNumber(quality?.limits?.maxLines, 2));
};

const estimateLinesByWords = (wordCount, maxWordsPerLine) => {
  if (wordCount <= 0) return 1;
  return Math.max(1, Math.ceil(wordCount / Math.max(1, maxWordsPerLine)));
};

const wrapWords = (text, maxWordsPerLine) => {
  const ws = words(text);
  const width = Math.max(1, maxWordsPerLine);
  if (ws.length === 0) return [];
  const linesNeeded = Math.max(1, Math.ceil(ws.length / width));
  const base = Math.floor(ws.length / linesNeeded);
  const extra = ws.length % linesNeeded;
  const lines = [];
  let cursor = 0;
  for (let i = 0; i < linesNeeded; i++) {
    const take = base + (i < extra ? 1 : 0);
    lines.push(ws.slice(cursor, cursor + take));
    cursor += take;
  }
  return lines;
};

const getRenderMode = (beat) => {
  const explicit = beat?.renderMode ?? beat?.render_mode;
  if (explicit && explicit !== 'remotion_only') return explicit;
  const intent = `${beat.intent ?? ''}`.toLowerCase();
  if (intent.includes('hook')) return 'hero';
  if (intent.includes('outro')) return 'outro';
  if (intent.includes('example')) return 'promptCard';
  if (intent.includes('problem')) return 'compare';
  if (intent.includes('how_steps') || intent.includes('pipeline')) return 'flow';
  return 'kinetic';
};

const modeToLayerType = (mode) => {
  if (mode === 'hero') return 'HeroTitle';
  if (mode === 'promptCard') return 'PromptAnswerCard';
  if (mode === 'outro') return 'LogoOutro';
  if (mode === 'compare') return 'BeforeAfter';
  if (mode === 'flow') return 'Stepper3';
  return 'KineticWords';
};

const pickReactContent = (intent, index = 0) => {
  const key = `${intent ?? ''}`.toLowerCase();
  if (key.includes('problem')) return index % 2 === 0 ? 'KeywordVsMeaningBroll' : 'SemanticOrbitBroll';
  if (key.includes('definition')) return 'EmbeddingsBroll';
  if (key.includes('analogy')) return 'VectorMapBroll';
  if (key.includes('how_steps')) return 'ChunksBroll';
  if (key.includes('pipeline')) return index % 2 === 0 ? 'RetrieveThenAnswerBroll' : 'PipelineBlocksBroll';
  if (key.includes('example')) return 'NearestNeighborsBroll';
  if (key.includes('recap')) return 'SearchIconBroll';
  return 'PipelineBlocksBroll';
};

const defaultLayerProps = (layerType, beat) => {
  const text = `${beat?.text ?? beat?.line ?? ''}`.trim();
  if (layerType === 'BeforeAfter') {
    return {
      beforeTitle: 'Keyword Search',
      afterTitle: 'Vector Search',
      beforeBullets: ['exact words only', 'synonyms missed', 'word mismatch'],
      afterBullets: ['intent match', 'semantic recall', 'nearby meaning'],
      marker: '→',
    };
  }
  if (layerType === 'Stepper3') {
    return {
      steps: [
        {title: 'Step 1', text: 'Chunk content'},
        {title: 'Step 2', text: 'Embed chunks'},
        {title: 'Step 3', text: 'Search nearest'},
      ],
    };
  }
  if (layerType === 'PromptAnswerCard') {
    return {
      prompt: text || 'User question',
      answer: 'Top relevant results from semantic retrieval.',
      appearMode: 'slideUp',
      typing: {enabled: true, cps: 20},
    };
  }
  if (layerType === 'Callout') {
    return {
      keyword: words(text).find((w) => w.replace(/[^a-zA-Z0-9]/g, '').length >= 3) ?? 'embedding',
      description: text,
    };
  }
  if (layerType === 'HeroTitle') {
    return {
      title: words(text).slice(0, 7).join(' '),
      subtitle: words(text).slice(0, 9).join(' '),
    };
  }
  if (layerType === 'LowerThird') {
    return {
      title: words(text).slice(0, 7).join(' '),
      durationSec: Math.max(2.5, toNumber(beat?.t1, 0) - toNumber(beat?.t0, 0)),
      align: 'left',
    };
  }
  return {};
};

const recipeLayersForBeat = (beat, cookbook) => {
  const intent = `${beat.intent ?? ''}`.trim();
  const recipe = cookbook?.intents?.[intent];
  if (recipe && Array.isArray(recipe.layers) && recipe.layers.length > 0) {
    return recipe.layers.map((type, idx) => {
      const layerType = `${type}`;
      if (layerType === 'MediaFrame') {
        return {
          type: layerType,
          props: {
            kind: 'react',
            reactContent: pickReactContent(intent, idx),
            fallbackReactContent: 'PipelineBlocksBroll',
          },
        };
      }
      return {type: layerType, props: defaultLayerProps(layerType, beat)};
    });
  }
  const fallbackType = modeToLayerType(getRenderMode(beat));
  if (fallbackType === 'MediaFrame') {
    return [
      {
        type: fallbackType,
        props: {
          kind: 'react',
          reactContent: pickReactContent(intent),
          fallbackReactContent: 'PipelineBlocksBroll',
        },
      },
    ];
  }
  return [{type: fallbackType, props: {}}];
};

const getBeatLayers = (beat, cookbook) => {
  const raw = beat?.scene?.layers;
  if (Array.isArray(raw) && raw.length > 0) {
    return raw
      .filter((layer) => layer && typeof layer === 'object')
      .map((layer) => ({
        type: `${layer.type ?? 'KineticWords'}`,
        props: (() => {
          const layerType = `${layer.type ?? 'KineticWords'}`;
          const baseProps = typeof layer.props === 'object' && layer.props !== null ? {...layer.props} : {};
          if (layerType !== 'MediaFrame') return baseProps;
          if (`${baseProps.reactContent ?? ''}`.trim().length > 0) return baseProps;
          return {
            ...baseProps,
            kind: 'react',
            reactContent: pickReactContent(beat.intent),
            fallbackReactContent: 'PipelineBlocksBroll',
          };
        })(),
      }));
  }
  return recipeLayersForBeat(beat, cookbook);
};

const layerTypeToMode = (type) => {
  if (type === 'HeroTitle') return 'hero';
  if (type === 'LowerThird') return 'lowerThird';
  if (type === 'PromptAnswerCard') return 'promptCard';
  if (type === 'MediaFrame') return 'media';
  if (type === 'LogoOutro') return 'outro';
  if (type === 'BeforeAfter') return 'compare';
  if (type === 'Stepper3') return 'flow';
  if (type === 'Callout') return 'callout';
  return 'kinetic';
};

const bboxForMode = (mode, width, height, layout) => {
  const isPortrait = height > width;
  const lowerThirdWidthPct = clamp(toNumber(layout.lowerThirdMaxWidthPct, isPortrait ? 0.82 : 0.62), 0.48, 0.84);
  const templates = {
    hero: {x: (1 - layout.heroMaxWidthPct) / 2, y: layout.heroYPct, w: layout.heroMaxWidthPct, h: layout.heroHeightPct},
    lowerThird: {x: 0.09, y: clamp(layout.lowerThirdYPct, 0.55, 0.86), w: lowerThirdWidthPct, h: 0.13},
    promptCard: {x: (1 - layout.cardWidthPct) / 2, y: clamp(layout.cardYPct, 0.1, 0.58), w: layout.cardWidthPct, h: layout.cardHeightPct},
    kinetic: {x: 0.1, y: clamp(layout.kineticYPct, 0.4, 0.88), w: 0.8, h: 0.16},
    media: {x: layout.mediaPadXPct, y: layout.mediaPadYPct, w: 1 - 2 * layout.mediaPadXPct, h: 1 - 2 * layout.mediaPadYPct},
    outro: {x: (1 - layout.heroMaxWidthPct) / 2, y: layout.heroYPct, w: layout.heroMaxWidthPct, h: layout.heroHeightPct},
    compare: isPortrait ? {x: 0.09, y: 0.22, w: 0.82, h: 0.4} : {x: 0.075, y: 0.16, w: 0.85, h: 0.46},
    flow: isPortrait ? {x: 0.09, y: 0.28, w: 0.82, h: 0.38} : {x: 0.075, y: 0.2, w: 0.85, h: 0.48},
    callout: isPortrait ? {x: 0.09, y: 0.26, w: 0.82, h: 0.3} : {x: 0.075, y: 0.22, w: 0.85, h: 0.34},
  };
  const box = templates[mode] ?? templates.kinetic;
  return {
    x: Math.round(box.x * width),
    y: Math.round(box.y * height),
    w: Math.round(box.w * width),
    h: Math.round(box.h * height),
  };
};

const isSafeMarginViolation = (bbox, width, height, margins) => {
  const left = width * toNumber(margins.marginLeftPct, 0.08);
  const right = width * toNumber(margins.marginRightPct, 0.08);
  const top = height * toNumber(margins.marginTopPct, 0.1);
  const bottom = height * toNumber(margins.marginBottomPct, 0.22);
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

const isRenderableLayer = (type) => SUPPORTED_LAYER_TYPES.has(`${type ?? ''}`);

const estimateFontPx = (layer, bbox, quality, stylekit) => {
  const type = `${layer?.type ?? ''}`;
  const maxFont = toNumber(quality?.limits?.maxFont, 120);
  const typo = stylekit?.typography ?? {};
  const styleHero = toNumber(typo.hero, 72);
  const styleTitle = toNumber(typo.title, 54);
  const styleBody = toNumber(typo.body, 40);
  const styleCaption = toNumber(typo.caption, 28);
  if (type === 'HeroTitle') return clamp(Math.round(Math.max(styleHero, bbox.h * 0.24)), 38, maxFont);
  if (type === 'LowerThird') return clamp(Math.round(Math.max(styleTitle * 0.72, bbox.h * 0.22)), 30, maxFont);
  if (type === 'KineticWords') return clamp(Math.round(Math.max(styleTitle * 0.68, bbox.h * 0.24)), 30, maxFont);
  if (type === 'PromptAnswerCard') return clamp(Math.round(Math.max(styleBody * 0.88, bbox.h * 0.16)), 28, maxFont);
  if (type === 'BeforeAfter' || type === 'Stepper3' || type === 'Callout')
    return clamp(Math.round(Math.max(styleBody * 0.82, styleCaption * 1.15, bbox.h * 0.16)), 30, maxFont);
  return clamp(Math.round(Math.max(styleBody * 0.7, bbox.h * 0.12)), 24, maxFont);
};

const getLayerCharCount = (layer, fallbackText) => {
  const type = `${layer?.type ?? ''}`;
  const props = layer?.props ?? {};
  const fallbackLen = `${fallbackText ?? ''}`.length;
  if (type === 'KineticWords') {
    const ws = Array.isArray(props.words) ? props.words : [];
    return Math.max(fallbackLen, `${ws.join(' ')}`.length);
  }
  if (type === 'LowerThird') return Math.max(fallbackLen, `${props.title ?? ''}`.length);
  if (type === 'HeroTitle') return Math.max(fallbackLen, `${props.title ?? ''} ${props.subtitle ?? ''}`.trim().length);
  if (type === 'PromptAnswerCard') return Math.max(fallbackLen, `${props.prompt ?? ''} ${props.answer ?? ''}`.trim().length);
  if (type === 'BeforeAfter') {
    const before = Array.isArray(props.beforeBullets) ? props.beforeBullets.join(' ') : '';
    const after = Array.isArray(props.afterBullets) ? props.afterBullets.join(' ') : '';
    return Math.max(fallbackLen, `${before} ${after}`.trim().length);
  }
  if (type === 'Stepper3') {
    const steps = Array.isArray(props.steps) ? props.steps.map((s) => `${s?.title ?? ''} ${s?.text ?? ''}`).join(' ') : '';
    return Math.max(fallbackLen, steps.length);
  }
  return fallbackLen;
};

const constrainTransitions = (beats, motionkit) => {
  const allowed = new Set((motionkit?.recipes?.transition?.types ?? ['fade', 'slide']).map((t) => `${t}`));
  const fallback = `${motionkit?.recipes?.transition?.default ?? 'fade'}`;
  return beats.map((beat, idx) => {
    const t = `${beat.transitionType ?? beat.transition_type ?? ''}`.trim();
    const chosen = allowed.has(t) ? t : idx % 2 === 0 ? 'fade' : 'slide';
    return {...beat, transitionType: allowed.has(chosen) ? chosen : fallback};
  });
};

const constrainMotionRecipes = (beats) => {
  const allowed = ['entrance', 'emphasis', 'transition'];
  const seen = new Set();
  return beats.map((beat, idx) => {
    const raw = `${beat.motionRecipe ?? beat.motion_recipe ?? ''}`.trim();
    let motion = allowed.includes(raw) ? raw : allowed[idx % allowed.length];
    if (seen.size >= 3 && !seen.has(motion)) motion = 'entrance';
    seen.add(motion);
    return {...beat, motionRecipe: motion};
  });
};

const summarizeNarrative = (beats) => {
  const intents = beats.map((b) => `${b.intent ?? ''}`);
  const hasHook = intents.includes('hook_title');
  const hasProblem = intents.includes('problem_compare') || intents.includes('myth_vs_fact');
  const hasHow = intents.includes('how_steps') || intents.includes('pipeline_flow') || intents.includes('pipeline_3');
  const hasExample = intents.includes('example_prompt');
  const hasRecap = intents.includes('recap_slogan');
  const hasOutro = intents.includes('outro');
  return {
    hasHook,
    hasExample,
    hasRecap,
    sectionCoverage: {
      hook: hasHook,
      problem: hasProblem,
      how: hasHow,
      example: hasExample,
      recap: hasRecap,
      outro: hasOutro,
    },
  };
};

const keywordsCount = (text) => {
  const bag = new Set(['vector', 'embedding', 'semantic', 'intent', 'retrieve', 'query', 'nearest', 'database', 'meaning']);
  const ws = words(text).map((w) => w.toLowerCase().replace(/[^a-z0-9]/g, ''));
  return ws.filter((w) => bag.has(w)).length;
};

const main = () => {
  const args = parseArgs(process.argv.slice(2));
  const specPath = path.resolve(process.cwd(), args.spec ?? DEFAULT_SPEC);
  const qualityPath = path.resolve(process.cwd(), args.quality ?? DEFAULT_QUALITY);
  const outPath = path.resolve(process.cwd(), args.out ?? DEFAULT_OUT);

  if (!fs.existsSync(specPath)) throw new Error(`Spec file not found: ${specPath}`);
  if (!fs.existsSync(qualityPath)) throw new Error(`Quality config not found: ${qualityPath}`);

  const stylekitPath = path.resolve(process.cwd(), 'src/style/stylekit.json');
  const motionkitPath = path.resolve(process.cwd(), 'src/style/motionkit.json');
  const cookbookPath = path.resolve(process.cwd(), 'src/style/cookbook.json');

  const spec = readJson(specPath);
  const quality = readJson(qualityPath);
  const stylekit = fs.existsSync(stylekitPath) ? readJson(stylekitPath) : {};
  const motionkit = fs.existsSync(motionkitPath) ? readJson(motionkitPath) : {};
  const cookbook = fs.existsSync(cookbookPath) ? readJson(cookbookPath) : {};

  const layout = {...DEFAULT_LAYOUT, ...(quality?.layout ?? {}), ...(spec?.layout ?? {})};

  const fps = toNumber(spec?.meta?.fps, toNumber(quality?.video?.fps, 30));
  const width = toNumber(spec?.meta?.width, toNumber(quality?.video?.width, 1080));
  const height = toNumber(spec?.meta?.height, toNumber(quality?.video?.height, 1920));
  const durationSec = toNumber(spec?.meta?.duration_sec ?? spec?.meta?.durationSec, toNumber(quality?.video?.durationSec, 60));
  const compositionId = spec?.meta?.compositionId ?? spec?.meta?.composition_id ?? 'ExplainerFromSpec';

  let beats = (spec?.beats ?? []).map((beat, index) => {
    const text = `${beat?.text ?? beat?.line ?? ''}`.trim();
    const beatWords = words(text);
    const maxWordsPerLine = maxWordsPerLineForBeat(beat, quality, cookbook);
    const maxLines = maxLinesForBeat(beat, quality, cookbook);
    const linesCount = estimateLinesByWords(beatWords.length, maxWordsPerLine);
    const overflow = linesCount > maxLines;

    const wrappedLines = wrapWords(text, maxWordsPerLine);

    const recipe = cookbook?.intents?.[`${beat?.intent ?? ''}`];
    const sceneRaw = beat?.scene ?? {};
    const sceneBackdrop = sceneRaw?.backdrop;
    const resolvedBackdrop =
      sceneBackdrop && typeof sceneBackdrop === 'object'
        ? {
            preset: `${sceneBackdrop.preset ?? 'gemini'}`,
            animate: sceneBackdrop.animate ?? true,
            intensity: toNumber(sceneBackdrop.intensity, 0.8),
          }
        : {
            preset: `${recipe?.backdrop?.preset ?? 'gemini'}`,
            animate: recipe?.backdrop?.animate ?? true,
            intensity: toNumber(recipe?.backdrop?.intensity, 0.8),
          };

    return {
      ...beat,
      id: beat?.id ?? `beat-${index + 1}`,
      t0: toNumber(beat?.t0, index * 3),
      t1: toNumber(beat?.t1, (index + 1) * 3),
      text,
      textLen: text.length,
      wordsCount: beatWords.length,
      maxWordsPerLine,
      maxLines,
      linesCount,
      overflow,
      wrappedLines,
      keywordsCount: keywordsCount(text),
      renderMode: getRenderMode(beat),
      layers: getBeatLayers(beat, cookbook),
      intent: `${beat?.intent ?? ''}`,
      scene: {
        ...(sceneRaw && typeof sceneRaw === 'object' ? sceneRaw : {}),
        backdrop: resolvedBackdrop,
      },
      transitionType: beat?.transitionType ?? beat?.transition_type,
      motionRecipe: beat?.motionRecipe ?? beat?.motion_recipe,
    };
  });

  beats = beats.sort((a, b) => a.t0 - b.t0);
  beats = constrainTransitions(beats, motionkit);
  beats = constrainMotionRecipes(beats);

  beats = beats.map((beat) => {
    const layerTypes = beat.layers.map((layer) => `${layer.type ?? ''}`);
    const reactContents = beat.layers
      .filter((layer) => `${layer.type ?? ''}` === 'MediaFrame')
      .map((layer) => `${layer.props?.reactContent ?? ''}`.trim())
      .filter((name) => name.length > 0);
    const renderableLayerCount = beat.layers.filter((layer) => isRenderableLayer(layer.type)).length;

    return {
      ...beat,
      layerTypes,
      reactContents,
      highlightedWords: extractHighlightedWords({
        text: beat.text,
        layers: beat.layers,
      }),
      renderableLayerCount,
      hasRenderableElements: renderableLayerCount > 0,
    };
  });

  const textBlocks = beats.flatMap((beat, beatIndex) =>
    beat.layers.map((layer, layerIndex) => {
      const mode = layerTypeToMode(layer.type);
      const bbox = bboxForMode(mode, width, height, layout);
      if (`${layer.type ?? ''}` === 'LowerThird') {
        const isLandscape = width >= height;
        const wordCount = words(beat.text).length;
        const hasTallVisual = beat.layerTypes.some((type) =>
          type === 'BeforeAfter' || type === 'Stepper3' || type === 'PromptAnswerCard',
        );
        const yPct = clamp(layout.lowerThirdYPct + (isLandscape && hasTallVisual ? 0.04 : 0), 0.56, 0.9);
        const widthPct = clamp(
          layout.lowerThirdMaxWidthPct + (isLandscape && wordCount <= 9 ? 0.08 : 0),
          0.5,
          0.84,
        );
        bbox.y = Math.round(yPct * height);
        bbox.w = Math.round(widthPct * width);
      }
      const safeMarginViolation = isSafeMarginViolation(bbox, width, height, quality?.safeArea ?? {
        marginLeftPct: stylekit?.safeArea?.leftPct ?? 0.08,
        marginRightPct: stylekit?.safeArea?.rightPct ?? 0.08,
        marginTopPct: stylekit?.safeArea?.topPct ?? 0.1,
        marginBottomPct: stylekit?.safeArea?.bottomPct ?? 0.22,
      });
      const frameOverflow = isFrameOverflow(bbox, width, height);
      const chars = getLayerCharCount(layer, beat.text);
      const estimatedFontPx = estimateFontPx(layer, bbox, quality, stylekit);
      const textLikeLayerTypes = new Set([
        'HeroTitle',
        'LowerThird',
        'KineticWords',
        'PromptAnswerCard',
        'Callout',
      ]);
      const isTextLayer = textLikeLayerTypes.has(`${layer.type ?? ''}`);

      return {
        id: `tb-${beat.id}-${beatIndex + 1}-${layerIndex + 1}`,
        beatId: beat.id,
        type: mode,
        layerType: layer.type,
        renderableLayer: isRenderableLayer(layer.type),
        bbox,
        frameOverflow,
        safeMarginViolation: isTextLayer ? safeMarginViolation : false,
        isTextLayer,
        chars,
        text: beat.text,
        maxLines: beat.maxLines,
        maxWordsPerLine: beat.maxWordsPerLine,
        plannedLines: beat.linesCount,
        estimatedFontPx,
      };
    }),
  );

  const safeAreaViolations = textBlocks.filter((block) => block.safeMarginViolation).length;
  const narrative = summarizeNarrative(beats);
  const transitionTypesUsed = unique(beats.map((beat) => beat.transitionType));
  const motionRecipesUsed = unique(beats.map((beat) => beat.motionRecipe));

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
      text: beat.text,
      textLen: beat.textLen,
      wordsCount: beat.wordsCount,
      linesCount: beat.linesCount,
      renderMode: beat.renderMode,
      transitionType: beat.transitionType,
      motionRecipe: beat.motionRecipe,
      backdropPreset: `${beat?.scene?.backdrop?.preset ?? 'gemini'}`,
      backdropIntensity: toNumber(beat?.scene?.backdrop?.intensity, 0.8),
      layerTypes: beat.layerTypes,
      reactContents: beat.reactContents,
      highlightedWords: beat.highlightedWords,
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
    narrative,
    density: {
      perBeat: beats.map((beat) => ({
        beatId: beat.id,
        text: beat.text,
        words: beat.wordsCount,
        lines: beat.linesCount,
        wrappedLines: beat.wrappedLines.map((line) => line.join(' ')),
        lineWordCounts: beat.wrappedLines.map((line) => line.length),
        keywordsCount: beat.keywordsCount,
        maxWordsPerLine: beat.maxWordsPerLine,
        maxLines: beat.maxLines,
        overflow: beat.overflow,
      })),
    },
    motionSummary: {
      transitionTypesUsed,
      motionRecipesUsed,
      countByType: {
        transition: countBy(beats.map((beat) => beat.transitionType)),
        motion: countBy(beats.map((beat) => beat.motionRecipe)),
      },
      beatCut: {
        flashOpacity: toNumber(quality?.beatCut?.flashOpacity, 0.08),
        flashDurationFrames: toNumber(quality?.beatCut?.flashDurationFrames, 2),
      },
    },
    layoutSummary: {
      safeAreaViolations,
    },
    effectsSummary: {
      transitionTypesUsed,
      transitionTypeCounts: countBy(beats.map((beat) => beat.transitionType)),
      motionRecipesUsed,
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
  fs.writeFileSync(outPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  console.log(`Manifest written: ${path.relative(process.cwd(), outPath)}`);
};

main();
