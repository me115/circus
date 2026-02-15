import {TransitionSeries, linearTiming} from "@remotion/transitions";
import {fade} from "@remotion/transitions/fade";
import {slide} from "@remotion/transitions/slide";
import {AbsoluteFill, Sequence} from "remotion";
import {BeatCut} from "../components/BeatCut";
import {BrandBackdrop} from "../components/BrandBackdrop";
import {HeroTitle} from "../components/HeroTitle";
import {KineticWords} from "../components/KineticWords";
import {LogoOutro} from "../components/LogoOutro";
import {LowerThird} from "../components/LowerThird";
import {MediaFrame} from "../components/MediaFrame";
import {PromptAnswerCard} from "../components/PromptAnswerCard";
import {tokens} from "../theme/tokens";
import {assets, withFallbackAsset} from "../utils/assets";
import {createBeatGrid} from "../utils/beat";

type GeminiStyleDemoProps = {
  title?: string;
  subtitle?: string;
  keywords?: string[];
  image1Src?: string;
  image2Src?: string;
  logoSrc?: string;
  tagline?: string;
};

type MontageScene = {
  words: string[];
  emphasize: number[];
  source: string;
  src: string;
};

const montageSceneDuration = 103;
const montageTransitionDuration = 11;

export const GeminiStyleDemo = ({
  title = "From Prompt To Product Clarity",
  subtitle = "A reusable Remotion component set inspired by Gemini-style motion language.",
  keywords = ["Context", "Reasoning", "Tools", "Draft", "Refine", "Deliver"],
  image1Src,
  image2Src,
  logoSrc,
  tagline = "Build faster stories with frame-accurate motion.",
}: GeminiStyleDemoProps) => {
  const primaryImage = withFallbackAsset(image1Src, assets.demoImage1);
  const secondaryImage = withFallbackAsset(image2Src, assets.demoImage2);
  const outroLogo = withFallbackAsset(logoSrc, assets.logo);

  const montageScenes: MontageScene[] = [
    {
      words: ["Understand", "the", "real", "question"],
      emphasize: [0, 3],
      source: "Beat 01",
      src: primaryImage,
    },
    {
      words: ["Map", "constraints", "before", "writing"],
      emphasize: [1],
      source: "Beat 02",
      src: secondaryImage,
    },
    {
      words: ["Draft", "options", "then", "compare"],
      emphasize: [0, 3],
      source: "Beat 03",
      src: primaryImage,
    },
    {
      words: ["Use", "tools", "to", "verify", "facts"],
      emphasize: [1, 4],
      source: "Beat 04",
      src: secondaryImage,
    },
    {
      words: ["Compress", "noise", "highlight", "signal"],
      emphasize: [2, 3],
      source: "Beat 05",
      src: primaryImage,
    },
    {
      words: ["Polish", "timing", "for", "clarity"],
      emphasize: [0, 1],
      source: "Beat 06",
      src: secondaryImage,
    },
    {
      words: ["Keep", "style", "consistent", "end", "to", "end"],
      emphasize: [2],
      source: "Beat 07",
      src: primaryImage,
    },
    {
      words: ["Ship", "the", "story", "with", "confidence"],
      emphasize: [0, 4],
      source: "Beat 08",
      src: secondaryImage,
    },
  ];

  const beatGrid = createBeatGrid(0, 750, 15);

  return (
    <AbsoluteFill style={{backgroundColor: tokens.colors.background}}>
      <BrandBackdrop preset="gemini" intensity={0.95} animate safePadding={72} />

      <Sequence durationInFrames={170}>
        <HeroTitle
          title={title}
          subtitle={subtitle}
          enterDelayFrames={6}
          align="center"
          accentWord="Product"
        />
      </Sequence>

      <Sequence from={150} durationInFrames={320}>
        <AbsoluteFill style={{padding: 120}}>
          <MediaFrame
            kind="image"
            src={primaryImage}
            startFrame={0}
            durationInFrames={300}
            kenBurns={{
              enabled: true,
              fromScale: 1.01,
              toScale: 1.09,
              fromX: -10,
              toX: 8,
              fromY: -6,
              toY: 5,
            }}
          />
        </AbsoluteFill>
        <AbsoluteFill
          style={{
            justifyContent: "flex-end",
            paddingLeft: 150,
            paddingRight: 150,
            paddingBottom: 220,
          }}
        >
          <KineticWords
            words={keywords}
            startFrame={22}
            wordStagger={7}
            mode="pop"
            emphasize={[1, 4]}
          />
        </AbsoluteFill>
        <LowerThird
          title="Kinetic words synced to speech rhythm"
          source="GeminiStyleDemo / Section 02"
          startFrame={16}
          durationInFrames={280}
        />
      </Sequence>

      <Sequence from={450} durationInFrames={750}>
        <TransitionSeries>
          {montageScenes.map((scene, idx) => (
            <TransitionSeries.Sequence
              key={`scene-${idx}`}
              durationInFrames={montageSceneDuration}
            >
              <AbsoluteFill style={{padding: 120}}>
                <MediaFrame
                  kind="image"
                  src={scene.src}
                  startFrame={0}
                  durationInFrames={montageSceneDuration}
                  kenBurns={{
                    enabled: true,
                    fromScale: 1.03,
                    toScale: 1.12,
                    fromX: idx % 2 === 0 ? -6 : 8,
                    toX: idx % 2 === 0 ? 8 : -4,
                    fromY: -6,
                    toY: 4,
                  }}
                />
              </AbsoluteFill>
              <AbsoluteFill
                style={{
                  justifyContent: "flex-end",
                  paddingLeft: 160,
                  paddingRight: 160,
                  paddingBottom: 210,
                }}
              >
                <KineticWords
                  words={scene.words}
                  startFrame={10}
                  wordStagger={6}
                  mode="slide"
                  emphasize={scene.emphasize}
                />
              </AbsoluteFill>
              <LowerThird
                title="Montage beat"
                source={scene.source}
                startFrame={6}
                durationInFrames={88}
                align={idx % 2 === 0 ? "left" : "right"}
              />
            </TransitionSeries.Sequence>
          ))
            .flatMap((sceneEl, idx, arr) => {
              if (idx === arr.length - 1) {
                return [sceneEl];
              }

              return [
                sceneEl,
                <TransitionSeries.Transition
                  key={`transition-${idx}`}
                  timing={linearTiming({durationInFrames: montageTransitionDuration})}
                  presentation={
                    idx % 2 === 0
                      ? fade({shouldFadeOutExitingScene: true})
                      : slide({direction: "from-right"})
                  }
                />,
              ];
            })}
        </TransitionSeries>

        <BeatCut
          beatsInFrames={beatGrid}
          flashDurationFrames={3}
          flashOpacity={0.22}
          shake={{enabled: true, amp: 3.4}}
        />
      </Sequence>

      <Sequence from={1200} durationInFrames={300}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            paddingLeft: 160,
            paddingRight: 160,
          }}
        >
          <PromptAnswerCard
            prompt="Can you explain this launch plan clearly and make it production-ready?"
            answer="Absolutely. I will structure the narrative into beats, keep transitions consistent, and align every visual with timing tokens so the output stays reusable."
            startFrame={18}
            appearMode="slideUp"
            showCursor
            typing={{enabled: true, cps: 32}}
          />
        </AbsoluteFill>
        <LowerThird
          title="Prompt / Answer block with typing cursor"
          source="GeminiStyleDemo / Section 04"
          startFrame={16}
          durationInFrames={260}
        />
      </Sequence>

      <LogoOutro
        logoSrc={outroLogo}
        tagline={tagline}
        startFrame={1500}
        durationInFrames={300}
        chimeSrc={assets.chime}
      />
    </AbsoluteFill>
  );
};
