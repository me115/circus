import {ThemeTokens} from "./types";

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

export const tokens: ThemeTokens = {
  colors: {
    background: "#05070e",
    base: "#0b1224",
    primary: "#73b4ff",
    secondary: "#44e6d8",
    textMuted: "#a6b1cc",
    accent: "#ffd978",
  },
  radii: {
    sm: 10,
    md: 16,
    lg: 24,
    xl: 36,
  },
  shadows: {
    card: {
      x: 0,
      y: 20,
      blur: 50,
      spread: -24,
      color: "rgba(17, 28, 55, 0.55)",
    },
    soft: {
      x: 0,
      y: 8,
      blur: 26,
      spread: -14,
      color: "rgba(8, 16, 31, 0.4)",
    },
  },
  typography: {
    fontFamilySans: "'Manrope', 'Avenir Next', 'Segoe UI', sans-serif",
    fontWeightBold: 800,
    sizes: {
      hero: 110,
      title: 54,
      body: 30,
      caption: 20,
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
      damping: 14,
      mass: 0.85,
      stiffness: 160,
    },
    inDurationFrames: 18,
    outDurationFrames: 12,
  },
};
