import {SkillTimelineSpec, TimelineBeat} from "../specs/types";

type NormalizeOptions = {
  minBeatSec?: number;
  maxBeatSec?: number;
  targetBeatSec?: number;
  maxWordsPerLine?: number;
  maxLines?: number;
};

type NormalizeResult = {
  spec: SkillTimelineSpec;
  changes: string[];
};

const clone = <T>(input: T): T => JSON.parse(JSON.stringify(input)) as T;

const asText = (beat: TimelineBeat): string => {
  return `${beat.line ?? beat.text ?? ""}`.trim();
};

const normalizeLineByWords = (
  line: string,
  maxWordsPerLine: number,
  maxLines: number,
): string => {
  const words = line.split(/\s+/).filter(Boolean);
  const maxWords = Math.max(1, maxWordsPerLine * maxLines);
  if (words.length <= maxWords) {
    return words.join(" ");
  }
  return `${words.slice(0, maxWords).join(" ").replace(/[.,;:!?]+$/, "")}.`;
};

const splitText = (line: string, segments: number): string[] => {
  const normalized = line.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return Array.from({length: segments}).map(() => "");
  }

  const bySentence = normalized.split(/(?<=[.!?])\s+/).filter(Boolean);
  if (bySentence.length >= segments) {
    return bySentence.slice(0, segments);
  }

  const words = normalized.split(" ");
  const bucketSize = Math.max(1, Math.ceil(words.length / segments));
  const result: string[] = [];
  for (let i = 0; i < segments; i++) {
    result.push(words.slice(i * bucketSize, (i + 1) * bucketSize).join(" ").trim());
  }
  return result.map((item) => item || normalized);
};

const ensureHook = (beats: TimelineBeat[], changes: string[]): TimelineBeat[] => {
  const hasHook = beats.some((beat) => `${beat.intent}`.toLowerCase() === "hook_title");
  if (hasHook) {
    return beats;
  }

  const hookText = asText(beats[0] ?? ({} as TimelineBeat)) || "Search by meaning, not just keywords.";
  const hookBeat: TimelineBeat = {
    id: "hook_auto",
    t0: 0,
    t1: 4,
    intent: "hook_title",
    line: normalizeLineByWords(hookText, 7, 2),
  };
  changes.push("insert_hook_title");
  return [hookBeat, ...beats];
};

const ensureExample = (beats: TimelineBeat[], changes: string[]): TimelineBeat[] => {
  const hasExample = beats.some((beat) => `${beat.intent}`.toLowerCase() === "example_prompt");
  if (hasExample) {
    return beats;
  }

  changes.push("insert_example_prompt");
  const beat: TimelineBeat = {
    id: "example_auto",
    t0: 44,
    t1: 48,
    intent: "example_prompt",
    line: "Ask a real question and retrieve relevant answers instantly.",
  };

  return [...beats, beat].sort((a, b) => a.t0 - b.t0);
};

const splitLongBeats = (
  beats: TimelineBeat[],
  maxBeatSec: number,
  targetBeatSec: number,
  changes: string[],
): TimelineBeat[] => {
  const output: TimelineBeat[] = [];
  for (const beat of beats) {
    const duration = Math.max(0.2, (beat.t1 ?? 0) - (beat.t0 ?? 0));
    if (duration <= maxBeatSec) {
      output.push(beat);
      continue;
    }
    const segments = Math.max(2, Math.round(duration / targetBeatSec));
    const segmentDuration = duration / segments;
    const textPieces = splitText(asText(beat), segments);
    for (let i = 0; i < segments; i++) {
      output.push({
        ...beat,
        id: `${beat.id}_s${i + 1}`,
        t0: beat.t0 + i * segmentDuration,
        t1: beat.t0 + (i + 1) * segmentDuration,
        line: textPieces[i] || asText(beat),
      });
    }
    changes.push(`split_${beat.id}`);
  }
  return output;
};

const mergeShortBeats = (
  beats: TimelineBeat[],
  minBeatSec: number,
  maxBeatSec: number,
  changes: string[],
): TimelineBeat[] => {
  if (beats.length <= 1) {
    return beats;
  }

  const result: TimelineBeat[] = [];
  let i = 0;
  while (i < beats.length) {
    const current = beats[i];
    const duration = Math.max(0.2, (current.t1 ?? 0) - (current.t0 ?? 0));
    if (duration >= minBeatSec || i === beats.length - 1) {
      result.push(current);
      i += 1;
      continue;
    }

    const next = beats[i + 1];
    const mergedDuration = Math.max(0.2, (next.t1 ?? next.t0) - (current.t0 ?? current.t1));
    if (mergedDuration > maxBeatSec + 0.8) {
      result.push(current);
      i += 1;
      continue;
    }
    result.push({
      ...current,
      id: `${current.id}_m`,
      t0: current.t0,
      t1: next.t1,
      intent: current.intent || next.intent,
      line: `${asText(current)} ${asText(next)}`.trim(),
    });
    changes.push(`merge_${current.id}_${next.id}`);
    i += 2;
  }

  return result;
};

const resequenceBeats = (
  beats: TimelineBeat[],
  durationSec: number,
  targetBeatSec: number,
): TimelineBeat[] => {
  const sorted = [...beats].sort((a, b) => a.t0 - b.t0);
  let cursor = 0;
  const out: TimelineBeat[] = [];
  for (let i = 0; i < sorted.length; i++) {
    const beat = sorted[i];
    const isLast = i === sorted.length - 1;
    const original = Math.max(2.2, (beat.t1 ?? beat.t0) - (beat.t0 ?? 0));
    const dur = isLast ? Math.max(2.5, durationSec - cursor) : Math.max(2.5, Math.min(4.0, original || targetBeatSec));
    out.push({
      ...beat,
      t0: Number(cursor.toFixed(3)),
      t1: Number((cursor + dur).toFixed(3)),
      line: beat.line ?? beat.text ?? "",
      text: beat.text ?? beat.line ?? "",
    });
    cursor += dur;
  }

  if (out.length > 0) {
    out[out.length - 1].t1 = Number(durationSec.toFixed(3));
  }
  return out;
};

export const normalizeStoryboard = (
  inputSpec: SkillTimelineSpec,
  options?: NormalizeOptions,
): NormalizeResult => {
  const spec = clone(inputSpec ?? {});
  const minBeatSec = options?.minBeatSec ?? 2.5;
  const maxBeatSec = options?.maxBeatSec ?? 4.0;
  const targetBeatSec = options?.targetBeatSec ?? 3.0;
  const maxWordsPerLine = options?.maxWordsPerLine ?? 7;
  const maxLines = options?.maxLines ?? 2;
  const changes: string[] = [];

  const beatsRaw = Array.isArray(spec.beats) ? spec.beats : [];
  let beats: TimelineBeat[] = beatsRaw
    .map((beat, idx) => ({
      ...beat,
      id: beat.id || `b${String(idx + 1).padStart(2, "0")}`,
      line: asText(beat),
    }))
    .sort((a, b) => a.t0 - b.t0);

  beats = ensureHook(beats, changes);
  beats = ensureExample(beats, changes);
  beats = splitLongBeats(beats, maxBeatSec, targetBeatSec, changes);
  beats = mergeShortBeats(beats, minBeatSec, maxBeatSec, changes);

  const durationSec = Number(
    (spec.meta?.duration_sec ??
      spec.meta?.durationSec ??
      Math.max(...beats.map((beat) => beat.t1), 60)) || 60,
  );

  beats = resequenceBeats(beats, durationSec, targetBeatSec).map((beat) => ({
    ...beat,
    line: normalizeLineByWords(asText(beat), maxWordsPerLine, maxLines),
    text: normalizeLineByWords(asText(beat), maxWordsPerLine, maxLines),
  }));

  spec.beats = beats;
  if (!spec.meta) {
    spec.meta = {};
  }
  spec.meta.durationSec = durationSec;
  spec.meta.duration_sec = durationSec;

  return {spec, changes};
};
