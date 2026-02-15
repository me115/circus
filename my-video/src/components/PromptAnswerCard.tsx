import {interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";
import {tokens, shadowToCss} from "../theme/tokens";

type PromptAnswerCardProps = {
  prompt: string;
  answer: string;
  startFrame: number;
  appearMode?: "slideUp" | "fade" | "pop";
  showCursor?: boolean;
  typing?: {
    enabled: boolean;
    cps: number;
  };
};

export const PromptAnswerCard = ({
  prompt,
  answer,
  startFrame,
  appearMode = "slideUp",
  showCursor = true,
  typing,
}: PromptAnswerCardProps) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();

  const localFrame = frame - startFrame;
  const inSpring = spring({
    fps,
    frame: Math.max(0, localFrame),
    config: tokens.motion.defaultSpring,
  });

  const baseOpacity = interpolate(localFrame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  let transform = "none";
  let opacity = baseOpacity;

  if (appearMode === "slideUp") {
    transform = `translateY(${interpolate(inSpring, [0, 1], [36, 0])}px)`;
  }

  if (appearMode === "fade") {
    opacity = baseOpacity;
  }

  if (appearMode === "pop") {
    transform = `translateY(${interpolate(inSpring, [0, 1], [14, 0])}px) scale(${interpolate(inSpring, [0, 1], [0.96, 1])})`;
  }

  const typingEnabled = typing?.enabled ?? false;
  const cps = typing?.cps ?? 18;
  const visibleCharCount = typingEnabled
    ? Math.max(0, Math.floor((Math.max(0, localFrame) / fps) * cps))
    : answer.length;
  const displayedAnswer = answer.slice(0, visibleCharCount);
  const cursorVisible = showCursor && typingEnabled && Math.floor(frame / 10) % 2 === 0;

  return (
    <div
      style={{
        width: Math.min(Math.floor(width * 0.74), 1220),
        margin: "0 auto",
        borderRadius: tokens.radii.xl,
        boxShadow: shadowToCss(tokens.shadows.card),
        backgroundColor: "rgba(11,18,36,0.82)",
        border: "1px solid rgba(173, 214, 255, 0.24)",
        padding: tokens.spacing.lg,
        transform,
        opacity,
        fontFamily: tokens.typography.fontFamilySans,
        backdropFilter: "blur(12px)",
      }}
    >
      <div
        style={{
          padding: tokens.spacing.md,
          borderRadius: tokens.radii.lg,
          backgroundColor: "rgba(91, 140, 220, 0.18)",
          marginBottom: tokens.spacing.md,
        }}
      >
        <div
          style={{
            fontSize: tokens.typography.sizes.caption,
            color: tokens.colors.textMuted,
            marginBottom: tokens.spacing.xs,
            letterSpacing: 0.4,
            textTransform: "uppercase",
          }}
        >
          Prompt
        </div>
        <div
          style={{
            margin: 0,
            fontSize: tokens.typography.sizes.body,
            color: "#f4f8ff",
            lineHeight: 1.32,
          }}
        >
          {prompt}
        </div>
      </div>

      <div
        style={{
          padding: tokens.spacing.md,
          borderRadius: tokens.radii.lg,
          backgroundColor: "rgba(68, 230, 216, 0.12)",
        }}
      >
        <div
          style={{
            fontSize: tokens.typography.sizes.caption,
            color: tokens.colors.textMuted,
            marginBottom: tokens.spacing.xs,
            letterSpacing: 0.4,
            textTransform: "uppercase",
          }}
        >
          Answer
        </div>
        <div
          style={{
            margin: 0,
            fontSize: tokens.typography.sizes.body,
            color: "#eff7ff",
            lineHeight: 1.4,
            minHeight: tokens.typography.sizes.body * 3.2,
          }}
        >
          {displayedAnswer}
          {showCursor ? (
            <span
              style={{
                display: "inline-block",
                width: 3,
                height: tokens.typography.sizes.body + 2,
                marginLeft: 4,
                transform: "translateY(6px)",
                backgroundColor: "#d9f6ff",
                opacity: cursorVisible ? 1 : 0,
              }}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
};
