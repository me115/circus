import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {entranceStyle, fadeInOut} from "../theme/motion";
import {tokens} from "../theme/tokens";
import {stylekit} from "../style";

type LowerThirdProps = {
  title: string;
  source?: string;
  startFrame: number;
  durationInFrames: number;
  align?: "left" | "right";
  yPct?: number;
  maxWidthPct?: number;
};

export const LowerThird = ({
  title,
  source,
  startFrame,
  durationInFrames,
  align = "left",
  yPct,
  maxWidthPct,
}: LowerThirdProps) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const isPortrait = height > width;

  const endFrame = startFrame + durationInFrames;
  const entryEnd = startFrame + 14;
  const exitStart = endFrame - 12;

  const opacity = fadeInOut(frame, startFrame, endFrame);
  const entrance = entranceStyle(frame, 30, startFrame);
  const enterY = interpolate(frame, [startFrame, entryEnd], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitY = interpolate(frame, [exitStart, endFrame], [0, 10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = frame >= exitStart ? exitY : enterY;
  const safeLeft = Math.round(width * stylekit.safeArea.leftPct);
  const safeRight = Math.round(width * stylekit.safeArea.rightPct);
  const safeBottom = Math.round(
    height * (isPortrait ? stylekit.safeArea.bottomPct : Math.min(0.12, stylekit.safeArea.bottomPct)),
  );
  const resolvedYPct = Math.min(0.9, Math.max(0.54, yPct ?? (isPortrait ? 0.74 : 0.68)));
  const resolvedMaxWidthPct = Math.max(
    0.48,
    Math.min(0.84, maxWidthPct ?? (isPortrait ? 0.82 : 0.62)),
  );
  const topPx = Math.round(height * resolvedYPct);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: align === "left" ? "flex-start" : "flex-end",
        paddingLeft: safeLeft,
        paddingRight: safeRight,
        paddingBottom: safeBottom,
        paddingTop: tokens.spacing.xl,
        top: topPx,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${translateY + entrance.y}px) scale(${entrance.scale})`,
          maxWidth: `${Math.round(resolvedMaxWidthPct * 100)}%`,
          textAlign: align,
          fontFamily: tokens.typography.fontFamilySans,
        }}
      >
        <div
          style={{
            color: "#f2f7ff",
            fontSize: tokens.typography.sizes.body,
            fontWeight: 700,
            lineHeight: 1.22,
          }}
        >
          {title}
        </div>
        {source ? (
          <div
            style={{
              marginTop: tokens.spacing.xs,
              color: tokens.colors.textMuted,
              fontSize: tokens.typography.sizes.caption,
              letterSpacing: 0.5,
            }}
          >
            {source}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
