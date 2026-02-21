import React from "react";
import {interpolate, useCurrentFrame} from "remotion";
import {wrapText} from "../../utils/wrapText";
import {EMPH_FRAMES, enter, emphasize, exit} from "../../motion/timing";

type AnimatedTextProps = {
  text?: string;
  lines?: string[];
  emphasis?: string[];
  mode?: "line" | "word";
  fontSize?: number;
  lineHeight?: number;
  color?: string;
  maxCharsPerLine?: number;
  maxLines?: number;
  textAlign?: "left" | "center";
  durationInFrames: number;
};

const normalizeToken = (token: string): string => {
  return token.toLowerCase().replace(/[.,!?;:()[\]{}'"`]/g, "");
};

export const AnimatedText: React.FC<AnimatedTextProps> = ({
  text,
  lines,
  emphasis = [],
  mode = "line",
  fontSize = 64,
  lineHeight = 1.12,
  color = "#f5f7ff",
  maxCharsPerLine = 24,
  maxLines = 2,
  textAlign = "center",
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const wrappedLines = React.useMemo(() => {
    if (Array.isArray(lines) && lines.length > 0) {
      return lines;
    }
    const source = (text ?? "").trim();
    if (!source) {
      return [];
    }
    return wrapText(source, {maxCharsPerLine, maxLines}).lines;
  }, [lines, maxCharsPerLine, maxLines, text]);

  const emphasisSet = React.useMemo(
    () => new Set(emphasis.map((item) => normalizeToken(item))),
    [emphasis],
  );

  const baseOpacity = enter(frame) * exit(frame, durationInFrames);
  const baseTransform = interpolate(enter(frame), [0, 1], [12, 0]);

  return (
    <div
      style={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        gap: fontSize * 0.22,
        alignItems: textAlign === "center" ? "center" : "flex-start",
        opacity: baseOpacity,
        transform: `translateY(${baseTransform}px)`,
      }}
    >
      {wrappedLines.map((line, lineIndex) => {
        const lineDelay = lineIndex * EMPH_FRAMES;
        const lineOpacity =
          mode === "line"
            ? interpolate(frame, [lineDelay, lineDelay + EMPH_FRAMES], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            : 1;

        const words = line.split(/\s+/).filter(Boolean);
        return (
          <div
            key={`${line}-${lineIndex}`}
            style={{
              fontSize,
              lineHeight,
              fontWeight: 700,
              color,
              textAlign,
              letterSpacing: "-0.02em",
              opacity: Math.max(0, Math.min(1, lineOpacity)),
              width: "100%",
            }}
          >
            {words.length === 0 ? (
              line
            ) : (
              words.map((word, wordIndex) => {
                const wordDelay = lineDelay + wordIndex * 2;
                const wordOpacity =
                  mode === "word"
                    ? interpolate(
                        frame,
                        [wordDelay, wordDelay + Math.max(2, EMPH_FRAMES / 2)],
                        [0, 1],
                        {
                          extrapolateLeft: "clamp",
                          extrapolateRight: "clamp",
                        },
                      )
                    : 1;
                const token = normalizeToken(word);
                const isHighlight = emphasisSet.has(token);
                const scale = isHighlight
                  ? emphasize(frame, wordDelay, wordDelay + EMPH_FRAMES)
                  : 1;
                return (
                  <span
                    key={`${word}-${wordIndex}`}
                    style={{
                      display: "inline-block",
                      marginRight: wordIndex === words.length - 1 ? 0 : 10,
                      opacity: Math.max(0, Math.min(1, wordOpacity)),
                      color: isHighlight ? "#48d8ff" : color,
                      transform: `scale(${scale})`,
                      transformOrigin: "center bottom",
                    }}
                  >
                    {word}
                  </span>
                );
              })
            )}
          </div>
        );
      })}
    </div>
  );
};
