import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {Card} from "../components/beat/Card";
import {Callout} from "../components/beat/Callout";
import {enter, exit} from "../motion/timing";
import {SceneProps} from "./types";

const viewBoxSize = 1000;

export const DiagramStepsScene: React.FC<SceneProps> = ({
  beat,
  durationInFrames,
  aspect,
}) => {
  const frame = useCurrentFrame();
  const steps = beat.steps;
  if (steps.length === 0) {
    return (
      <AbsoluteFill style={{justifyContent: "center", alignItems: "center", color: "#fff"}}>
        <div style={{fontSize: 48, fontWeight: 700}}>No diagram steps provided.</div>
      </AbsoluteFill>
    );
  }

  const inProgress = enter(frame);
  const outProgress = exit(frame, durationInFrames);
  const opacity = inProgress * outProgress;
  const stepIndex = Math.min(
    steps.length - 1,
    Math.floor((frame / Math.max(durationInFrames, 1)) * steps.length),
  );
  const step = steps[stepIndex];

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: aspect === "9:16" ? "80px 48px" : "70px 120px",
      }}
    >
      <Card style={{width: "100%", maxWidth: aspect === "9:16" ? 960 : 1500, opacity}}>
        <div style={{fontSize: aspect === "9:16" ? 42 : 46, fontWeight: 800, marginBottom: 16}}>
          {beat.title ?? "Diagram Steps"}
        </div>
        <div
          style={{
            fontSize: aspect === "9:16" ? 30 : 36,
            color: "rgba(240,245,255,0.9)",
            marginBottom: 18,
            minHeight: aspect === "9:16" ? 84 : 56,
          }}
        >
          {step.label}
        </div>

        <div style={{position: "relative", width: "100%", aspectRatio: "16/9"}}>
          <svg
            viewBox={`0 0 ${viewBoxSize} ${viewBoxSize}`}
            width="100%"
            height="100%"
            style={{
              borderRadius: 24,
              background:
                "radial-gradient(circle at 22% 24%, rgba(98,149,255,0.18), transparent 50%), rgba(10,20,45,0.75)",
            }}
          >
            {step.edges.map((edge) => {
              const from = step.nodes.find((node) => node.id === edge.from);
              const to = step.nodes.find((node) => node.id === edge.to);
              if (!from || !to) {
                return null;
              }
              return (
                <line
                  key={`${edge.from}-${edge.to}`}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke="rgba(118,204,255,0.75)"
                  strokeWidth={7}
                  strokeLinecap="round"
                />
              );
            })}
            {step.nodes.map((node, index) => {
              const focused = step.focusNodeIds.includes(node.id);
              const scale = focused
                ? interpolate(inProgress, [0, 1], [0.92, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })
                : 1;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x} ${node.y}) scale(${scale})`}
                  style={{
                    transformOrigin: "center",
                  }}
                >
                  <circle
                    cx={0}
                    cy={0}
                    r={focused ? 72 : 58}
                    fill={focused ? "rgba(72,216,255,0.28)" : "rgba(31,84,168,0.24)"}
                    stroke={focused ? "#55ddff" : "rgba(190,214,255,0.6)"}
                    strokeWidth={focused ? 6 : 4}
                  />
                  <text
                    x={0}
                    y={8}
                    textAnchor="middle"
                    fill="#f8faff"
                    style={{
                      fontSize: focused ? 28 : 23,
                      fontWeight: focused ? 800 : 700,
                    }}
                  >
                    {node.text}
                  </text>
                  <text
                    x={0}
                    y={focused ? 98 : 86}
                    textAnchor="middle"
                    fill="rgba(210,230,255,0.9)"
                    style={{
                      fontSize: 16,
                      fontWeight: 700,
                    }}
                  >
                    {index + 1}
                  </text>
                </g>
              );
            })}
          </svg>
          {step.focusNodeIds.length >= 1 ? (
            <Callout
              from={{x: 780, y: 210}}
              to={{x: 620, y: 320}}
              label={`Step ${stepIndex + 1}`}
              durationInFrames={durationInFrames}
            />
          ) : null}
        </div>
      </Card>
    </AbsoluteFill>
  );
};
