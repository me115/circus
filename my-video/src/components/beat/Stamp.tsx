import React from "react";
import {interpolate, useCurrentFrame} from "remotion";
import {enter, exit} from "../../motion/timing";

type StampProps = {
  text: string;
  durationInFrames: number;
};

export const Stamp: React.FC<StampProps> = ({text, durationInFrames}) => {
  const frame = useCurrentFrame();
  const inProgress = enter(frame);
  const opacity = inProgress * exit(frame, durationInFrames);
  const scale = interpolate(inProgress, [0, 1], [1.25, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        border: "5px solid rgba(255,85,100,0.88)",
        borderRadius: 14,
        color: "#ff6d83",
        fontSize: 48,
        fontWeight: 800,
        letterSpacing: "0.12em",
        padding: "12px 24px",
        transform: `rotate(-12deg) scale(${scale})`,
        opacity,
      }}
    >
      {text}
    </div>
  );
};
