import {interpolate, spring} from "remotion";
import {tokens} from "./tokens";
import {SpringLikeConfig} from "./types";
import {motionkit} from "../style";

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

export const entranceStyle = (
  frame: number,
  fps: number,
  delayFrames = 0,
): {opacity: number; y: number; scale: number} => {
  const entrance = spring({
    fps,
    frame: Math.max(0, frame - delayFrames),
    config: {
      damping: motionkit.recipes.entrance.damping,
      stiffness: motionkit.recipes.entrance.stiffness,
      mass: 0.85,
    },
  });
  return {
    opacity: interpolate(entrance, [0, 1], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
    y: interpolate(
      entrance,
      [0, 1],
      [motionkit.recipes.entrance.yFrom, motionkit.recipes.entrance.yTo],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      },
    ),
    scale: interpolate(
      entrance,
      [0, 1],
      [motionkit.recipes.entrance.scaleFrom, motionkit.recipes.entrance.scaleTo],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      },
    ),
  };
};

export const emphasisPulseScale = (frame: number, startFrame: number): number => {
  const endFrame = startFrame + motionkit.recipes.emphasis.frames;
  return interpolate(
    frame,
    [startFrame, startFrame + motionkit.recipes.emphasis.frames * 0.5, endFrame],
    [1, motionkit.recipes.emphasis.scalePeak, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
};

export const constrainTransitionType = (transitionType: string): "fade" | "slide" => {
  const allowed = new Set(motionkit.recipes.transition.types);
  return allowed.has(transitionType as "fade" | "slide")
    ? (transitionType as "fade" | "slide")
    : motionkit.recipes.transition.default;
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
