export type StyleKit = {
  palette: {
    bg1: string;
    bg2: string;
    primary: string;
    accent: string;
    text: string;
    muted: string;
  };
  typography: {
    fontFamily: string;
    hero: number;
    title: number;
    body: number;
    caption: number;
    lineHeight: number;
  };
  radii: {
    card: number;
    media: number;
  };
  shadows: {
    card: string;
    soft: string;
  };
  safeArea: {
    leftPct: number;
    rightPct: number;
    topPct: number;
    bottomPct: number;
  };
};

export type MotionKit = {
  recipes: {
    entrance: {
      type: "spring";
      damping: number;
      stiffness: number;
      yFrom: number;
      yTo: number;
      scaleFrom: number;
      scaleTo: number;
      frames: number;
    };
    emphasis: {
      type: "pulse";
      scalePeak: number;
      frames: number;
    };
    transition: {
      types: Array<"fade" | "slide">;
      default: "fade" | "slide";
      durationFrames: number;
    };
  };
  limits: {
    maxTransitionTypes: number;
    maxMotionRecipes: number;
  };
};

export type CookbookIntentRecipe = {
  durationSec: number;
  layers: string[];
  backdrop?: {
    preset?: "gemini" | "dark" | "light";
    animate?: boolean;
    intensity?: number;
  };
  constraints?: {
    maxWords?: number;
    maxBullets?: number;
    maxWordsPerBullet?: number;
    maxWordsPerStep?: number;
    maxWordsPerLine?: number;
    maxLines?: number;
  };
};

export type Cookbook = {
  intents: Record<string, CookbookIntentRecipe>;
};
