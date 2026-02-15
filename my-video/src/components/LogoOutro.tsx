import {useState} from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {springIn} from "../theme/motion";
import {tokens} from "../theme/tokens";
import {BrandBackdrop} from "./BrandBackdrop";

type LogoOutroProps = {
  logoSrc: string;
  tagline: string;
  startFrame: number;
  durationInFrames: number;
  chimeSrc?: string;
};

export const LogoOutro = ({
  logoSrc,
  tagline,
  startFrame,
  durationInFrames,
  chimeSrc,
}: LogoOutroProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [logoError, setLogoError] = useState(false);

  const localFrame = Math.max(0, frame - startFrame);
  const inSpring = springIn(frame, fps, startFrame);
  const visibility = interpolate(
    frame,
    [startFrame, startFrame + 20, startFrame + durationInFrames - 24, startFrame + durationInFrames],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  return (
    <>
      <AbsoluteFill style={{opacity: visibility, pointerEvents: "none"}}>
        <BrandBackdrop preset="dark" intensity={0.84} animate safePadding={72} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          opacity: visibility,
          transform: `translateY(${interpolate(inSpring, [0, 1], [16, 0])}px) scale(${interpolate(
            inSpring,
            [0, 1],
            [0.97, 1],
          )})`,
        }}
      >
        <div
          style={{
            width: 180,
            height: 180,
            borderRadius: 42,
            overflow: "hidden",
            backgroundColor: "rgba(12, 22, 41, 0.9)",
            border: "1px solid rgba(176, 218, 255, 0.3)",
            boxShadow: "0 22px 60px rgba(0, 0, 0, 0.45)",
            display: "grid",
            placeItems: "center",
            marginBottom: tokens.spacing.md,
          }}
        >
          {logoSrc && !logoError ? (
            <Img
              src={logoSrc}
              style={{width: "100%", height: "100%", objectFit: "cover"}}
              onError={() => setLogoError(true)}
            />
          ) : (
            <div
              style={{
                color: "#e4f0ff",
                fontFamily: tokens.typography.fontFamilySans,
                fontWeight: 700,
                fontSize: 46,
              }}
            >
              G
            </div>
          )}
        </div>

        <div
          style={{
            fontFamily: tokens.typography.fontFamilySans,
            color: "#f2f7ff",
            fontSize: tokens.typography.sizes.title,
            fontWeight: 700,
            letterSpacing: -0.5,
            marginBottom: tokens.spacing.sm,
          }}
        >
          Gemini Style Demo
        </div>
        <div
          style={{
            fontFamily: tokens.typography.fontFamilySans,
            color: tokens.colors.textMuted,
            fontSize: tokens.typography.sizes.body,
            opacity: interpolate(localFrame, [10, 30], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {tagline}
        </div>
      </AbsoluteFill>

      {chimeSrc ? (
        <Sequence from={startFrame + 12} durationInFrames={Math.min(60, durationInFrames)}>
          <Audio src={chimeSrc} volume={0.4} />
        </Sequence>
      ) : null}
    </>
  );
};
