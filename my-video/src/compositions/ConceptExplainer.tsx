import React from "react";
import {AbsoluteFill, Audio, Sequence, staticFile} from "remotion";
import {parseVideoSpec, VideoSpec} from "../schema/spec";
import {buildTimeline} from "../timeline/buildTimeline";
import {validateSpecForReadability} from "../schema/validateReadability";
import {DefinitionScene} from "../scenes/DefinitionScene";
import {DiagramStepsScene} from "../scenes/DiagramStepsScene";
import {HookScene} from "../scenes/HookScene";
import {MentalModelScene} from "../scenes/MentalModelScene";
import {MisconceptionScene} from "../scenes/MisconceptionScene";
import {OutroScene} from "../scenes/OutroScene";
import {RecapScene} from "../scenes/RecapScene";

type ConceptExplainerProps = {
  spec: VideoSpec;
};

const SceneRenderer: React.FC<{
  spec: VideoSpec;
  beat: VideoSpec["beats"][number];
  durationInFrames: number;
}> = ({spec, beat, durationInFrames}) => {
  const sceneProps = {
    beat,
    durationInFrames,
    aspect: spec.meta.aspect,
  } as const;

  switch (beat.type) {
    case "hook":
      return <HookScene {...sceneProps} />;
    case "definition":
      return <DefinitionScene {...sceneProps} />;
    case "mental_model":
      return <MentalModelScene {...sceneProps} />;
    case "diagram_steps":
      return <DiagramStepsScene {...sceneProps} />;
    case "misconception":
      return <MisconceptionScene {...sceneProps} />;
    case "recap":
      return <RecapScene {...sceneProps} />;
    case "outro":
      return <OutroScene {...sceneProps} />;
    default:
      return <DefinitionScene {...sceneProps} />;
  }
};

export const ConceptExplainer: React.FC<ConceptExplainerProps> = ({spec}) => {
  const safeSpec = React.useMemo(() => parseVideoSpec(spec), [spec]);
  const timeline = React.useMemo(() => buildTimeline(safeSpec), [safeSpec]);
  const warnings = React.useMemo(() => validateSpecForReadability(safeSpec), [safeSpec]);

  React.useEffect(() => {
    if (warnings.length === 0) {
      return;
    }
    console.warn("[readability warnings]", warnings);
  }, [warnings]);

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 18% 22%, rgba(105,156,255,0.26), transparent 46%), radial-gradient(circle at 82% 70%, rgba(69,218,255,0.24), transparent 44%), linear-gradient(160deg,#081230,#0f2451 56%,#0a1b3e)",
        color: "#f6f8ff",
      }}
    >
      {timeline.items.map((item) => {
        return (
          <Sequence
            key={item.beat.id}
            from={item.fromFrame}
            durationInFrames={item.durationFrames}
          >
            <SceneRenderer
              spec={safeSpec}
              beat={item.beat}
              durationInFrames={item.durationFrames}
            />
          </Sequence>
        );
      })}

      {safeSpec.audio?.src ? (
        <Sequence from={Math.round((safeSpec.audio.startSec ?? 0) * timeline.fps)}>
          <Audio src={staticFile(safeSpec.audio.src)} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
