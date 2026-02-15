// @ts-nocheck
const fs = require("node:fs");
const path = require("node:path");
const {spawnSync} = require("node:child_process");
const {bundle} = require("@remotion/bundler");
const {renderMedia, selectComposition} = require("@remotion/renderer");

const DEFAULT_SPEC = "src/specs/skill.timeline.json";
const DEFAULT_QUALITY = "src/config/quality.json";
const DEFAULT_OUT = "out/video.mp4";
const DEFAULT_MANIFEST = "out/manifest.json";

const parseArgs = (argv) => {
  const args = {};

  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      continue;
    }

    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
      continue;
    }

    args[key] = next;
    i += 1;
  }

  return args;
};

const ensureDir = (dirPath) => {
  fs.mkdirSync(dirPath, {recursive: true});
};

const readJson = (filePath) => {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
};

const runNodeScript = (scriptPath, scriptArgs) => {
  const result = spawnSync("node", [scriptPath, ...scriptArgs], {
    cwd: process.cwd(),
    stdio: "inherit",
  });

  if (result.status !== 0) {
    throw new Error(`Command failed: node ${scriptPath} ${scriptArgs.join(" ")}`);
  }
};

const maybeNormalizeAudio = (videoPath, quality) => {
  if (!quality?.postAudioNormalize?.enabled) {
    return;
  }

  const tmpPath = `${videoPath}.norm.mp4`;
  const targetLufs = quality?.audio?.targetLUFS ?? -16;
  const targetTp = quality?.audio?.maxTruePeakDbTP ?? -1;
  const af = `loudnorm=I=${targetLufs}:TP=${targetTp}:LRA=11`;

  const result = spawnSync(
    "ffmpeg",
    [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      videoPath,
      "-af",
      af,
      "-c:v",
      "copy",
      "-c:a",
      "aac",
      tmpPath,
    ],
    {cwd: process.cwd(), encoding: "utf8"},
  );

  if (result.status !== 0) {
    console.warn("Audio normalization skipped because ffmpeg failed.");
    return;
  }

  fs.renameSync(tmpPath, videoPath);
};

const main = async () => {
  const args = parseArgs(process.argv.slice(2));

  const specPath = path.resolve(process.cwd(), args.spec ?? DEFAULT_SPEC);
  const qualityPath = path.resolve(process.cwd(), args.quality ?? DEFAULT_QUALITY);
  const outPath = path.resolve(process.cwd(), args.out ?? DEFAULT_OUT);
  const manifestPath = path.resolve(process.cwd(), args.manifest ?? DEFAULT_MANIFEST);

  if (!fs.existsSync(specPath)) {
    throw new Error(`Spec file not found: ${specPath}`);
  }

  if (!fs.existsSync(qualityPath)) {
    throw new Error(`Quality config not found: ${qualityPath}`);
  }

  ensureDir(path.dirname(outPath));
  ensureDir(path.dirname(manifestPath));

  runNodeScript(path.join(process.cwd(), "scripts/emit_manifest.ts"), [
    "--spec",
    path.relative(process.cwd(), specPath),
    "--quality",
    path.relative(process.cwd(), qualityPath),
    "--out",
    path.relative(process.cwd(), manifestPath),
  ]);

  const spec = readJson(specPath);
  const quality = readJson(qualityPath);

  const inputProps = {
    spec,
    quality,
    specPath: path.relative(process.cwd(), specPath),
  };

  const entryPoint = path.join(process.cwd(), "src/index.ts");
  const serveUrl = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });

  const compositionId = args.composition ?? spec?.meta?.compositionId ?? "SkillExplainer60";

  const composition = await selectComposition({
    serveUrl,
    id: compositionId,
    inputProps,
  });

  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    audioCodec: "aac",
    outputLocation: outPath,
    inputProps,
    overwrite: true,
    imageFormat: "jpeg",
  });

  maybeNormalizeAudio(outPath, quality);

  console.log(`Rendered: ${path.relative(process.cwd(), outPath)}`);
};

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
