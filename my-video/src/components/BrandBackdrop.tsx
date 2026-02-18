import {useId, useMemo} from "react";
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {StylePreset} from "../theme/types";
import {stylekit} from "../style";

type BrandBackdropProps = {
  preset?: StylePreset;
  intensity?: number;
  animate?: boolean;
  safePadding?: number;
};

const presetGradients: Record<StylePreset, string[]> = {
  gemini: [
    `linear-gradient(135deg, ${stylekit.palette.bg1} 0%, ${stylekit.palette.bg2} 56%, #172243 100%)`,
    `radial-gradient(circle at 18% 20%, ${stylekit.palette.primary}66, transparent 48%)`,
    `radial-gradient(circle at 82% 28%, ${stylekit.palette.accent}55, transparent 50%)`,
  ],
  dark: [
    "linear-gradient(145deg, #02040a 0%, #0a1223 52%, #0d1d37 100%)",
    "radial-gradient(circle at 75% 22%, rgba(115, 180, 255, 0.26), transparent 44%)",
    "radial-gradient(circle at 26% 78%, rgba(68, 230, 216, 0.2), transparent 42%)",
  ],
  light: [
    "linear-gradient(140deg, #f2f7ff 0%, #d4e6fb 46%, #c8f0eb 100%)",
    "radial-gradient(circle at 72% 30%, rgba(115, 180, 255, 0.3), transparent 52%)",
    "radial-gradient(circle at 20% 72%, rgba(68, 230, 216, 0.2), transparent 50%)",
  ],
};

export const BrandBackdrop = ({
  preset = "gemini",
  intensity = 0.9,
  animate = true,
  safePadding = Math.round(stylekit.safeArea.leftPct * 1000),
}: BrandBackdropProps) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const reactId = useId();

  const turbulenceId = useMemo(() => {
    const safeId = reactId.replace(/[^a-zA-Z0-9_-]/g, "");
    return `noise-${safeId}`;
  }, [reactId]);

  const progress = animate ? frame : 0;
  const blobShiftX = interpolate(progress, [0, 300], [-28, 28], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const blobShiftY = interpolate(progress, [0, 300], [16, -20], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const baseFrequency = animate
    ? (0.68 + Math.sin(frame / 34) * 0.08) * 0.0032
    : 0.0028;

  const vignetteRadius = Math.max(50, 78 - safePadding * 0.05);

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        backgroundImage: presetGradients[preset].join(","),
      }}
    >
      <AbsoluteFill
        style={{
          opacity: 0.65 * intensity,
          mixBlendMode: preset === "light" ? "multiply" : "screen",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: width * 0.05 + blobShiftX,
            top: height * 0.12 + blobShiftY,
            width: width * 0.35,
            height: width * 0.35,
            borderRadius: 9999,
            filter: "blur(80px)",
            background: "radial-gradient(circle, rgba(115,180,255,0.9), transparent 70%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            right: width * 0.08 - blobShiftX * 0.7,
            bottom: height * 0.1 - blobShiftY * 0.55,
            width: width * 0.3,
            height: width * 0.3,
            borderRadius: 9999,
            filter: "blur(72px)",
            background: "radial-gradient(circle, rgba(68,230,216,0.8), transparent 72%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            right: width * 0.28,
            top: height * 0.42 + blobShiftY * 0.25,
            width: width * 0.2,
            height: width * 0.2,
            borderRadius: 9999,
            filter: "blur(64px)",
            background: "radial-gradient(circle, rgba(255,217,120,0.55), transparent 74%)",
          }}
        />
      </AbsoluteFill>

      <svg width="0" height="0" aria-hidden>
        <defs>
          <filter id={turbulenceId}>
            <feTurbulence
              type="fractalNoise"
              baseFrequency={baseFrequency}
              numOctaves={2}
              seed={animate ? 18 + (frame % 7) : 12}
            />
            <feColorMatrix
              type="matrix"
              values="0 0 0 0 0
                0 0 0 0 0
                0 0 0 0 0
                0 0 0 0.1 0"
            />
          </filter>
        </defs>
      </svg>

      <AbsoluteFill
        style={{
          pointerEvents: "none",
          opacity: 0.26 * intensity,
          backgroundColor: preset === "light" ? "#0d1e34" : "#ffffff",
          filter: `url(#${turbulenceId})`,
          mixBlendMode: preset === "light" ? "overlay" : "soft-light",
        }}
      />

      <AbsoluteFill
        style={{
          pointerEvents: "none",
          background: `radial-gradient(circle at center, rgba(0,0,0,0) ${vignetteRadius}%, rgba(0,0,0,0.38) 100%)`,
        }}
      />
    </AbsoluteFill>
  );
};
