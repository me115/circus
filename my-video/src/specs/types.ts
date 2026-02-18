export type BackdropConfig = {
  preset?: "gemini" | "dark" | "light";
  animate?: boolean;
  intensity?: number;
};

export type SceneLayer = {
  type:
    | "HeroTitle"
    | "MediaFrame"
    | "LowerThird"
    | "KineticWords"
    | "PromptAnswerCard"
    | "LogoOutro"
    | "BeforeAfter"
    | "Stepper3"
    | "Callout";
  props?: Record<string, unknown>;
};

export type BeatScene = {
  backdrop?: BackdropConfig;
  layers?: SceneLayer[];
};

export type TimelineBeat = {
  id: string;
  t0: number;
  t1: number;
  intent: string;
  text?: string;
  line?: string;
  renderMode?: string;
  render_mode?: string;
  transitionType?: string;
  transition_type?: string;
  motionRecipe?: string;
  motion_recipe?: string;
  scene?: BeatScene;
};

export type LayoutConfig = {
  safePadding?: number;
  mediaPadXPct?: number;
  mediaPadYPct?: number;
  kineticYPct?: number;
  lowerThirdYPct?: number;
  lowerThirdMaxWidthPct?: number;
  cardYPct?: number;
  cardWidthPct?: number;
  cardHeightPct?: number;
  heroMaxWidthPct?: number;
  heroYPct?: number;
  heroHeightPct?: number;
};

export type SkillTimelineSpec = {
  meta?: {
    compositionId?: string;
    composition_id?: string;
    stylePreset?: string;
    style_preset?: string;
    fps?: number;
    width?: number;
    height?: number;
    durationSec?: number;
    duration_sec?: number;
    title?: string;
    subtitle?: string;
    tagline?: string;
    audioBedVolume?: number;
    audioLayerCount?: number;
    hookEnabled?: boolean;
    hookDurationSec?: number;
    hookText?: string;
  };
  audio?: {
    src?: string;
    startSec?: number;
  };
  generation?: {
    beatTargetSec?: number;
    splitStrategy?: string;
  };
  layout?: LayoutConfig;
  beats?: TimelineBeat[];
  global_overlays?: {
    beatcut?: {
      enabled?: boolean;
      beatsInFrames?: number[];
      flashOpacity?: number;
      flashDurationFrames?: number;
    };
  };
};

export type QualityConfig = {
  targetScore?: number;
  beatCut?: {
    flashOpacity?: number;
    flashDurationFrames?: number;
    shakeAmp?: number;
    intervalFrames?: number;
  };
  layout?: LayoutConfig;
};
