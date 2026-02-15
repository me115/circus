import {TransitionSeries, linearTiming} from "@remotion/transitions";
import {fade} from "@remotion/transitions/fade";
import {slide} from "@remotion/transitions/slide";
import {AbsoluteFill, Audio, useVideoConfig} from "remotion";
import {BeatCut} from "../components/BeatCut";
import {BrandBackdrop} from "../components/BrandBackdrop";
import {HeroTitle} from "../components/HeroTitle";
import {KineticWords} from "../components/KineticWords";
import {MediaFrame} from "../components/MediaFrame";
import {PromptAnswerCard} from "../components/PromptAnswerCard";
import {tokens} from "../theme/tokens";
import {assets} from "../utils/assets";
import {LayoutConfig, QualityConfig, SkillTimelineSpec, TimelineBeat} from "../specs/types";

type SkillExplainer60Props = {
  spec?: SkillTimelineSpec;
  quality?: QualityConfig;
};

type NormalizedBeat = TimelineBeat & {
  renderMode: string;
  transitionType: string;
  motionRecipe: string;
  startFrame: number;
  durationInFrames: number;
};

const DEFAULT_LAYOUT: Required<LayoutConfig> = {
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

const pickRenderMode = (beat: TimelineBeat): string => {
  if (beat.renderMode) {
    return beat.renderMode;
  }

  const intent = `${beat.intent ?? ""}`.toLowerCase();
  if (intent.includes("hook")) return "hero";
  if (intent.includes("outro")) return "outro";
  if (intent.includes("proof")) return "promptCard";
  if (intent.includes("process")) return "media";
  if (intent.includes("cta")) return "lowerThird";
  return "kinetic";
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
      },
    ];
  }

  let cursor = 0;

  const normalized = beats.map((beat, index) => {
    const declaredDuration = Math.max(0.6, (beat.t1 ?? 0) - (beat.t0 ?? 0));
    const fromSpec = Math.max(18, Math.round(declaredDuration * fps));
    const remaining = durationInFrames - cursor;
    const isLast = index === beats.length - 1;
    const duration = isLast ? Math.max(18, remaining) : Math.max(18, Math.min(fromSpec, remaining));

    const normalizedBeat: NormalizedBeat = {
      ...beat,
      renderMode: pickRenderMode(beat),
      transitionType: beat.transitionType ?? "fade",
      motionRecipe: beat.motionRecipe ?? "spring",
      startFrame: cursor,
      durationInFrames: duration,
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
    });
  }

  return normalized;
};

const renderWords = (text: string): string[] => {
  return text
    .split(/\s+/)
    .map((w) => w.trim())
    .filter((w) => w.length > 0);
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

const BeatScene = ({
  beat,
  index,
  layout,
}: {
  beat: NormalizedBeat;
  index: number;
  layout: Required<LayoutConfig>;
}) => {
  const {width, height} = useVideoConfig();
  const padX = Math.round(width * layout.mediaPadXPct);
  const padY = Math.round(height * layout.mediaPadYPct);
  const words = renderWords(beat.text);
  const kineticMode = getKineticMode(beat.motionRecipe);
  const promptAppearMode = getPromptAppearMode(beat.motionRecipe);
  const kenBurns = getKenBurnsByRecipe(beat.motionRecipe, index);

  const mediaSrc = index % 2 === 0 ? assets.demoImage1 : assets.demoImage2;

  const media = (
    <AbsoluteFill style={{padding: `${padY}px ${padX}px`}}>
      <MediaFrame
        kind="image"
        src={mediaSrc}
        startFrame={0}
        durationInFrames={Math.max(12, beat.durationInFrames - 2)}
        kenBurns={kenBurns}
      />
    </AbsoluteFill>
  );

  if (beat.renderMode === "hero") {
    return (
      <AbsoluteFill>
        {media}
        <div
          style={{
            position: "absolute",
            left: Math.round(width * (1 - layout.heroMaxWidthPct) * 0.5),
            top: Math.round(height * layout.heroYPct),
            width: Math.round(width * layout.heroMaxWidthPct),
            height: Math.round(height * layout.heroHeightPct),
          }}
        >
          <HeroTitle title={beat.text} subtitle="Objective metrics first." enterDelayFrames={4} />
        </div>
      </AbsoluteFill>
    );
  }

  if (beat.renderMode === "promptCard") {
    return (
      <AbsoluteFill>
        {media}
        <div
          style={{
            position: "absolute",
            left: Math.round((1 - layout.cardWidthPct) * width * 0.5),
            top: Math.round(height * layout.cardYPct),
            width: Math.round(width * layout.cardWidthPct),
            height: Math.round(height * layout.cardHeightPct),
            display: "flex",
            alignItems: "center",
          }}
        >
          <PromptAnswerCard
            prompt={beat.text}
            answer="The loop evaluates objectively, applies spec patches, then rerenders for visible improvement."
            startFrame={3}
            appearMode={promptAppearMode}
            showCursor
            typing={{enabled: true, cps: 30}}
          />
        </div>
      </AbsoluteFill>
    );
  }

  if (beat.renderMode === "lowerThird") {
    return (
      <AbsoluteFill>
        {media}
        <div
          style={{
            position: "absolute",
            left: Math.round(width * 0.1),
            right: Math.round(width * 0.1),
            top: Math.round(height * layout.lowerThirdYPct),
          }}
        >
          <div
            style={{
              fontFamily: tokens.typography.fontFamilySans,
              fontSize: tokens.typography.sizes.body,
              color: "#eef4ff",
              fontWeight: 700,
              lineHeight: 1.25,
              textShadow: "0 6px 30px rgba(5,10,22,0.55)",
            }}
          >
            {beat.text}
          </div>
        </div>
      </AbsoluteFill>
    );
  }

  if (beat.renderMode === "outro") {
    return (
      <AbsoluteFill>
        {media}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: Math.round(height * 0.24),
            display: "grid",
            placeItems: "center",
          }}
        >
          <HeroTitle
            title={beat.text}
            subtitle="Measured quality, stable motion, no blank sections."
            enterDelayFrames={2}
          />
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill>
      {media}
      <div
        style={{
          position: "absolute",
          left: Math.round(width * 0.1),
          right: Math.round(width * 0.1),
          top: Math.round(height * layout.kineticYPct),
          fontSize: tokens.typography.sizes.body,
        }}
      >
        <KineticWords
          words={words}
          startFrame={4}
          wordStagger={6}
          mode={beat.renderMode === "media" ? "slide" : kineticMode}
          emphasize={[0, Math.max(0, words.length - 1)]}
        />
      </div>
    </AbsoluteFill>
  );
};

export const SkillExplainer60 = ({spec, quality}: SkillExplainer60Props) => {
  const {fps, durationInFrames} = useVideoConfig();

  const layout: Required<LayoutConfig> = {
    ...DEFAULT_LAYOUT,
    ...(quality?.layout ?? {}),
    ...(spec?.layout ?? {}),
  };

  const beats = normalizeBeats(spec, fps, durationInFrames);
  const beatsInFrames = beats.map((beat) => beat.startFrame);
  const audioBedVolume = spec?.meta?.audioBedVolume ?? 0.08;
  const audioLayerCount = Math.max(1, Math.min(4, Math.floor(spec?.meta?.audioLayerCount ?? 1)));

  return (
    <AbsoluteFill style={{backgroundColor: tokens.colors.background}}>
      <BrandBackdrop preset="gemini" intensity={0.95} animate safePadding={layout.safePadding} />

      {Array.from({length: audioLayerCount}).map((_, idx) => (
        <Audio
          key={`bed-${idx}`}
          src={assets.bed}
          loop
          volume={audioBedVolume}
          playbackRate={1 - idx * 0.02}
        />
      ))}
      <Audio src={assets.chime} volume={0.18} />

      <TransitionSeries>
        {beats
          .map((beat, index) => (
            <TransitionSeries.Sequence key={beat.id} durationInFrames={beat.durationInFrames}>
              <BeatScene beat={beat} index={index} layout={layout} />
            </TransitionSeries.Sequence>
          ))
          .flatMap((sceneEl, index, arr) => {
            if (index === arr.length - 1) {
              return [sceneEl];
            }

            const beat = beats[index];
            const timingFrames = Math.max(12, Math.min(20, Math.floor(beat.durationInFrames * 0.18)));

            return [
              sceneEl,
              <TransitionSeries.Transition
                key={`transition-${beats[index].id}`}
                timing={linearTiming({durationInFrames: timingFrames})}
                presentation={
                  beat.transitionType === "slide"
                    ? slide({direction: index % 2 === 0 ? "from-right" : "from-left"})
                    : fade({shouldFadeOutExitingScene: true})
                }
              />,
            ];
          })}
      </TransitionSeries>

      <BeatCut
        beatsInFrames={beatsInFrames}
        flashDurationFrames={quality?.beatCut?.flashDurationFrames ?? 2}
        flashOpacity={quality?.beatCut?.flashOpacity ?? 0.08}
        shake={{enabled: true, amp: quality?.beatCut?.shakeAmp ?? 2.4}}
      />
    </AbsoluteFill>
  );
};
