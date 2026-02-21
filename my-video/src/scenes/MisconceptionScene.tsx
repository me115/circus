import React from "react";
import {AbsoluteFill} from "remotion";
import {AnimatedText} from "../components/beat/AnimatedText";
import {Card} from "../components/beat/Card";
import {Stamp} from "../components/beat/Stamp";
import {SceneProps} from "./types";

export const MisconceptionScene: React.FC<SceneProps> = ({
  beat,
  durationInFrames,
  aspect,
}) => {
  const myth = beat.onScreen[0] ?? "误区：向量数据库就是更快SQL";
  const fix = beat.onScreen[1] ?? "正确：它解决的是语义相似检索。";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: aspect === "9:16" ? "0 76px" : "0 150px",
      }}
    >
      <Card style={{width: "100%", maxWidth: aspect === "9:16" ? 960 : 1400}}>
        <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
          <div style={{fontSize: aspect === "9:16" ? 42 : 50, fontWeight: 800}}>
            Misconception Check
          </div>
          <Stamp text="MYTH" durationInFrames={durationInFrames} />
        </div>
        <div style={{marginTop: 24}}>
          <AnimatedText
            text={myth}
            durationInFrames={durationInFrames}
            fontSize={aspect === "9:16" ? 36 : 44}
            maxCharsPerLine={aspect === "9:16" ? 16 : 28}
            maxLines={2}
            textAlign="left"
            mode="line"
          />
        </div>
        <div style={{marginTop: 18}}>
          <AnimatedText
            text={fix}
            emphasis={beat.emphasis}
            durationInFrames={durationInFrames}
            fontSize={aspect === "9:16" ? 34 : 40}
            maxCharsPerLine={aspect === "9:16" ? 16 : 28}
            maxLines={2}
            textAlign="left"
            mode="line"
          />
        </div>
      </Card>
    </AbsoluteFill>
  );
};
