export type StylePreset = "gemini" | "dark" | "light";

export type Shadow = {
  x: number;
  y: number;
  blur: number;
  spread: number;
  color: string;
};

export type ColorTokens = {
  background: string;
  base: string;
  primary: string;
  secondary: string;
  textMuted: string;
  accent: string;
};

export type RadiiTokens = {
  sm: number;
  md: number;
  lg: number;
  xl: number;
};

export type ShadowTokens = {
  card: Shadow;
  soft: Shadow;
};

export type TypographyTokens = {
  fontFamilySans: string;
  fontWeightBold: number;
  lineHeight: number;
  sizes: {
    hero: number;
    title: number;
    body: number;
    caption: number;
  };
};

export type SpacingTokens = {
  xs: number;
  sm: number;
  md: number;
  lg: number;
  xl: number;
};

export type SpringLikeConfig = {
  damping: number;
  mass: number;
  stiffness: number;
};

export type MotionTokens = {
  defaultSpring: SpringLikeConfig;
  emphasisScalePeak: number;
  emphasisFrames: number;
  inDurationFrames: number;
  outDurationFrames: number;
  transitionDurationFrames: number;
  allowedTransitions: Array<"fade" | "slide">;
};

export type ThemeTokens = {
  colors: ColorTokens;
  radii: RadiiTokens;
  shadows: ShadowTokens;
  typography: TypographyTokens;
  spacing: SpacingTokens;
  motion: MotionTokens;
};
