import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

const projectRoot = process.cwd();
const publicDir = path.join(projectRoot, "public");
const demoDir = path.join(publicDir, "demo");

const ensureDir = (dirPath) => {
  fs.mkdirSync(dirPath, {recursive: true});
};

const toRgba = (hex) => {
  const clean = hex.replace("#", "");
  const normalized = clean.length === 3
    ? clean
        .split("")
        .map((c) => c + c)
        .join("")
    : clean;

  return {
    r: Number.parseInt(normalized.slice(0, 2), 16),
    g: Number.parseInt(normalized.slice(2, 4), 16),
    b: Number.parseInt(normalized.slice(4, 6), 16),
    a: 255,
  };
};

const crcTable = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c >>> 0;
  }
  return table;
})();

const crc32 = (buffer) => {
  let c = 0xffffffff;
  for (let i = 0; i < buffer.length; i++) {
    c = crcTable[(c ^ buffer[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
};

const pngChunk = (type, data) => {
  const typeBuffer = Buffer.from(type, "ascii");
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);

  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);

  return Buffer.concat([length, typeBuffer, data, crc]);
};

const buildGradientPng = (width, height, fromHex, toHex) => {
  const from = toRgba(fromHex);
  const to = toRgba(toHex);
  const rowBytes = width * 4 + 1;
  const raw = Buffer.alloc(rowBytes * height);

  for (let y = 0; y < height; y++) {
    const rowOffset = y * rowBytes;
    raw[rowOffset] = 0;

    for (let x = 0; x < width; x++) {
      const tX = x / Math.max(1, width - 1);
      const tY = y / Math.max(1, height - 1);
      const t = Math.min(1, Math.max(0, tX * 0.65 + tY * 0.35));

      const px = rowOffset + 1 + x * 4;
      raw[px] = Math.round(from.r + (to.r - from.r) * t);
      raw[px + 1] = Math.round(from.g + (to.g - from.g) * t);
      raw[px + 2] = Math.round(from.b + (to.b - from.b) * t);
      raw[px + 3] = 255;
    }
  }

  const signature = Buffer.from([
    0x89, 0x50, 0x4e, 0x47,
    0x0d, 0x0a, 0x1a, 0x0a,
  ]);

  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;
  ihdrData[9] = 6;
  ihdrData[10] = 0;
  ihdrData[11] = 0;
  ihdrData[12] = 0;

  const idatData = zlib.deflateSync(raw, {level: 9});

  return Buffer.concat([
    signature,
    pngChunk("IHDR", ihdrData),
    pngChunk("IDAT", idatData),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
};

const buildSineWav = ({
  durationSeconds,
  sampleRate,
  frequency,
}) => {
  const sampleCount = Math.floor(durationSeconds * sampleRate);
  const pcm = Buffer.alloc(sampleCount * 2);

  for (let i = 0; i < sampleCount; i++) {
    const t = i / sampleRate;
    const attack = Math.min(1, i / (sampleRate * 0.01));
    const release = Math.max(0, 1 - i / sampleCount);
    const envelope = attack * release;
    const sample = Math.sin(2 * Math.PI * frequency * t) * 0.45 * envelope;
    pcm.writeInt16LE(Math.round(sample * 32767), i * 2);
  }

  const header = Buffer.alloc(44);
  header.write("RIFF", 0, "ascii");
  header.writeUInt32LE(36 + pcm.length, 4);
  header.write("WAVE", 8, "ascii");
  header.write("fmt ", 12, "ascii");
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(1, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write("data", 36, "ascii");
  header.writeUInt32LE(pcm.length, 40);

  return Buffer.concat([header, pcm]);
};

const writeIfMissing = (filePath, bufferBuilder) => {
  if (fs.existsSync(filePath)) {
    console.log(`exists: ${path.relative(projectRoot, filePath)}`);
    return;
  }

  fs.writeFileSync(filePath, bufferBuilder());
  console.log(`created: ${path.relative(projectRoot, filePath)}`);
};

ensureDir(publicDir);
ensureDir(demoDir);

writeIfMissing(path.join(publicDir, "logo.png"), () =>
  buildGradientPng(512, 512, "#3a84ff", "#21cab7"),
);

writeIfMissing(path.join(demoDir, "img1.png"), () =>
  buildGradientPng(1280, 720, "#0a1530", "#2c5ea8"),
);

writeIfMissing(path.join(demoDir, "img2.png"), () =>
  buildGradientPng(1280, 720, "#0b2734", "#26ab9c"),
);

writeIfMissing(path.join(publicDir, "chime.wav"), () =>
  buildSineWav({durationSeconds: 0.12, sampleRate: 44100, frequency: 1046.5}),
);
