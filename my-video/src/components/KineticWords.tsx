import {interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";
import {tokens} from "../theme/tokens";
import {staggerFrame} from "../utils/beat";

type KineticMode = "pop" | "slide" | "type";

type KineticWordsProps = {
  words: string[];
  startFrame: number;
  wordStagger?: number;
  mode?: KineticMode;
  emphasize?: number[];
};

export const KineticWords = ({
  words,
  startFrame,
  wordStagger = 7,
  mode = "pop",
  emphasize = [],
}: KineticWordsProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const emphasizeSet = new Set(emphasize);

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        rowGap: tokens.spacing.sm,
        columnGap: tokens.spacing.xs,
        fontFamily: tokens.typography.fontFamilySans,
      }}
    >
      {words.map((word, index) => {
        const wordStart = staggerFrame(startFrame, index, wordStagger);
        const localFrame = frame - wordStart;
        const baseSpring = spring({
          fps,
          frame: Math.max(0, localFrame),
          config: tokens.motion.defaultSpring,
        });

        const opacity = interpolate(localFrame, [0, 6], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        let transform = "none";
        let shownWord = word;

        if (mode === "pop") {
          transform = `scale(${interpolate(baseSpring, [0, 1], [0.9, 1])})`;
        }

        if (mode === "slide") {
          transform = `translateY(${interpolate(baseSpring, [0, 1], [10, 0])}px)`;
        }

        if (mode === "type") {
          const charCount = Math.max(0, Math.floor((localFrame / fps) * 18));
          shownWord = word.slice(0, Math.min(word.length, charCount));
          transform = "none";
        }

        const isEmphasis = emphasizeSet.has(index);

        return (
          <span
            key={`${word}-${index}`}
            style={{
              opacity: mode === "type" && shownWord.length === 0 ? 0 : opacity,
              transform,
              fontSize: tokens.typography.sizes.body,
              fontWeight: isEmphasis ? 700 : 600,
              color: isEmphasis ? tokens.colors.accent : "#f3f7ff",
              textShadow: isEmphasis ? "0 0 18px rgba(255, 217, 120, 0.35)" : undefined,
              WebkitTextStroke: isEmphasis ? "0.7px rgba(255,255,255,0.25)" : undefined,
              letterSpacing: 0.4,
            }}
          >
            {shownWord}
          </span>
        );
      })}
    </div>
  );
};
