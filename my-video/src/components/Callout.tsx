import {interpolate, useCurrentFrame} from "remotion";
import {tokens} from "../theme/tokens";

type CalloutProps = {
  keyword: string;
  description: string;
};

export const Callout = ({keyword, description}: CalloutProps) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 14], [0.92, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        display: "flex",
        justifyContent: "center",
        opacity,
        transform: `scale(${zoom})`,
      }}
    >
      <div
        style={{
          width: "82%",
          borderRadius: tokens.radii.xl,
          border: "1px solid rgba(255,255,255,0.2)",
          background: "linear-gradient(160deg, rgba(9,16,34,0.86), rgba(12,22,44,0.72))",
          padding: 24,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            right: 24,
            top: 24,
            width: 90,
            height: 90,
            borderRadius: 999,
            border: "2px solid rgba(45,226,230,0.7)",
            boxShadow: "0 0 28px rgba(45,226,230,0.28)",
          }}
        />
        <div
          style={{
            color: tokens.colors.secondary,
            fontFamily: tokens.typography.fontFamilySans,
            fontSize: Math.round(tokens.typography.sizes.caption * 0.8),
            fontWeight: 760,
            textTransform: "uppercase",
            marginBottom: 8,
          }}
        >
          explain term
        </div>
        <div
          style={{
            color: "#ffffff",
            fontFamily: tokens.typography.fontFamilySans,
            fontSize: Math.round(tokens.typography.sizes.title * 0.48),
            fontWeight: 800,
            marginBottom: 8,
          }}
        >
          {keyword}
        </div>
        <div
          style={{
            color: tokens.colors.textMuted,
            fontFamily: tokens.typography.fontFamilySans,
            fontSize: Math.round(tokens.typography.sizes.body * 0.38),
            lineHeight: 1.24,
          }}
        >
          {description}
        </div>
      </div>
    </div>
  );
};
