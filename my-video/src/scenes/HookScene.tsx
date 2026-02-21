import React from "react";
import {AbsoluteFill} from "remotion";
import {AnimatedText} from "../components/beat/AnimatedText";
import {SceneProps} from "./types";

export const HookScene: React.FC<SceneProps> = ({beat, durationInFrames, aspect}) => {
  const lines = beat.onScreen.length > 0 ? beat.onScreen.slice(0, 2) : [beat.title ?? ""];

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: aspect === "9:16" ? "0 90px" : "0 180px",
      }}
    >
      <AnimatedText
        lines={lines}
        emphasis={beat.emphasis}
        mode="line"
        durationInFrames={durationInFrames}
        fontSize={aspect === "9:16" ? 86 : 94}
        maxCharsPerLine={aspect === "9:16" ? 14 : 28}
        maxLines={2}
        textAlign="center"
      />
    </AbsoluteFill>
  );
};
