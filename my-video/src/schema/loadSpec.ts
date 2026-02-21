import fs from "node:fs";
import path from "node:path";
import {parseVideoSpec, VideoSpec} from "./spec";

export const loadSpec = (specOrPath: VideoSpec | string, cwd = process.cwd()): VideoSpec => {
  if (typeof specOrPath !== "string") {
    return parseVideoSpec(specOrPath);
  }

  const absolute = path.isAbsolute(specOrPath)
    ? specOrPath
    : path.join(cwd, specOrPath);
  const raw = fs.readFileSync(absolute, "utf8");
  return parseVideoSpec(JSON.parse(raw));
};
