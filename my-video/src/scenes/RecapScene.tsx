import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {Card} from "../components/beat/Card";
import {SceneProps} from "./types";

export const RecapScene: React.FC<SceneProps> = ({beat, durationInFrames, aspect}) => {
  const frame = useCurrentFrame();
  const bullets = beat.onScreen.slice(0, 3);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: aspect === "9:16" ? "0 70px" : "0 130px",
      }}
    >
      <Card style={{width: "100%", maxWidth: aspect === "9:16" ? 960 : 1320}}>
        <div style={{fontSize: aspect === "9:16" ? 46 : 52, fontWeight: 800, marginBottom: 20}}>
          {beat.title ?? "Recap"}
        </div>
        <div style={{display: "flex", flexDirection: "column", gap: 18}}>
          {bullets.map((line, index) => {
            const start = index * Math.floor(durationInFrames / Math.max(3, bullets.length + 1));
            const opacity = interpolate(frame, [start, start + 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const y = interpolate(frame, [start, start + 10], [10, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div
                key={`${line}-${index}`}
                style={{
                  fontSize: aspect === "9:16" ? 34 : 40,
                  fontWeight: 700,
                  opacity,
                  transform: `translateY(${y}px)`,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <span style={{color: "#4edbff"}}>•</span>
                <span>{line}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </AbsoluteFill>
  );
};
