import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {flashOpacityAtFrame} from "../utils/beat";

type BeatCutProps = {
  beatsInFrames: number[];
  flashDurationFrames?: number;
  flashOpacity?: number;
  shake?: {
    enabled: boolean;
    amp: number;
  };
};

export const BeatCut = ({
  beatsInFrames,
  flashDurationFrames = 3,
  flashOpacity = 0.25,
  shake = {enabled: true, amp: 4},
}: BeatCutProps) => {
  const frame = useCurrentFrame();
  const flash = flashOpacityAtFrame(
    frame,
    beatsInFrames,
    flashDurationFrames,
    flashOpacity,
  );

  let shakeX = 0;
  let shakeY = 0;

  if (shake.enabled) {
    const shakeWindow = 8;
    for (const beat of beatsInFrames) {
      const delta = frame - beat;
      if (delta < 0 || delta > shakeWindow) {
        continue;
      }

      const decay = interpolate(delta, [0, shakeWindow], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      shakeX += Math.sin(delta * 2.2 + beat * 0.13) * shake.amp * decay;
      shakeY += Math.cos(delta * 2.8 + beat * 0.11) * shake.amp * 0.75 * decay;
    }
  }

  const shakeStrength = Math.min(1, Math.abs(shakeX) / 8 + Math.abs(shakeY) / 8);

  return (
    <AbsoluteFill style={{pointerEvents: "none"}}>
      <AbsoluteFill
        style={{
          backgroundColor: "#ffffff",
          opacity: flash,
        }}
      />
      <AbsoluteFill
        style={{
          opacity: shakeStrength * 0.14,
          transform: `translate(${shakeX}px, ${shakeY}px)`,
          border: "1px solid rgba(255,255,255,0.45)",
          boxShadow: "inset 0 0 80px rgba(255, 255, 255, 0.18)",
        }}
      />
    </AbsoluteFill>
  );
};
