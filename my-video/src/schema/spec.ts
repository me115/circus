import {z} from "zod";

export const aspectSchema = z.enum(["9:16", "16:9"]);

export const beatTypeSchema = z.enum([
  "hook",
  "definition",
  "mental_model",
  "diagram_steps",
  "misconception",
  "recap",
  "outro",
]);

const pointNodeSchema = z.object({
  id: z.string().min(1),
  text: z.string().min(1),
  x: z.number().finite(),
  y: z.number().finite(),
});

const edgeSchema = z.object({
  from: z.string().min(1),
  to: z.string().min(1),
});

const stepSchema = z.object({
  label: z.string().min(1),
  nodes: z.array(pointNodeSchema).min(1),
  edges: z.array(edgeSchema).default([]),
  focusNodeIds: z.array(z.string()).default([]),
});

const markerSchema = z.object({
  id: z.string().min(1),
  startSec: z.number().nonnegative(),
  endSec: z.number().nonnegative().optional(),
  beatId: z.string().optional(),
});

export const beatSchema = z.object({
  id: z.string().min(1),
  type: beatTypeSchema,
  durationSec: z.number().positive().optional(),
  markerId: z.string().optional(),
  title: z.string().optional(),
  subtitle: z.string().optional(),
  onScreen: z.array(z.string()).default([]),
  emphasis: z.array(z.string()).default([]),
  steps: z.array(stepSchema).default([]),
});

export const videoSpecSchema = z.object({
  meta: z.object({
    title: z.string().default("Concept Explainer"),
    aspect: aspectSchema.default("16:9"),
    fps: z.number().int().positive().default(30),
  }),
  audio: z.object({
    src: z.string().optional(),
    startSec: z.number().nonnegative().default(0),
    markers: z.array(markerSchema).optional(),
  }).optional(),
  beats: z.array(beatSchema).min(1),
});

export type VideoSpec = z.infer<typeof videoSpecSchema>;
export type VideoBeat = z.infer<typeof beatSchema>;
export type VideoMarker = z.infer<typeof markerSchema>;
export type DiagramStep = z.infer<typeof stepSchema>;
export type DiagramNode = z.infer<typeof pointNodeSchema>;
export type DiagramEdge = z.infer<typeof edgeSchema>;

export const parseVideoSpec = (input: unknown): VideoSpec => {
  return videoSpecSchema.parse(input);
};
