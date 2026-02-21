import React from "react";
import {AbsoluteFill} from "remotion";
import {AnimatedText} from "../components/beat/AnimatedText";
import {Card} from "../components/beat/Card";
import {SceneProps} from "./types";

export const MentalModelScene: React.FC<SceneProps> = ({
  beat,
  durationInFrames,
  aspect,
}) => {
  const left = beat.onScreen[0] ?? "关键词搜索：找字面";
  const right = beat.onScreen[1] ?? "向量搜索：找语义";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: aspect === "9:16" ? "0 56px" : "0 120px",
      }}
    >
      <div
        style={{
          width: "100%",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 28,
          alignItems: "stretch",
        }}
      >
        <Card>
          <div style={{fontSize: aspect === "9:16" ? 44 : 48, fontWeight: 800, marginBottom: 12}}>
            传统检索
          </div>
          <AnimatedText
            text={left}
            durationInFrames={durationInFrames}
            fontSize={aspect === "9:16" ? 34 : 38}
            maxCharsPerLine={aspect === "9:16" ? 14 : 22}
            maxLines={2}
            textAlign="left"
            mode="line"
          />
        </Card>
        <Card>
          <div style={{fontSize: aspect === "9:16" ? 44 : 48, fontWeight: 800, marginBottom: 12}}>
            向量检索
          </div>
          <AnimatedText
            text={right}
            emphasis={beat.emphasis}
            durationInFrames={durationInFrames}
            fontSize={aspect === "9:16" ? 34 : 38}
            maxCharsPerLine={aspect === "9:16" ? 14 : 22}
            maxLines={2}
            textAlign="left"
            mode="line"
          />
        </Card>
      </div>
    </AbsoluteFill>
  );
};
