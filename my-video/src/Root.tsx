import "./index.css";
import {CalculateMetadataFunction, Composition} from "remotion";
import {GeminiStyleDemo} from "./compositions/GeminiStyleDemo";
import {ExplainerFromSpec} from "./compositions/ExplainerFromSpec";
import {SkillExplainer60} from "./compositions/SkillExplainer60";
import {ConceptExplainer} from "./compositions/ConceptExplainer";
import defaultBeatSpec from "./beats/vector-db.beats.json";
import {buildTimeline} from "./timeline/buildTimeline";
import {parseVideoSpec, VideoSpec} from "./schema/spec";

type ConceptProps = {
  spec: VideoSpec;
};

const getAspectSize = (aspect: "9:16" | "16:9"): {width: number; height: number} => {
  if (aspect === "9:16") {
    return {width: 1080, height: 1920};
  }
  return {width: 1920, height: 1080};
};

const calculateConceptMetadata: CalculateMetadataFunction<ConceptProps> = async ({
  props,
}) => {
  const spec = parseVideoSpec(props?.spec ?? defaultBeatSpec);
  const timeline = buildTimeline(spec);
  const size = getAspectSize(spec.meta.aspect);
  return {
    fps: spec.meta.fps,
    width: size.width,
    height: size.height,
    durationInFrames: timeline.totalFrames,
    props: {
      spec,
    },
  };
};

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="ConceptExplainer"
        component={ConceptExplainer}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          spec: parseVideoSpec(defaultBeatSpec),
        }}
        calculateMetadata={calculateConceptMetadata}
      />
      <Composition
        id="GeminiStyleDemo"
        component={GeminiStyleDemo}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: "From Prompt To Product Clarity",
          subtitle:
            "A reusable Remotion component set inspired by Gemini-style motion language.",
          keywords: ["Context", "Reasoning", "Tools", "Draft", "Refine", "Deliver"],
        }}
      />
      <Composition
        id="ExplainerFromSpec"
        component={ExplainerFromSpec}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="SkillExplainer60"
        component={SkillExplainer60}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
