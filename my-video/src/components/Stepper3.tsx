import {interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {tokens} from "../theme/tokens";

type StepItem = {
  title: string;
  text: string;
};

type Stepper3Props = {
  steps: StepItem[];
};

export const Stepper3 = ({steps}: Stepper3Props) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const isPortrait = height > width;
  const stepTitleSize = isPortrait
    ? Math.round(tokens.typography.sizes.title * 0.5)
    : Math.round(tokens.typography.sizes.title * 0.5);
  const stepBodySize = isPortrait
    ? Math.round(tokens.typography.sizes.body * 0.45)
    : Math.round(tokens.typography.sizes.body * 0.46);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: isPortrait ? "1fr" : "repeat(3, 1fr)",
        gap: isPortrait ? 14 : 18,
        height: "100%",
      }}
    >
      {steps.slice(0, 3).map((step, idx) => {
        const start = idx * 8;
        const light = interpolate(frame, [start, start + 12], [0.35, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={step.title}
            style={{
              borderRadius: tokens.radii.xl,
              border: "1px solid rgba(255,255,255,0.2)",
              background: "linear-gradient(160deg, rgba(9,16,34,0.85), rgba(12,22,44,0.68))",
              padding: isPortrait ? 24 : 26,
              minHeight: isPortrait ? 152 : 236,
              opacity: light,
              boxShadow: `0 0 ${Math.round(22 * light)}px rgba(45,226,230,${0.18 * light})`,
              display: "flex",
              flexDirection: isPortrait ? "row" : "column",
              alignItems: isPortrait ? "center" : "flex-start",
              justifyContent: "flex-start",
              gap: isPortrait ? 18 : 0,
            }}
          >
            <div
              style={{
                width: isPortrait ? 44 : 52,
                height: isPortrait ? 44 : 52,
                borderRadius: 999,
                display: "grid",
                placeItems: "center",
                marginBottom: 12,
                border: "1px solid rgba(124,92,255,0.5)",
                backgroundColor: "rgba(124,92,255,0.18)",
                color: "#ffffff",
                fontFamily: tokens.typography.fontFamilySans,
                fontWeight: 700,
                fontSize: Math.round(tokens.typography.sizes.caption * (isPortrait ? 0.72 : 0.78)),
                flexShrink: 0,
              }}
            >
              {idx + 1}
            </div>
            <div style={{display: "flex", flexDirection: "column", minWidth: 0}}>
              <div
                style={{
                  color: "#f4f8ff",
                  fontFamily: tokens.typography.fontFamilySans,
                  fontSize: stepTitleSize,
                  fontWeight: 760,
                  marginBottom: 8,
                }}
              >
                {step.title}
              </div>
              <div
                style={{
                  color: tokens.colors.textMuted,
                  fontFamily: tokens.typography.fontFamilySans,
                  fontSize: stepBodySize,
                  lineHeight: 1.28,
                }}
              >
                {step.text}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
