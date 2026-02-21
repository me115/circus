import {VideoBeat} from "../schema/spec";

export type SceneProps = {
  beat: VideoBeat;
  durationInFrames: number;
  aspect: "9:16" | "16:9";
};
