import {useMemo, useState} from "react";
import {AbsoluteFill, Img, OffthreadVideo, interpolate, useCurrentFrame} from "remotion";
import {tokens, shadowToCss} from "../theme/tokens";

type BorderConfig = {
  width: number;
  color: string;
  opacity: number;
};

type KenBurnsConfig = {
  enabled: boolean;
  fromScale: number;
  toScale: number;
  fromX: number;
  toX: number;
  fromY: number;
  toY: number;
};

type MediaFrameProps = {
  kind: "image" | "video";
  src: string;
  startFrame: number;
  durationInFrames: number;
  cornerRadius?: number;
  border?: BorderConfig;
  kenBurns?: KenBurnsConfig;
};

const defaultBorder: BorderConfig = {
  width: 1,
  color: "#b6d8ff",
  opacity: 0.28,
};

const defaultKenBurns: KenBurnsConfig = {
  enabled: true,
  fromScale: 1.02,
  toScale: 1.08,
  fromX: -8,
  toX: 6,
  fromY: -6,
  toY: 4,
};

export const MediaFrame = ({
  kind,
  src,
  startFrame,
  durationInFrames,
  cornerRadius = tokens.radii.lg,
  border = defaultBorder,
  kenBurns = defaultKenBurns,
}: MediaFrameProps) => {
  const frame = useCurrentFrame();
  const [hasError, setHasError] = useState(false);

  const progress = interpolate(
    frame,
    [startFrame, startFrame + durationInFrames],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  const mediaStyle = useMemo(() => {
    const scale = kenBurns.enabled
      ? interpolate(progress, [0, 1], [kenBurns.fromScale, kenBurns.toScale])
      : 1;
    const x = kenBurns.enabled
      ? interpolate(progress, [0, 1], [kenBurns.fromX, kenBurns.toX])
      : 0;
    const y = kenBurns.enabled
      ? interpolate(progress, [0, 1], [kenBurns.fromY, kenBurns.toY])
      : 0;

    return {
      width: "100%",
      height: "100%",
      objectFit: "cover" as const,
      transform: `translate(${x}px, ${y}px) scale(${scale})`,
      filter: "saturate(1.04) contrast(1.03)",
    };
  }, [kenBurns.enabled, kenBurns.fromScale, kenBurns.toScale, kenBurns.fromX, kenBurns.toX, kenBurns.fromY, kenBurns.toY, progress]);

  const showFallback = hasError || !src;

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        borderRadius: cornerRadius,
        boxShadow: shadowToCss(tokens.shadows.soft),
        backgroundColor: "rgba(10,16,29,0.7)",
      }}
    >
      {showFallback ? (
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            color: "#d2dbef",
            fontFamily: tokens.typography.fontFamilySans,
            fontSize: tokens.typography.sizes.caption,
            letterSpacing: 0.6,
            textTransform: "uppercase",
            background:
              "linear-gradient(125deg, rgba(41,57,83,0.6), rgba(19,30,47,0.9))",
          }}
        >
          Missing media placeholder
        </AbsoluteFill>
      ) : kind === "image" ? (
        <Img src={src} style={mediaStyle} onError={() => setHasError(true)} />
      ) : (
        <OffthreadVideo
          src={src}
          style={mediaStyle}
          muted
          onError={() => setHasError(true)}
        />
      )}
      <AbsoluteFill
        style={{
          pointerEvents: "none",
          borderRadius: cornerRadius,
          border: `${border.width}px solid ${border.color}`,
          opacity: border.opacity,
        }}
      />
    </AbsoluteFill>
  );
};
