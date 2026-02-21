import {interpolate, spring} from "remotion";

export const ENTER_FRAMES = 12;
export const EXIT_FRAMES = 10;
export const EMPH_FRAMES = 8;

export const enter = (frame: number): number => {
  return spring({
    frame,
    fps: 30,
    config: {
      damping: 18,
      stiffness: 120,
      mass: 0.6,
    },
  });
};

export const exit = (frame: number, durationFrames: number): number => {
  const start = Math.max(0, durationFrames - EXIT_FRAMES);
  if (frame < start) {
    return 1;
  }
  return interpolate(frame, [start, durationFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

export const emphasize = (frame: number, t0: number, t1: number): number => {
  if (frame < t0 || frame > t1) {
    return 1;
  }
  const mid = (t0 + t1) / 2;
  return interpolate(frame, [t0, mid, t1], [1, 1.04, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};
