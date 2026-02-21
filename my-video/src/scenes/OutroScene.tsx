import React from "react";
import {AbsoluteFill} from "remotion";
import {AnimatedText} from "../components/beat/AnimatedText";
import {SceneProps} from "./types";

export const OutroScene: React.FC<SceneProps> = ({beat, durationInFrames, aspect}) => {
  const line = beat.onScreen[0] ?? beat.title ?? "Thanks for watching";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: aspect === "9:16" ? "0 80px" : "0 160px",
      }}
    >
      <AnimatedText
        text={line}
        emphasis={beat.emphasis}
        durationInFrames={durationInFrames}
        fontSize={aspect === "9:16" ? 64 : 76}
        maxCharsPerLine={aspect === "9:16" ? 14 : 26}
        maxLines={2}
        textAlign="center"
        mode="line"
      />
    </AbsoluteFill>
  );
};
