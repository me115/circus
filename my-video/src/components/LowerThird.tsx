import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {fadeInOut} from "../theme/motion";
import {tokens} from "../theme/tokens";

type LowerThirdProps = {
  title: string;
  source?: string;
  startFrame: number;
  durationInFrames: number;
  align?: "left" | "right";
};

export const LowerThird = ({
  title,
  source,
  startFrame,
  durationInFrames,
  align = "left",
}: LowerThirdProps) => {
  const frame = useCurrentFrame();

  const endFrame = startFrame + durationInFrames;
  const entryEnd = startFrame + 14;
  const exitStart = endFrame - 12;

  const opacity = fadeInOut(frame, startFrame, endFrame);
  const enterY = interpolate(frame, [startFrame, entryEnd], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitY = interpolate(frame, [exitStart, endFrame], [0, 10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = frame >= exitStart ? exitY : enterY;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: align === "left" ? "flex-start" : "flex-end",
        padding: tokens.spacing.xl,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${translateY}px)`,
          maxWidth: "42%",
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
