import {interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {tokens} from "../theme/tokens";
import {entranceStyle} from "../theme/motion";

type BeforeAfterProps = {
  beforeTitle: string;
  afterTitle: string;
  beforeBullets: string[];
  afterBullets: string[];
  marker?: string;
};

const Card = ({
  title,
  bullets,
  opacity,
  y,
  isPortrait,
}: {
  title: string;
  bullets: string[];
  opacity: number;
  y: number;
  isPortrait: boolean;
}) => {
  return (
    <div
      style={{
        flex: 1,
        height: "100%",
        minHeight: isPortrait ? 280 : 220,
        borderRadius: tokens.radii.xl,
        border: "1px solid rgba(255,255,255,0.18)",
        background: "linear-gradient(160deg, rgba(9,16,34,0.82), rgba(12,22,44,0.66))",
        boxShadow: `${tokens.shadows.card.x}px ${tokens.shadows.card.y}px ${tokens.shadows.card.blur}px ${tokens.shadows.card.spread}px ${tokens.shadows.card.color}`,
        padding: isPortrait ? 26 : 24,
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <div
        style={{
          color: "#f4f8ff",
          fontFamily: tokens.typography.fontFamilySans,
          fontSize: Math.round(tokens.typography.sizes.title * (isPortrait ? 0.52 : 0.6)),
          fontWeight: 760,
          marginBottom: isPortrait ? 12 : 14,
        }}
      >
        {title}
      </div>
      <div style={{display: "grid", gap: isPortrait ? 8 : 10}}>
        {bullets.slice(0, 3).map((bullet) => (
          <div
            key={`${title}-${bullet}`}
            style={{
              color: tokens.colors.textMuted,
              fontFamily: tokens.typography.fontFamilySans,
              fontSize: Math.round(tokens.typography.sizes.body * (isPortrait ? 0.42 : 0.52)),
              lineHeight: 1.24,
            }}
          >
            • {bullet}
          </div>
        ))}
      </div>
    </div>
  );
};

export const BeforeAfter = ({
  beforeTitle,
  afterTitle,
  beforeBullets,
  afterBullets,
  marker = "vs",
}: BeforeAfterProps) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const isPortrait = height > width;
  const beforeIn = entranceStyle(frame, 30, 2);
  const afterIn = entranceStyle(frame, 30, 10);
  const markerOpacity = interpolate(frame, [12, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "stretch",
        gap: isPortrait ? 18 : 22,
        width: "100%",
        height: "100%",
      }}
    >
      <Card
        title={beforeTitle}
        bullets={beforeBullets}
        opacity={beforeIn.opacity}
        y={beforeIn.y}
        isPortrait={isPortrait}
      />
      <div
        style={{
          color: tokens.colors.secondary,
          fontFamily: tokens.typography.fontFamilySans,
          fontWeight: 800,
          fontSize: Math.round(tokens.typography.sizes.title * (isPortrait ? 0.6 : 0.66)),
          opacity: markerOpacity,
          display: "flex",
          alignItems: "center",
          transform: `scale(${interpolate(frame, [12, 22], [0.96, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })})`,
        }}
      >
        {marker}
      </div>
      <Card
        title={afterTitle}
        bullets={afterBullets}
        opacity={afterIn.opacity}
        y={afterIn.y}
        isPortrait={isPortrait}
      />
    </div>
  );
};
