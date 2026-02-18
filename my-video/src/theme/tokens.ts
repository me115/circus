import {ThemeTokens} from "./types";
import {motionkit, stylekit} from "../style";

export const shadowToCss = ({
  x,
  y,
  blur,
  spread,
  color,
}: {
  x: number;
  y: number;
  blur: number;
  spread: number;
  color: string;
}) => `${x}px ${y}px ${blur}px ${spread}px ${color}`;

const parseShadow = (raw: string, fallback: {x: number; y: number; blur: number; spread: number; color: string}) => {
  const parts = (raw || "").trim().split(/\s+/);
  if (parts.length < 5) {
    return fallback;
  }

  const nums = parts.slice(0, 4).map((p) => Number.parseFloat(p.replace("px", "")));
  if (nums.some((n) => !Number.isFinite(n))) {
    return fallback;
  }

  return {
    x: nums[0],
    y: nums[1],
    blur: nums[2],
    spread: nums[3],
    color: parts.slice(4).join(" "),
  };
};

export const tokens: ThemeTokens = {
  colors: {
    background: stylekit.palette.bg1,
    base: stylekit.palette.bg2,
    primary: stylekit.palette.primary,
    secondary: stylekit.palette.accent,
    textMuted: stylekit.palette.muted,
    accent: stylekit.palette.accent,
  },
  radii: {
    sm: 10,
    md: 16,
    lg: stylekit.radii.media,
    xl: stylekit.radii.card,
  },
  shadows: {
    card: parseShadow(stylekit.shadows.card, {
      x: 0,
      y: 20,
      blur: 50,
      spread: -24,
      color: "rgba(17, 28, 55, 0.55)",
    }),
    soft: parseShadow(stylekit.shadows.soft, {
      x: 0,
      y: 8,
      blur: 26,
      spread: -14,
      color: "rgba(8, 16, 31, 0.4)",
    }),
  },
  typography: {
    fontFamilySans: stylekit.typography.fontFamily,
    fontWeightBold: 800,
    lineHeight: stylekit.typography.lineHeight,
    sizes: {
      hero: stylekit.typography.hero,
      title: stylekit.typography.title,
      body: stylekit.typography.body,
      caption: stylekit.typography.caption,
    },
  },
  spacing: {
    xs: 8,
    sm: 12,
    md: 20,
    lg: 32,
    xl: 64,
  },
  motion: {
    defaultSpring: {
      damping: motionkit.recipes.entrance.damping,
      mass: 0.85,
      stiffness: motionkit.recipes.entrance.stiffness,
    },
    emphasisScalePeak: motionkit.recipes.emphasis.scalePeak,
    emphasisFrames: motionkit.recipes.emphasis.frames,
    inDurationFrames: motionkit.recipes.entrance.frames,
    outDurationFrames: 12,
    transitionDurationFrames: motionkit.recipes.transition.durationFrames,
    allowedTransitions: motionkit.recipes.transition.types,
  },
};
