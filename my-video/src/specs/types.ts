export type TimelineBeat = {
  id: string;
  t0: number;
  t1: number;
  intent: string;
  text: string;
  renderMode?: string;
  transitionType?: string;
  motionRecipe?: string;
};

export type LayoutConfig = {
  safePadding?: number;
  mediaPadXPct?: number;
  mediaPadYPct?: number;
  kineticYPct?: number;
  lowerThirdYPct?: number;
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
    fps?: number;
    width?: number;
    height?: number;
    durationSec?: number;
    title?: string;
    subtitle?: string;
    tagline?: string;
    audioBedVolume?: number;
    audioLayerCount?: number;
  };
  generation?: {
    beatTargetSec?: number;
    splitStrategy?: string;
  };
  layout?: LayoutConfig;
  beats?: TimelineBeat[];
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
