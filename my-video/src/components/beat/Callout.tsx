import React from "react";
import {interpolate, useCurrentFrame} from "remotion";
import {enter, exit} from "../../motion/timing";

type Point = {
  x: number;
  y: number;
};

type CalloutProps = {
  from: Point;
  to: Point;
  label?: string;
  color?: string;
  durationInFrames: number;
};

export const Callout: React.FC<CalloutProps> = ({
  from,
  to,
  label,
  color = "#4edbff",
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const inProgress = enter(frame);
  const outProgress = exit(frame, durationInFrames);
  const draw = Math.max(0.01, Math.min(1, inProgress * outProgress));
  const totalLength = Math.hypot(to.x - from.x, to.y - from.y);
  const dashOffset = interpolate(draw, [0, 1], [totalLength, 0]);

  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 1000 1000"
      style={{position: "absolute", inset: 0, overflow: "visible"}}
    >
      <defs>
        <marker
          id="arrow-head"
          markerWidth="10"
          markerHeight="10"
          refX="8"
          refY="3"
          orient="auto"
          markerUnits="strokeWidth"
        >
          <path d="M0,0 L0,6 L9,3 z" fill={color} />
        </marker>
      </defs>
      <line
        x1={from.x}
        y1={from.y}
        x2={to.x}
        y2={to.y}
        stroke={color}
        strokeWidth={4}
        strokeLinecap="round"
        strokeDasharray={totalLength}
        strokeDashoffset={dashOffset}
        markerEnd="url(#arrow-head)"
      />
      <circle
        cx={to.x}
        cy={to.y}
        r={22}
        fill="transparent"
        stroke={color}
        strokeWidth={3}
        opacity={draw}
      />
      {label ? (
        <text
          x={(from.x + to.x) / 2}
          y={(from.y + to.y) / 2 - 14}
          textAnchor="middle"
          fill={color}
          style={{
            fontSize: 34,
            fontWeight: 700,
            opacity: draw,
          }}
        >
          {label}
        </text>
      ) : null}
    </svg>
  );
};
