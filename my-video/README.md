# Remotion video

<p align="center">
  <a href="https://github.com/remotion-dev/logo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-dark.apng">
      <img alt="Animated Remotion Logo" src="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-light.gif">
    </picture>
  </a>
</p>

Welcome to your Remotion project!

## Commands

**Install Dependencies**

```console
npm i
```

**Start Preview**

```console
npm run dev
# or
npm start
```

**Render video**

```console
npm run render
```

**Upgrade Remotion**

```console
npx remotion upgrade
```

## Docs

Get started with Remotion by reading the [fundamentals page](https://www.remotion.dev/docs/the-fundamentals).

## Help

We provide help on our [Discord server](https://discord.gg/6VzzNDwUwV).

## Issues

Found an issue with Remotion? [File an issue here](https://github.com/remotion-dev/remotion/issues/new).

## License

Note that for some entities a company license is needed. [Read the terms here](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md).

## GeminiStyleDemo

### Open Studio

```console
npm start
```

Then select composition `GeminiStyleDemo`.

### Replace Assets

- Replace logo at `public/logo.png`
- Replace outro sound at `public/chime.wav`
- Demo placeholders are at `public/demo/img1.png` and `public/demo/img2.png`
- If `public/chime.wav` is missing, run:

```console
npm run generate:assets
```

This generates a minimal 0.12s sine-wave chime placeholder. Replace with a real sound effect when needed.

### Render MP4

```console
npm run render
```

Output path: `out/gemini-style-demo.mp4`

### Component Library

- `BrandBackdrop`: `preset`, `intensity`, `animate`, `safePadding`
- `HeroTitle`: `title`, `subtitle`, `align`, `enterDelayFrames`, `accentWord`
- `KineticWords`: `words`, `startFrame`, `wordStagger`, `mode`, `emphasize`
- `PromptAnswerCard`: `prompt`, `answer`, `startFrame`, `appearMode`, `showCursor`, `typing`
- `MediaFrame`: `kind`, `src`, `startFrame`, `durationInFrames`, `cornerRadius`, `border`, `kenBurns`
- `BeatCut`: `beatsInFrames`, `flashDurationFrames`, `flashOpacity`, `shake`
- `LowerThird`: `title`, `source`, `startFrame`, `durationInFrames`, `align`
- `LogoOutro`: `logoSrc`, `tagline`, `startFrame`, `durationInFrames`, `chimeSrc`

## QA Pipeline

Automated quality evaluation and iterative optimization are documented in:

- `qa/README_QA.md`

Key commands:

```console
npm run render:skill
npm run qa:eval
npm run qa:loop
```
