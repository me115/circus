import {ReactNode} from "react";
import {TransitionSeries, linearTiming} from "@remotion/transitions";
import {fade} from "@remotion/transitions/fade";
import {slide} from "@remotion/transitions/slide";
import {AbsoluteFill, Audio, interpolate, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {BeforeAfter} from "../components/BeforeAfter";
import {BeatCut} from "../components/BeatCut";
import {BrandBackdrop} from "../components/BrandBackdrop";
import {Callout} from "../components/Callout";
import {HeroTitle} from "../components/HeroTitle";
import {KineticWords} from "../components/KineticWords";
import {LogoOutro} from "../components/LogoOutro";
import {LowerThird} from "../components/LowerThird";
import {MediaFrame} from "../components/MediaFrame";
import {ProgrammaticBroll} from "../components/ProgrammaticBroll";
import {PromptAnswerCard} from "../components/PromptAnswerCard";
import {Stepper3} from "../components/Stepper3";
import {routeStoryboard} from "../router/intent_router";
import {normalizeStoryboard} from "../router/storyboard_normalizer";
import {motionkit} from "../style";
import {constrainTransitionType} from "../theme/motion";
import {tokens} from "../theme/tokens";
import {StylePreset} from "../theme/types";
import {
  BackdropConfig,
  LayoutConfig,
  QualityConfig,
  SceneLayer,
  SkillTimelineSpec,
  TimelineBeat,
} from "../specs/types";
import {assets} from "../utils/assets";

type SkillExplainer60Props = {
  spec?: SkillTimelineSpec;
  quality?: QualityConfig;
};

type NormalizedBeat = TimelineBeat & {
  text: string;
  renderMode: string;
  transitionType: string;
  motionRecipe: string;
  startFrame: number;
  durationInFrames: number;
  layers: SceneLayer[];
  backdrop: Required<BackdropConfig>;
};

const DEFAULT_LAYOUT: Required<LayoutConfig> = {
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

const asRecord = (value: unknown): Record<string, unknown> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value as Record<string, unknown>;
};

const asString = (value: unknown, fallback = ""): string => {
  return typeof value === "string" ? value : fallback;
};

const asNumber = (value: unknown, fallback: number): number => {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
};

const asBool = (value: unknown, fallback: boolean): boolean => {
  return typeof value === "boolean" ? value : fallback;
};

const asStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
};

const asNumberArray = (value: unknown): number[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is number => typeof item === "number" && Number.isFinite(item));
};

const pickRenderMode = (beat: TimelineBeat): string => {
  const explicit = beat.renderMode ?? beat.render_mode;
  if (explicit && explicit !== "remotion_only") {
    return explicit;
  }

  const layers = beat.scene?.layers ?? [];
  if (layers.length > 0) {
    return "scene";
  }

  const intent = `${beat.intent ?? ""}`.toLowerCase();
  if (intent.includes("hook")) return "hero";
  if (intent.includes("outro")) return "outro";
  if (intent.includes("proof")) return "promptCard";
  if (intent.includes("process")) return "media";
  if (intent.includes("cta")) return "lowerThird";
  return "kinetic";
};

const resolveBackdrop = (beat: TimelineBeat): Required<BackdropConfig> => {
  const cfg = beat.scene?.backdrop ?? {};
  const presetRaw = cfg.preset;
  const preset: StylePreset =
    presetRaw === "dark" || presetRaw === "light" || presetRaw === "gemini"
      ? presetRaw
      : "gemini";

  return {
    preset,
    animate: cfg.animate ?? true,
    intensity: cfg.intensity ?? 0.85,
  };
};

const normalizeBeats = (
  spec: SkillTimelineSpec | undefined,
  fps: number,
  durationInFrames: number,
): NormalizedBeat[] => {
  const beats = [...(spec?.beats ?? [])].sort((a, b) => a.t0 - b.t0);

  if (beats.length === 0) {
    return [
      {
        id: "fallback",
        t0: 0,
        t1: durationInFrames / fps,
        intent: "fallback",
        text: "Quality loop active",
        renderMode: "hero",
        transitionType: "fade",
        motionRecipe: "spring",
        startFrame: 0,
        durationInFrames,
        layers: [],
        backdrop: {preset: "gemini", animate: true, intensity: 0.85},
      },
    ];
  }

  let cursor = 0;

  const normalized = beats.map((beat, index) => {
    const declaredDuration = Math.max(0.6, (beat.t1 ?? 0) - (beat.t0 ?? 0));
    const fromSpec = Math.max(18, Math.round(declaredDuration * fps));
    const remaining = durationInFrames - cursor;
    const isLast = index === beats.length - 1;
    const duration = isLast
      ? Math.max(18, remaining)
      : Math.max(18, Math.min(fromSpec, remaining));

    const normalizedBeat: NormalizedBeat = {
      ...beat,
      text: beat.text ?? beat.line ?? "",
      renderMode: pickRenderMode(beat),
      transitionType: beat.transitionType ?? beat.transition_type ?? "fade",
      motionRecipe: beat.motionRecipe ?? beat.motion_recipe ?? "spring",
      startFrame: cursor,
      durationInFrames: duration,
      layers: beat.scene?.layers ?? [],
      backdrop: resolveBackdrop(beat),
    };

    cursor += duration;
    return normalizedBeat;
  });

  if (cursor < durationInFrames) {
    normalized.push({
      id: "tail",
      t0: cursor / fps,
      t1: durationInFrames / fps,
      intent: "tail",
      text: "Keep improving by measurable deltas.",
      renderMode: "outro",
      transitionType: "fade",
      motionRecipe: "spring",
      startFrame: cursor,
      durationInFrames: durationInFrames - cursor,
      layers: [],
      backdrop: {preset: "gemini", animate: true, intensity: 0.82},
    });
  }

  return normalized;
};

const prepareSpec = (spec: SkillTimelineSpec | undefined): SkillTimelineSpec | undefined => {
  if (!spec) {
    return spec;
  }
  const normalized = normalizeStoryboard(spec, {
    minBeatSec: 2.5,
    maxBeatSec: 4.0,
    targetBeatSec: 3.0,
    maxWordsPerLine: 7,
    maxLines: 2,
  });
  return routeStoryboard(normalized.spec);
};

const renderWords = (text: string | undefined): string[] => {
  if (!text) {
    return [];
  }
  return text
    .split(/\s+/)
    .map((w) => w.trim())
    .filter((w) => w.length > 0);
};

const HIGHLIGHT_STOPWORDS = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "by",
  "for",
  "from",
  "in",
  "into",
  "it",
  "of",
  "on",
  "or",
  "that",
  "the",
  "to",
  "with",
]);

const isMeaningfulHighlightWord = (word: string): boolean => {
  const cleaned = word.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
  if (cleaned.length < 3) {
    return false;
  }
  return !HIGHLIGHT_STOPWORDS.has(cleaned);
};

const sanitizeEmphasize = (words: string[], raw: number[]): number[] => {
  if (words.length === 0) {
    return [0];
  }
  const used = new Set<number>();
  const meaningful = words
    .map((word, idx) => ({word, idx}))
    .filter((item) => isMeaningfulHighlightWord(item.word))
    .map((item) => item.idx);
  const fallback = meaningful.length > 0 ? meaningful[0] : 0;

  const normalized: number[] = [];
  for (const value of raw) {
    if (!Number.isFinite(value)) {
      continue;
    }
    const idx = Math.max(0, Math.min(words.length - 1, Math.round(value)));
    if (!isMeaningfulHighlightWord(words[idx])) {
      continue;
    }
    if (used.has(idx)) {
      continue;
    }
    used.add(idx);
    normalized.push(idx);
  }

  if (normalized.length > 0) {
    return normalized;
  }
  return [fallback];
};

const getKineticMode = (motionRecipe: string): "pop" | "slide" | "type" => {
  if (motionRecipe === "slide" || motionRecipe === "kenburns") {
    return "slide";
  }
  if (motionRecipe === "type") {
    return "type";
  }
  return "pop";
};

const getPromptAppearMode = (motionRecipe: string): "slideUp" | "fade" | "pop" => {
  if (motionRecipe === "slide") {
    return "slideUp";
  }
  if (motionRecipe === "spring" || motionRecipe === "pop") {
    return "pop";
  }
  return "fade";
};

const getKenBurnsByRecipe = (recipe: string, index: number) => {
  if (recipe === "kenburns") {
    return {
      enabled: true,
      fromScale: 1.03,
      toScale: 1.1,
      fromX: index % 2 === 0 ? -12 : 12,
      toX: index % 2 === 0 ? 10 : -10,
      fromY: -8,
      toY: 8,
    };
  }

  if (recipe === "slide") {
    return {
      enabled: true,
      fromScale: 1.0,
      toScale: 1.04,
      fromX: index % 2 === 0 ? -16 : 16,
      toX: index % 2 === 0 ? 8 : -8,
      fromY: 0,
      toY: 0,
    };
  }

  if (recipe === "spring" || recipe === "pop") {
    return {
      enabled: true,
      fromScale: 0.98,
      toScale: 1.05,
      fromX: 0,
      toX: index % 2 === 0 ? 4 : -4,
      fromY: -2,
      toY: 2,
    };
  }

  return {
    enabled: true,
    fromScale: 1.01,
    toScale: 1.07,
    fromX: index % 2 === 0 ? -8 : 8,
    toX: index % 2 === 0 ? 8 : -6,
    fromY: -4,
    toY: 5,
  };
};

const defaultBrollByIntent = (intent: string): string => {
  const key = intent.toLowerCase();
  if (key.includes("problem")) return "KeywordVsMeaningBroll";
  if (key.includes("analogy")) return "VectorMapBroll";
  if (key.includes("step1")) return "ChunksBroll";
  if (key.includes("step2")) return "EmbeddingsBroll";
  if (key.includes("step3")) return "StoreAndLinkBroll";
  if (key.includes("nearest")) return "NearestNeighborsBroll";
  if (key.includes("use")) return "UseCasesIconsBroll";
  if (key.includes("rag")) return "RetrieveThenAnswerBroll";
  return "PipelineBlocksBroll";
};

const renderLayer = ({
  beat,
  layer,
  index,
  layout,
  frameWidth,
  frameHeight,
}: {
  beat: NormalizedBeat;
  layer: SceneLayer;
  index: number;
  layout: Required<LayoutConfig>;
  frameWidth: number;
  frameHeight: number;
}): ReactNode => {
  const props = asRecord(layer.props);
  const mediaPadX = Math.round(frameWidth * layout.mediaPadXPct);
  const mediaPadY = Math.round(frameHeight * layout.mediaPadYPct);

  if (layer.type === "HeroTitle") {
    const title = asString(props.title, beat.text);
    const subtitle = asString(props.subtitle);
    const align = asString(props.align, "center") === "left" ? "left" : "center";
    const enterDelayFrames = asNumber(props.enterDelayFrames, 4);
    const accentWord = asString(props.accentWord);

    return (
      <div
        key={`${beat.id}-hero-${index}`}
        style={{
          position: "absolute",
          left: Math.round(frameWidth * (1 - layout.heroMaxWidthPct) * 0.5),
          top: Math.round(frameHeight * layout.heroYPct),
          width: Math.round(frameWidth * layout.heroMaxWidthPct),
          height: Math.round(frameHeight * layout.heroHeightPct),
        }}
      >
        <HeroTitle
          title={title}
          subtitle={subtitle}
          align={align}
          enterDelayFrames={enterDelayFrames}
          accentWord={accentWord || undefined}
        />
      </div>
    );
  }

  if (layer.type === "MediaFrame") {
    const kind = asString(props.kind, "react");
    if (kind === "react") {
      return (
        <AbsoluteFill key={`${beat.id}-react-${index}`}>
          <ProgrammaticBroll
            name={asString(props.reactContent)}
            fallbackName={asString(props.fallbackReactContent, "PipelineBlocksBroll")}
          />
        </AbsoluteFill>
      );
    }

    const srcRaw = asString(props.src);
    const safeSrc = srcRaw ? staticFile(srcRaw) : index % 2 === 0 ? assets.demoImage1 : assets.demoImage2;
    const mediaKind = kind === "video" ? "video" : "image";

    return (
      <AbsoluteFill key={`${beat.id}-media-${index}`} style={{padding: `${mediaPadY}px ${mediaPadX}px`}}>
        <MediaFrame
          kind={mediaKind}
          src={safeSrc}
          startFrame={asNumber(props.startFrame, 0)}
          durationInFrames={Math.max(12, beat.durationInFrames - 2)}
          kenBurns={getKenBurnsByRecipe(beat.motionRecipe, index)}
        />
      </AbsoluteFill>
    );
  }

  if (layer.type === "KineticWords") {
    const words = asStringArray(props.words);
    const emphasize = asNumberArray(props.emphasize);
    const modeRaw = asString(props.mode, "pop");
    const mode = modeRaw === "slide" || modeRaw === "type" ? modeRaw : "pop";
    const startFrameOffset = asNumber(props.startFrameOffset, 4);

    const wordList = words.length > 0 ? words : renderWords(beat.text);
    const emphasizeList = sanitizeEmphasize(wordList, emphasize.length > 0 ? emphasize : [0]);

    return (
      <div
        key={`${beat.id}-kinetic-${index}`}
        style={{
          position: "absolute",
          left: Math.round(frameWidth * 0.1),
          right: Math.round(frameWidth * 0.1),
          top: Math.round(frameHeight * layout.kineticYPct),
          fontSize: tokens.typography.sizes.body,
        }}
      >
        <KineticWords
          words={wordList}
          startFrame={startFrameOffset}
          wordStagger={6}
          mode={mode}
          emphasize={emphasizeList}
        />
      </div>
    );
  }

  if (layer.type === "LowerThird") {
    const durationSec = asNumber(props.durationSec, beat.durationInFrames / 30);
    const title = asString(props.title, beat.text);
    const source = asString(props.source);
    const align = asString(props.align, "left") === "right" ? "right" : "left";
    const startFrame = asNumber(props.startFrame, 4);
    const durationInFrames = Math.max(12, Math.round(durationSec * 30));
    const isLandscape = frameWidth >= frameHeight;
    const wordCount = renderWords(title).length;
    const hasTallVisual = beat.layers.some(
      (item) =>
        item.type === "BeforeAfter" || item.type === "Stepper3" || item.type === "PromptAnswerCard",
    );
    const yPctBase = layout.lowerThirdYPct + (isLandscape && hasTallVisual ? 0.04 : 0);
    const yPct = Math.min(0.9, Math.max(0.56, yPctBase));
    const maxWidthPct = Math.max(
      0.5,
      Math.min(
        0.84,
        layout.lowerThirdMaxWidthPct + (isLandscape && wordCount <= 9 ? 0.08 : 0),
      ),
    );

    return (
      <LowerThird
        key={`${beat.id}-lt-${index}`}
        title={title}
        source={source}
        startFrame={startFrame}
        durationInFrames={Math.min(durationInFrames, beat.durationInFrames - 1)}
        align={align}
        yPct={yPct}
        maxWidthPct={maxWidthPct}
      />
    );
  }

  if (layer.type === "PromptAnswerCard") {
    const typingRaw = asRecord(props.typing);
    const prompt = asString(props.prompt, beat.text);
    const answer = asString(props.answer, "Answer from retrieved context.");
    const appearRaw = asString(props.appearMode, "slideUp");
    const appearMode = appearRaw === "fade" || appearRaw === "pop" ? appearRaw : "slideUp";
    const typing = {
      enabled: asBool(typingRaw.enabled, false),
      cps: asNumber(typingRaw.cps, 20),
    };

    return (
      <div
        key={`${beat.id}-card-${index}`}
        style={{
          position: "absolute",
          left: Math.round((1 - layout.cardWidthPct) * frameWidth * 0.5),
          top: Math.round(frameHeight * layout.cardYPct),
          width: Math.round(frameWidth * layout.cardWidthPct),
          height: Math.round(frameHeight * layout.cardHeightPct),
          display: "flex",
          alignItems: "center",
        }}
      >
        <PromptAnswerCard
          prompt={prompt}
          answer={answer}
          startFrame={asNumber(props.startFrame, 3)}
          appearMode={appearMode}
          showCursor
          typing={typing}
        />
      </div>
    );
  }

  if (layer.type === "BeforeAfter") {
    const beforeBullets = asStringArray(props.beforeBullets);
    const afterBullets = asStringArray(props.afterBullets);
    const isPortrait = frameHeight > frameWidth;
    return (
      <div
        key={`${beat.id}-before-after-${index}`}
        style={{
          position: "absolute",
          left: Math.round(frameWidth * (isPortrait ? 0.09 : 0.075)),
          right: Math.round(frameWidth * (isPortrait ? 0.09 : 0.075)),
          top: Math.round(frameHeight * (isPortrait ? 0.22 : 0.16)),
          height: Math.round(frameHeight * (isPortrait ? 0.4 : 0.46)),
        }}
      >
        <BeforeAfter
          beforeTitle={asString(props.beforeTitle, "Before")}
          afterTitle={asString(props.afterTitle, "After")}
          beforeBullets={beforeBullets.length > 0 ? beforeBullets : ["exact match", "synonym miss"]}
          afterBullets={afterBullets.length > 0 ? afterBullets : ["intent match", "semantic recall"]}
          marker={asString(props.marker, "→")}
        />
      </div>
    );
  }

  if (layer.type === "Stepper3") {
    const stepsRaw = Array.isArray(props.steps) ? props.steps : [];
    const isPortrait = frameHeight > frameWidth;
    const steps = stepsRaw
      .filter((s): s is Record<string, unknown> => !!s && typeof s === "object")
      .map((step, idx) => ({
        title: asString(step.title, `Step ${idx + 1}`),
        text: asString(step.text, "Explain clearly"),
      }));
    return (
      <div
        key={`${beat.id}-stepper-${index}`}
        style={{
          position: "absolute",
          left: Math.round(frameWidth * (isPortrait ? 0.09 : 0.075)),
          right: Math.round(frameWidth * (isPortrait ? 0.09 : 0.075)),
          top: Math.round(frameHeight * (isPortrait ? 0.28 : 0.2)),
          height: Math.round(frameHeight * (isPortrait ? 0.38 : 0.48)),
        }}
      >
        <Stepper3
          steps={steps.length > 0 ? steps : [
            {title: "Step 1", text: "Chunk"},
            {title: "Step 2", text: "Embed"},
            {title: "Step 3", text: "Search"},
          ]}
        />
      </div>
    );
  }

  if (layer.type === "Callout") {
    return (
      <div
        key={`${beat.id}-callout-${index}`}
        style={{
          position: "absolute",
          left: Math.round(frameWidth * 0.09),
          right: Math.round(frameWidth * 0.09),
          top: Math.round(frameHeight * 0.28),
        }}
      >
        <Callout
          keyword={asString(props.keyword, "embedding")}
          description={asString(props.description, beat.text)}
        />
      </div>
    );
  }

  if (layer.type === "LogoOutro") {
    const logoSrcRaw = asString(props.logoSrc, "logo.png");
    const chimeSrcRaw = asString(props.chimeSrc);
    const logoSrc = logoSrcRaw ? staticFile(logoSrcRaw) : assets.logo;
    const chimeSrc = chimeSrcRaw ? staticFile(chimeSrcRaw) : assets.chime;

    return (
      <LogoOutro
        key={`${beat.id}-outro-${index}`}
        logoSrc={logoSrc}
        tagline={asString(props.tagline, beat.text)}
        startFrame={0}
        durationInFrames={beat.durationInFrames}
        chimeSrc={chimeSrc}
      />
    );
  }

  return null;
};

const renderFallbackScene = ({
  beat,
  layout,
  frameWidth,
  frameHeight,
}: {
  beat: NormalizedBeat;
  layout: Required<LayoutConfig>;
  frameWidth: number;
  frameHeight: number;
}): ReactNode => {
  const words = renderWords(beat.text);
  const kineticMode = getKineticMode(beat.motionRecipe);
  const promptAppearMode = getPromptAppearMode(beat.motionRecipe);
  const fallbackEmphasize = sanitizeEmphasize(words, [0, Math.max(0, words.length - 1)]);

  if (beat.renderMode === "hero") {
    return (
      <div
        style={{
          position: "absolute",
          left: Math.round(frameWidth * (1 - layout.heroMaxWidthPct) * 0.5),
          top: Math.round(frameHeight * layout.heroYPct),
          width: Math.round(frameWidth * layout.heroMaxWidthPct),
          height: Math.round(frameHeight * layout.heroHeightPct),
        }}
      >
        <HeroTitle title={beat.text} subtitle="Explain clearly with visual structure." enterDelayFrames={4} />
      </div>
    );
  }

  if (beat.renderMode === "promptCard") {
    return (
      <div
        style={{
          position: "absolute",
          left: Math.round((1 - layout.cardWidthPct) * frameWidth * 0.5),
          top: Math.round(frameHeight * layout.cardYPct),
          width: Math.round(frameWidth * layout.cardWidthPct),
          height: Math.round(frameHeight * layout.cardHeightPct),
          display: "flex",
          alignItems: "center",
        }}
      >
        <PromptAnswerCard
          prompt={beat.text}
          answer="This scene mixes concepts, structure, and examples in one frame."
          startFrame={3}
          appearMode={promptAppearMode}
          showCursor
          typing={{enabled: true, cps: 28}}
        />
      </div>
    );
  }

  if (beat.renderMode === "outro") {
    return (
      <LogoOutro
        logoSrc={assets.logo}
        tagline={beat.text}
        startFrame={0}
        durationInFrames={beat.durationInFrames}
        chimeSrc={assets.chime}
      />
    );
  }

  return (
    <>
      <ProgrammaticBroll name={defaultBrollByIntent(beat.intent)} fallbackName="PipelineBlocksBroll" />
      <div
        style={{
          position: "absolute",
          left: Math.round(frameWidth * 0.1),
          right: Math.round(frameWidth * 0.1),
          top: Math.round(frameHeight * layout.kineticYPct),
        }}
      >
        <KineticWords
          words={words.length > 0 ? words : ["Clear", "Visual", "Story"]}
          startFrame={4}
          wordStagger={6}
          mode={beat.renderMode === "media" ? "slide" : kineticMode}
          emphasize={words.length > 0 ? fallbackEmphasize : [0, 2]}
        />
      </div>
      <LowerThird
        title={beat.text}
        source=""
        startFrame={6}
        durationInFrames={Math.max(12, beat.durationInFrames - 10)}
        align="left"
        yPct={Math.min(0.9, Math.max(0.56, layout.lowerThirdYPct + (frameWidth >= frameHeight ? 0.04 : 0)))}
        maxWidthPct={Math.max(0.52, Math.min(0.84, layout.lowerThirdMaxWidthPct + (frameWidth >= frameHeight ? 0.08 : 0)))}
      />
    </>
  );
};

const BeatScene = ({
  beat,
  layout,
}: {
  beat: NormalizedBeat;
  layout: Required<LayoutConfig>;
}) => {
  const {width, height} = useVideoConfig();
  const hasLayers = beat.layers.length > 0;

  return (
    <AbsoluteFill>
      <BrandBackdrop
        preset={beat.backdrop.preset}
        animate={beat.backdrop.animate}
        intensity={beat.backdrop.intensity}
        safePadding={layout.safePadding}
      />
      {hasLayers
        ? beat.layers.map((layer, idx) =>
            renderLayer({
              beat,
              layer,
              index: idx,
              layout,
              frameWidth: width,
              frameHeight: height,
            }),
          )
        : renderFallbackScene({beat, layout, frameWidth: width, frameHeight: height})}
    </AbsoluteFill>
  );
};

const HookIntro = ({
  text,
  durationInFrames,
}: {
  text: string;
  durationInFrames: number;
}) => {
  const frame = useCurrentFrame();
  if (frame >= durationInFrames) {
    return null;
  }

  const fadeInFrames = Math.max(8, Math.floor(durationInFrames * 0.18));
  const fadeOutFrames = Math.max(10, Math.floor(durationInFrames * 0.22));
  const outStart = Math.max(fadeInFrames + 6, durationInFrames - fadeOutFrames);
  const opacity = interpolate(
    frame,
    [0, fadeInFrames, outStart, durationInFrames],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const scale = interpolate(frame, [0, fadeInFrames, durationInFrames], [0.985, 1, 1.01], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundImage:
          "radial-gradient(circle at 22% 26%, rgba(124,92,255,0.16), transparent 45%), radial-gradient(circle at 78% 72%, rgba(45,226,230,0.14), transparent 42%), linear-gradient(138deg, #05070f 0%, #0B1020 56%, #101a33 100%)",
        justifyContent: "center",
        alignItems: "center",
        opacity,
        transform: `scale(${scale})`,
        zIndex: 200,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          width: "82%",
          textAlign: "center",
          color: "#ffffff",
          fontFamily: tokens.typography.fontFamilySans,
          fontWeight: 760,
          fontSize: Math.max(68, Math.round(tokens.typography.sizes.hero * 0.78)),
          lineHeight: 1.08,
          letterSpacing: -0.6,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

export const SkillExplainer60 = ({spec, quality}: SkillExplainer60Props) => {
  const {fps, durationInFrames} = useVideoConfig();
  const preparedSpec = prepareSpec(spec);

  const layout: Required<LayoutConfig> = {
    ...DEFAULT_LAYOUT,
    ...(quality?.layout ?? {}),
    ...(preparedSpec?.layout ?? {}),
  };

  const beats = normalizeBeats(preparedSpec, fps, durationInFrames);
  const audioBedVolume = preparedSpec?.meta?.audioBedVolume ?? 0.08;
  const audioLayerCount = Math.max(
    1,
    Math.min(4, Math.floor(preparedSpec?.meta?.audioLayerCount ?? 1)),
  );
  const voiceoverSrcRaw = preparedSpec?.audio?.src?.trim();
  const voiceoverSrc = voiceoverSrcRaw ? staticFile(voiceoverSrcRaw) : null;
  const voiceoverStart = Math.max(0, Number(preparedSpec?.audio?.startSec ?? 0));

  const beatCutCfg = preparedSpec?.global_overlays?.beatcut;
  const beatCutEnabled = beatCutCfg?.enabled ?? true;
  const beatCutFrames =
    beatCutCfg?.beatsInFrames && beatCutCfg.beatsInFrames.length > 0
      ? beatCutCfg.beatsInFrames
      : beats.map((beat) => beat.startFrame);
  const transitionFrames = beats.map((beat, index) =>
    index === beats.length - 1
      ? 0
      : Math.max(
          motionkit.recipes.transition.durationFrames,
          Math.min(20, Math.floor(beat.durationInFrames * 0.18)),
        ),
  );
  const hookEnabled = preparedSpec?.meta?.hookEnabled ?? false;
  const hookDurationSec = Math.max(1.8, Math.min(2.4, Number(preparedSpec?.meta?.hookDurationSec ?? 2.2)));
  const hookDurationInFrames = Math.min(
    durationInFrames - 1,
    Math.max(1, Math.round(hookDurationSec * fps)),
  );
  const hookTextRaw = preparedSpec?.meta?.hookText?.trim();
  const hookText = hookTextRaw || beats[0]?.text || "Your search is missing answers.";

  return (
    <AbsoluteFill style={{backgroundColor: tokens.colors.background}}>
      {Array.from({length: audioLayerCount}).map((_, idx) => (
        <Audio
          key={`bed-${idx}`}
          src={assets.bed}
          loop
          volume={audioBedVolume}
          playbackRate={1 - idx * 0.02}
        />
      ))}
      {voiceoverSrc ? <Audio src={voiceoverSrc} startFrom={Math.round(voiceoverStart * fps)} /> : null}

      <TransitionSeries>
        {beats
          .map((beat, index) => (
            <TransitionSeries.Sequence
              key={beat.id}
              durationInFrames={beat.durationInFrames + (index > 0 ? transitionFrames[index - 1] : 0)}
            >
              <BeatScene beat={beat} layout={layout} />
            </TransitionSeries.Sequence>
          ))
          .flatMap((sceneEl, index, arr) => {
            if (index === arr.length - 1) {
              return [sceneEl];
            }

            const beat = beats[index];
            const timingFrames = transitionFrames[index];
            const transitionType = constrainTransitionType(beat.transitionType);

            return [
              sceneEl,
              <TransitionSeries.Transition
                key={`transition-${beats[index].id}`}
                timing={linearTiming({durationInFrames: timingFrames})}
                presentation={
                  transitionType === "slide"
                    ? slide({direction: index % 2 === 0 ? "from-right" : "from-left"})
                    : fade({shouldFadeOutExitingScene: true})
                }
              />,
            ];
          })}
      </TransitionSeries>

      {beatCutEnabled ? (
        <BeatCut
          beatsInFrames={beatCutFrames}
          flashDurationFrames={
            beatCutCfg?.flashDurationFrames ?? quality?.beatCut?.flashDurationFrames ?? 2
          }
          flashOpacity={beatCutCfg?.flashOpacity ?? quality?.beatCut?.flashOpacity ?? 0.08}
          shake={{enabled: true, amp: quality?.beatCut?.shakeAmp ?? 2.4}}
        />
      ) : null}

      {hookEnabled ? <HookIntro text={hookText} durationInFrames={hookDurationInFrames} /> : null}
    </AbsoluteFill>
  );
};
