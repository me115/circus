import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {springIn} from "../theme/motion";
import {tokens} from "../theme/tokens";

type HeroTitleProps = {
  title: string;
  subtitle?: string;
  align?: "left" | "center";
  enterDelayFrames?: number;
  accentWord?: string;
};

const renderTitleWords = (title: string, accentWord?: string) => {
  const normalizedAccent = accentWord?.trim().toLowerCase();

  return title.split(" ").map((word, idx) => {
    const normalizedWord = word.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
    const isAccent = normalizedAccent && normalizedWord === normalizedAccent;

    return (
      <span
        key={`${word}-${idx}`}
        style={
          isAccent
            ? {
                color: tokens.colors.accent,
                textShadow: "0 0 20px rgba(255, 217, 120, 0.42)",
              }
            : undefined
        }
      >
        {word}
        {idx < title.split(" ").length - 1 ? " " : ""}
      </span>
    );
  });
};

export const HeroTitle = ({
  title,
  subtitle,
  align = "center",
  enterDelayFrames = 0,
  accentWord,
}: HeroTitleProps) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();

  const titleIn = springIn(frame, fps, enterDelayFrames);
  const subtitleIn = springIn(frame, fps, enterDelayFrames + 10);

  const titleOpacity = interpolate(titleIn, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleScale = interpolate(titleIn, [0, 1], [0.96, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(titleIn, [0, 1], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: align === "center" ? "center" : "flex-start",
        paddingLeft: align === "left" ? tokens.spacing.xl : tokens.spacing.lg,
        paddingRight: tokens.spacing.lg,
        color: "#f3f7ff",
        fontFamily: tokens.typography.fontFamilySans,
      }}
    >
      <div
        style={{
          maxWidth: Math.floor(width * 0.8),
          textAlign: align,
          transform: `translateY(${titleY}px) scale(${titleScale})`,
          opacity: titleOpacity,
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: tokens.typography.sizes.hero,
            fontWeight: tokens.typography.fontWeightBold,
            letterSpacing: -1.8,
            lineHeight: 0.95,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {renderTitleWords(title, accentWord)}
        </h1>

        {subtitle ? (
          <p
            style={{
              margin: `${tokens.spacing.md}px 0 0 0`,
              fontSize: tokens.typography.sizes.body,
              lineHeight: 1.3,
              color: tokens.colors.textMuted,
              opacity: subtitleIn,
              transform: `translateY(${interpolate(subtitleIn, [0, 1], [16, 0])}px)`,
            }}
          >
            {subtitle}
          </p>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
