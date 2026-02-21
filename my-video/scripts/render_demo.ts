// @ts-nocheck
const fs = require("node:fs");
const path = require("node:path");
const {spawnSync} = require("node:child_process");
const {bundle} = require("@remotion/bundler");
const {renderMedia, selectComposition} = require("@remotion/renderer");

const parseArgs = (argv) => {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
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

const ensureDir = (dirPath) => fs.mkdirSync(dirPath, {recursive: true});
const readJson = (filePath) => JSON.parse(fs.readFileSync(filePath, "utf8"));

const runNodeScript = (scriptPath, scriptArgs) => {
  const result = spawnSync("node", [scriptPath, ...scriptArgs], {
    cwd: process.cwd(),
    stdio: "inherit",
  });
  if (result.status !== 0) {
    throw new Error(`Failed command: node ${scriptPath} ${scriptArgs.join(" ")}`);
  }
};

const main = async () => {
  const args = parseArgs(process.argv.slice(2));
  const specPath = path.resolve(process.cwd(), args.spec ?? "src/beats/vector-db.beats.json");
  const outPath = path.resolve(process.cwd(), args.out ?? "out/vector-db.mp4");
  const manifestPath = path.resolve(
    process.cwd(),
    args.manifest ?? "out/vector-db.manifest.json",
  );
  const compositionId = args.composition ?? "ConceptExplainer";

  if (!fs.existsSync(specPath)) {
    throw new Error(`Spec not found: ${specPath}`);
  }

  ensureDir(path.dirname(outPath));
  ensureDir(path.dirname(manifestPath));

  const spec = readJson(specPath);
  const inputProps = {spec};

  const serveUrl = await bundle({
    entryPoint: path.join(process.cwd(), "src/index.ts"),
    webpackOverride: (config) => config,
  });

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

  runNodeScript(path.join(process.cwd(), "scripts/emit_beats_manifest.ts"), [
    "--spec",
    path.relative(process.cwd(), specPath),
    "--out",
    path.relative(process.cwd(), manifestPath),
  ]);

  console.log(`Rendered demo: ${path.relative(process.cwd(), outPath)}`);
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
