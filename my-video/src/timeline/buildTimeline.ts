import {VideoBeat, VideoMarker, VideoSpec} from "../schema/spec";

export type TimelineItem = {
  beat: VideoBeat;
  startSec: number;
  endSec: number;
  fromFrame: number;
  durationFrames: number;
};

export type BuiltTimeline = {
  items: TimelineItem[];
  totalFrames: number;
  totalDurationSec: number;
  fps: number;
};

const MIN_BEAT_SEC = 0.25;
const FALLBACK_BEAT_SEC = 3.0;

const clampDuration = (value: number): number => {
  return Number.isFinite(value) ? Math.max(MIN_BEAT_SEC, value) : MIN_BEAT_SEC;
};

const findMarkerForBeat = (
  beat: VideoBeat,
  index: number,
  markers: VideoMarker[],
): VideoMarker | null => {
  if (beat.markerId) {
    return markers.find((marker) => marker.id === beat.markerId) ?? null;
  }
  const byBeatId = markers.find((marker) => marker.beatId === beat.id);
  if (byBeatId) {
    return byBeatId;
  }
  return markers[index] ?? null;
};

const inferMarkerEnd = (
  marker: VideoMarker,
  markers: VideoMarker[],
  markerIndex: number,
  beat: VideoBeat,
): number => {
  if (typeof marker.endSec === "number") {
    return marker.endSec;
  }
  const next = markers[markerIndex + 1];
  if (next) {
    return next.startSec;
  }
  return marker.startSec + (beat.durationSec ?? FALLBACK_BEAT_SEC);
};

export const buildTimeline = (spec: VideoSpec): BuiltTimeline => {
  const fps = spec.meta.fps;
  const markers = spec.audio?.markers ?? [];
  const useMarkers = markers.length > 0;

  const items: TimelineItem[] = [];
  let cursorSec = 0;

  spec.beats.forEach((beat, index) => {
    let startSec = cursorSec;
    let endSec = cursorSec + (beat.durationSec ?? FALLBACK_BEAT_SEC);

    if (useMarkers) {
      const marker = findMarkerForBeat(beat, index, markers);
      if (marker) {
        const markerIndex = markers.findIndex((item) => item.id === marker.id);
        const inferredEnd = inferMarkerEnd(
          marker,
          markers,
          Math.max(0, markerIndex),
          beat,
        );
        startSec = Math.max(cursorSec, marker.startSec);
        endSec = Math.max(
          startSec + MIN_BEAT_SEC,
          inferredEnd,
        );
      } else {
        startSec = cursorSec;
        endSec = startSec + (beat.durationSec ?? FALLBACK_BEAT_SEC);
      }
    } else {
      startSec = cursorSec;
      endSec = startSec + (beat.durationSec ?? FALLBACK_BEAT_SEC);
    }

    const durationSec = clampDuration(endSec - startSec);
    const fromFrame = Math.round(startSec * fps);
    const durationFrames = Math.max(1, Math.round(durationSec * fps));

    items.push({
      beat,
      startSec,
      endSec: startSec + durationSec,
      fromFrame,
      durationFrames,
    });
    cursorSec = startSec + durationSec;
  });

  const totalFrames =
    items.length === 0
      ? 1
      : items[items.length - 1].fromFrame + items[items.length - 1].durationFrames;
  const totalDurationSec = totalFrames / fps;

  return {
    items,
    totalFrames,
    totalDurationSec,
    fps,
  };
};
