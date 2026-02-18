import {cookbook, motionkit} from "../style";
import {BeatScene, SceneLayer, SkillTimelineSpec, TimelineBeat} from "../specs/types";

const parseWords = (text: string): string[] => {
  return text
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean);
};

const stopwords = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "by",
  "for",
  "from",
  "in",
  "into",
  "it",
  "of",
  "on",
  "or",
  "that",
  "the",
  "to",
  "with",
]);

const pickMeaningfulWord = (text: string, fallback: string): string => {
  const ws = parseWords(text);
  for (const token of ws) {
    const cleaned = token.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
    if (cleaned.length >= 3 && !stopwords.has(cleaned)) {
      return token;
    }
  }
  return fallback;
};

const shortHeadline = (text: string, maxWords: number): string => {
  const words = parseWords(text);
  if (words.length <= maxWords) {
    return words.join(" ");
  }
  return words.slice(0, maxWords).join(" ");
};

const pickBrollVariant = (intent: string): string => {
  const key = intent.toLowerCase();
  if (key.includes("problem")) return "KeywordVsMeaningBroll";
  if (key.includes("definition")) return "EmbeddingsBroll";
  if (key.includes("analogy")) return "SemanticOrbitBroll";
  if (key.includes("how_steps") || key.includes("pipeline")) return "RetrieveThenAnswerBroll";
  if (key.includes("example")) return "NearestNeighborsBroll";
  if (key.includes("recap")) return "SearchIconBroll";
  return "SemanticOrbitBroll";
};

const toSceneLayer = (layerName: string, beat: TimelineBeat): SceneLayer => {
  const line = `${beat.line ?? beat.text ?? ""}`.trim();
  if (layerName === "HeroTitle") {
    const headline = shortHeadline(line, 7);
    const subtitle = parseWords(line).length > 9 ? shortHeadline(line, 9) : line;
    return {
      type: "HeroTitle",
      props: {
        title: headline,
        subtitle,
        enterDelayFrames: 2,
      },
    };
  }

  if (layerName === "BeforeAfter") {
    return {
      type: "BeforeAfter",
      props: {
        beforeTitle: "Keyword Search",
        afterTitle: "Vector Search",
        beforeBullets: ["exact words only", "synonyms missed", "word mismatch"],
        afterBullets: ["intent match", "semantic recall", "nearby meaning"],
        marker: "→",
      },
    };
  }

  if (layerName === "Stepper3") {
    return {
      type: "Stepper3",
      props: {
        steps: [
          {title: "Step 1", text: "Chunk content"},
          {title: "Step 2", text: "Embed chunks"},
          {title: "Step 3", text: "Search nearest"},
        ],
      },
    };
  }

  if (layerName === "MediaFrame") {
    return {
      type: "MediaFrame",
      props: {
        kind: "react",
        reactContent: pickBrollVariant(beat.intent),
        fallbackReactContent: "PipelineBlocksBroll",
      },
    };
  }

  if (layerName === "LowerThird") {
    return {
      type: "LowerThird",
      props: {
        title: shortHeadline(line, 7),
        source: "",
        durationSec: Math.max(2.5, (beat.t1 ?? 0) - (beat.t0 ?? 0)),
        align: "left",
      },
    };
  }

  if (layerName === "PromptAnswerCard") {
    return {
      type: "PromptAnswerCard",
      props: {
        prompt: line,
        answer: "Top relevant results from semantic retrieval.",
        appearMode: "slideUp",
        typing: {enabled: true, cps: 20},
      },
    };
  }

  if (layerName === "KineticWords") {
    const kineticWords = parseWords(shortHeadline(line, 8));
    const emphasisIdx = Math.max(
      0,
      kineticWords.findIndex((w) => {
        const cleaned = w.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
        return cleaned.length >= 3 && !stopwords.has(cleaned);
      }),
    );
    return {
      type: "KineticWords",
      props: {
        words: kineticWords,
        mode: "pop",
        emphasize: [Math.min(2, emphasisIdx)],
      },
    };
  }

  if (layerName === "Callout") {
    return {
      type: "Callout",
      props: {
        keyword: pickMeaningfulWord(line, "embedding"),
        description: shortHeadline(line, 8),
      },
    };
  }

  if (layerName === "LogoOutro") {
    return {
      type: "LogoOutro",
      props: {
        logoSrc: "logo.png",
        tagline: shortHeadline(line, 10),
        chimeSrc: "chime.wav",
      },
    };
  }

  return {
    type: "KineticWords",
    props: {words: parseWords(shortHeadline(line, 6)), mode: "pop", emphasize: [0]},
  };
};

const resolveScene = (beat: TimelineBeat): BeatScene => {
  if (Array.isArray(beat.scene?.layers) && beat.scene?.layers.length) {
    return beat.scene as BeatScene;
  }

  const recipe = cookbook.intents[beat.intent] ?? cookbook.intents.definition_card;
  const layers = recipe.layers.map((layerName) => toSceneLayer(layerName, beat));
  return {
    backdrop: recipe.backdrop ?? {preset: "gemini", animate: true, intensity: 0.8},
    layers,
  };
};

const constrainTransitionTypes = (beats: TimelineBeat[]): TimelineBeat[] => {
  const allowed = new Set(motionkit.recipes.transition.types);
  const defaultType = motionkit.recipes.transition.default;
  const normalized = beats.map((beat, idx) => {
    const current = `${beat.transitionType ?? beat.transition_type ?? ""}`.trim();
    if (allowed.has(current as "fade" | "slide")) {
      return {...beat, transitionType: current, transition_type: current};
    }
    const fallback = idx % 2 === 0 ? "fade" : "slide";
    const chosen = allowed.has(fallback as "fade" | "slide") ? fallback : defaultType;
    return {...beat, transitionType: chosen, transition_type: chosen};
  });

  const seen = new Set<string>();
  return normalized.map((beat) => {
    const key = `${beat.transitionType}`;
    if (seen.size < motionkit.limits.maxTransitionTypes || seen.has(key)) {
      seen.add(key);
      return beat;
    }
    return {...beat, transitionType: defaultType, transition_type: defaultType};
  });
};

const constrainMotionRecipes = (beats: TimelineBeat[]): TimelineBeat[] => {
  const allowedRecipes = ["entrance", "emphasis", "transition"];
  const seen = new Set<string>();
  return beats.map((beat, idx) => {
    const current = `${beat.motionRecipe ?? beat.motion_recipe ?? ""}`.trim();
    let chosen = current;
    if (!allowedRecipes.includes(chosen)) {
      chosen = allowedRecipes[idx % allowedRecipes.length];
    }
    if (seen.size >= motionkit.limits.maxMotionRecipes && !seen.has(chosen)) {
      chosen = allowedRecipes[0];
    }
    seen.add(chosen);
    return {...beat, motionRecipe: chosen, motion_recipe: chosen};
  });
};

export const routeStoryboard = (input: SkillTimelineSpec): SkillTimelineSpec => {
  const spec = JSON.parse(JSON.stringify(input ?? {})) as SkillTimelineSpec;
  const beats = Array.isArray(spec.beats) ? spec.beats : [];

  let routed = beats.map((beat, idx) => {
    const resolvedText = `${beat.line ?? beat.text ?? ""}`.trim();
    const recipe = cookbook.intents[beat.intent];
    const durationSec = Math.max(0.5, (beat.t1 ?? 0) - (beat.t0 ?? 0));
    const motionRecipe = durationSec <= 3 ? "entrance" : recipe?.layers.includes("KineticWords") ? "emphasis" : "transition";
    return {
      ...beat,
      id: beat.id || `b${String(idx + 1).padStart(2, "0")}`,
      line: resolvedText,
      text: resolvedText,
      scene: resolveScene(beat),
      transitionType: beat.transitionType ?? beat.transition_type ?? (idx % 2 === 0 ? "fade" : "slide"),
      transition_type: beat.transitionType ?? beat.transition_type ?? (idx % 2 === 0 ? "fade" : "slide"),
      motionRecipe: beat.motionRecipe ?? beat.motion_recipe ?? motionRecipe,
      motion_recipe: beat.motionRecipe ?? beat.motion_recipe ?? motionRecipe,
    } as TimelineBeat;
  });

  routed = constrainTransitionTypes(routed);
  routed = constrainMotionRecipes(routed);
  spec.beats = routed;
  return spec;
};
