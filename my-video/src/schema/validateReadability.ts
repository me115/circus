import {VideoSpec} from "./spec";
import {wrapText} from "../utils/wrapText";

export type ReadabilityWarning = {
  beatId: string;
  text: string;
  reason: string;
};

type ValidateOptions = {
  maxCharsPerLine?: number;
  maxLines?: number;
};

const collectBeatTexts = (spec: VideoSpec): Array<{beatId: string; text: string}> => {
  const rows: Array<{beatId: string; text: string}> = [];
  spec.beats.forEach((beat) => {
    (beat.onScreen ?? []).forEach((line) => {
      rows.push({
        beatId: beat.id,
        text: line,
      });
    });
    beat.steps.forEach((step) => {
      rows.push({
        beatId: beat.id,
        text: step.label,
      });
      step.nodes.forEach((node) => {
        rows.push({
          beatId: beat.id,
          text: node.text,
        });
      });
    });
  });
  return rows;
};

export const validateSpecForReadability = (
  spec: VideoSpec,
  options?: ValidateOptions,
): ReadabilityWarning[] => {
  const maxCharsPerLine = options?.maxCharsPerLine ?? (spec.meta.aspect === "9:16" ? 14 : 26);
  const maxLines = options?.maxLines ?? 2;
  const warnings: ReadabilityWarning[] = [];

  collectBeatTexts(spec).forEach((item) => {
    if (!item.text.trim()) {
      return;
    }
    const wrapped = wrapText(item.text, {maxCharsPerLine, maxLines});
    if (wrapped.overflow) {
      warnings.push({
        beatId: item.beatId,
        text: item.text,
        reason: `Text overflow (>${maxLines} lines at ${maxCharsPerLine} chars/line)`,
      });
    }
  });

  return warnings;
};
