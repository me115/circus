import type {CSSProperties} from "react";
import {tokens} from "../theme/tokens";

export type SafeAreaBounds = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export const getSafeAreaBounds = (
  width: number,
  height: number,
  safePadding = tokens.spacing.xl,
): SafeAreaBounds => {
  return {
    x: safePadding,
    y: safePadding,
    width: Math.max(0, width - safePadding * 2),
    height: Math.max(0, height - safePadding * 2),
  };
};

export const getContentMaxWidth = (width: number, ratio = 0.8): number => {
  return Math.floor(width * ratio);
};

export const centerWithin = (bounds: SafeAreaBounds): CSSProperties => {
  return {
    left: bounds.x,
    top: bounds.y,
    width: bounds.width,
    height: bounds.height,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };
};
