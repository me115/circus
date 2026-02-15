import {interpolate} from "remotion";

export const secondsToFrames = (seconds: number, fps: number): number => {
  return Math.round(seconds * fps);
};

export const framesToSeconds = (frames: number, fps: number): number => {
  return frames / fps;
};

export const staggerFrame = (
  startFrame: number,
  index: number,
  stepFrames: number,
): number => {
  return startFrame + index * stepFrames;
};

export const createBeatGrid = (
  startFrame: number,
  endFrame: number,
  intervalFrames: number,
): number[] => {
  const beats: number[] = [];

  for (let f = startFrame; f <= endFrame; f += intervalFrames) {
    beats.push(f);
  }

  return beats;
};

export const flashOpacityAtFrame = (
  frame: number,
  beatsInFrames: number[],
  flashDurationFrames: number,
  flashOpacity: number,
): number => {
  return beatsInFrames.reduce((maxOpacity, beat) => {
    const dist = Math.abs(frame - beat);
    if (dist >= flashDurationFrames) {
      return maxOpacity;
    }

    const currentOpacity = interpolate(
      dist,
      [0, flashDurationFrames],
      [flashOpacity, 0],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      },
    );

    return Math.max(maxOpacity, currentOpacity);
  }, 0);
};
