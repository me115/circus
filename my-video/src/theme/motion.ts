import {interpolate, spring} from "remotion";
import {tokens} from "./tokens";
import {SpringLikeConfig} from "./types";

export const springIn = (
  frame: number,
  fps: number,
  delayFrames = 0,
  config: SpringLikeConfig = tokens.motion.defaultSpring,
): number => {
  return spring({
    fps,
    frame: Math.max(0, frame - delayFrames),
    config,
  });
};

export const fadeInOut = (frame: number, start: number, end: number): number => {
  if (end <= start) {
    return frame >= start ? 1 : 0;
  }

  const fadeDuration = Math.max(1, Math.min(12, Math.floor((end - start) / 2)));

  return interpolate(
    frame,
    [start, start + fadeDuration, end - fadeDuration, end],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
};

export const slideY = (
  frame: number,
  start: number,
  end: number,
  from: number,
  to: number,
): number => {
  if (end <= start) {
    return to;
  }

  return interpolate(frame, [start, end], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};
