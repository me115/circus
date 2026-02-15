import "./index.css";
import {Composition} from "remotion";
import {GeminiStyleDemo} from "./compositions/GeminiStyleDemo";
import {SkillExplainer60} from "./compositions/SkillExplainer60";

export const RemotionRoot = () => {
  return (
    <>
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
