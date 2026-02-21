import React from "react";
import {AbsoluteFill} from "remotion";
import {AnimatedText} from "../components/beat/AnimatedText";
import {Card} from "../components/beat/Card";
import {SceneProps} from "./types";

export const DefinitionScene: React.FC<SceneProps> = ({
  beat,
  durationInFrames,
  aspect,
}) => {
  const textLine = beat.onScreen[0] ?? beat.subtitle ?? "";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: aspect === "9:16" ? "0 80px" : "0 160px",
      }}
    >
      <Card style={{width: "100%", maxWidth: aspect === "9:16" ? 930 : 1320}}>
        <div style={{fontSize: aspect === "9:16" ? 54 : 62, fontWeight: 800, marginBottom: 18}}>
          {beat.title ?? "Definition"}
        </div>
        <AnimatedText
          text={textLine}
          emphasis={beat.emphasis}
          durationInFrames={durationInFrames}
          fontSize={aspect === "9:16" ? 46 : 52}
          maxCharsPerLine={aspect === "9:16" ? 16 : 32}
          maxLines={2}
          textAlign="left"
          mode="line"
        />
      </Card>
    </AbsoluteFill>
  );
};
