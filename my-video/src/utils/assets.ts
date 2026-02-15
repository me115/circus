import {staticFile} from "remotion";

export const assets = {
  logo: staticFile("logo.png"),
  chime: staticFile("chime.wav"),
  demoImage1: staticFile("demo/img1.png"),
  demoImage2: staticFile("demo/img2.png"),
  demoBroll: staticFile("demo/broll.mp4"),
};

export const withFallbackAsset = (
  src: string | undefined,
  fallback: string,
): string => {
  if (!src || src.trim().length === 0) {
    return fallback;
  }

  return src;
};
