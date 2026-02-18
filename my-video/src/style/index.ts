import stylekitData from "./stylekit.json";
import motionkitData from "./motionkit.json";
import cookbookData from "./cookbook.json";
import {Cookbook, MotionKit, StyleKit} from "./types";

export const stylekit: StyleKit = stylekitData as StyleKit;
export const motionkit: MotionKit = motionkitData as MotionKit;
export const cookbook: Cookbook = cookbookData as Cookbook;
