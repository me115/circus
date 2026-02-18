import {QualityConfig, SkillTimelineSpec} from "../specs/types";
import {SkillExplainer60} from "./SkillExplainer60";

type ExplainerFromSpecProps = {
  spec?: SkillTimelineSpec;
  quality?: QualityConfig;
};

export const ExplainerFromSpec = ({spec, quality}: ExplainerFromSpecProps) => {
  return <SkillExplainer60 spec={spec} quality={quality} />;
};
