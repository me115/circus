// @ts-nocheck
const fs = require('node:fs');
const path = require('node:path');

const parseArgs = (argv) => {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
};

const toNumber = (v, fallback) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

const words = (text) => `${text ?? ''}`.replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
const normalizeLine = (line, maxWordsPerLine, maxLines) => {
  const ws = words(line);
  const maxWords = Math.max(1, maxWordsPerLine * maxLines);
  if (ws.length <= maxWords) return ws.join(' ');
  return `${ws.slice(0, maxWords).join(' ').replace(/[.,;:!?]+$/, '')}.`;
};

const splitText = (line, segments) => {
  const raw = `${line ?? ''}`.trim();
  if (!raw) return Array.from({length: segments}).map(() => '');
  const sents = raw.split(/(?<=[.!?])\s+/).filter(Boolean);
  if (sents.length >= segments) return sents.slice(0, segments);
  const ws = raw.split(' ');
  const size = Math.max(1, Math.ceil(ws.length / segments));
  return Array.from({length: segments}).map((_, i) => ws.slice(i * size, (i + 1) * size).join(' ').trim() || raw);
};

const resequence = (beats, durationSec) => {
  let cursor = 0;
  const out = beats.map((beat, idx) => {
    const isLast = idx === beats.length - 1;
    const original = Math.max(2.5, toNumber(beat.t1, 0) - toNumber(beat.t0, 0));
    const dur = isLast ? Math.max(2.5, durationSec - cursor) : Math.max(2.5, Math.min(4.0, original));
    const next = {
      ...beat,
      t0: Number(cursor.toFixed(3)),
      t1: Number((cursor + dur).toFixed(3)),
    };
    cursor += dur;
    return next;
  });
  if (out.length > 0) out[out.length - 1].t1 = Number(durationSec.toFixed(3));
  return out;
};

const normalize = (spec, quality) => {
  const cloned = JSON.parse(JSON.stringify(spec ?? {}));
  const limits = quality?.limits ?? {};
  const maxWordsPerLine = toNumber(limits.maxWordsPerLine, 7);
  const maxLines = toNumber(limits.maxLines, 2);
  const targetSec = toNumber(quality?.rhythm?.targetBeatSec, 3.0);
  const maxSec = toNumber(quality?.rhythm?.maxBeatSec, 4.0);
  const minSec = toNumber(quality?.rhythm?.minBeatSec, 2.5);

  let beats = Array.isArray(cloned.beats) ? cloned.beats.map((beat, idx) => ({
    ...beat,
    id: beat.id || `b${String(idx + 1).padStart(2, '0')}`,
    line: `${beat.line ?? beat.text ?? ''}`.trim(),
  })) : [];

  beats = beats.sort((a, b) => toNumber(a.t0, 0) - toNumber(b.t0, 0));

  const hasHook = beats.some((beat) => `${beat.intent ?? ''}` === 'hook_title');
  if (!hasHook) {
    beats.unshift({
      id: 'hook_auto',
      t0: 0,
      t1: 4,
      intent: 'hook_title',
      line: 'Search by meaning, not just keywords.',
    });
  }

  const hasExample = beats.some((beat) => `${beat.intent ?? ''}` === 'example_prompt');
  if (!hasExample) {
    beats.push({
      id: 'example_auto',
      t0: 44,
      t1: 48,
      intent: 'example_prompt',
      line: 'Ask one question, retrieve best answers instantly.',
    });
  }

  const splitBeats = [];
  for (const beat of beats) {
    const duration = Math.max(0.2, toNumber(beat.t1, 0) - toNumber(beat.t0, 0));
    if (duration <= maxSec) {
      splitBeats.push(beat);
      continue;
    }
    const segments = Math.max(2, Math.round(duration / targetSec));
    const per = duration / segments;
    const textParts = splitText(beat.line, segments);
    for (let i = 0; i < segments; i++) {
      splitBeats.push({
        ...beat,
        id: `${beat.id}_s${i + 1}`,
        t0: toNumber(beat.t0, 0) + i * per,
        t1: toNumber(beat.t0, 0) + (i + 1) * per,
        line: textParts[i],
      });
    }
  }

  const merged = [];
  let i = 0;
  while (i < splitBeats.length) {
    const cur = splitBeats[i];
    const dur = Math.max(0.2, toNumber(cur.t1, 0) - toNumber(cur.t0, 0));
    if (dur >= minSec || i === splitBeats.length - 1) {
      merged.push(cur);
      i += 1;
      continue;
    }
    const next = splitBeats[i + 1];
    const mergedDur = Math.max(0.2, toNumber(next.t1, 0) - toNumber(cur.t0, 0));
    if (mergedDur > maxSec + 0.8) {
      merged.push(cur);
      i += 1;
      continue;
    }
    merged.push({
      ...cur,
      id: `${cur.id}_m`,
      t0: cur.t0,
      t1: next.t1,
      line: `${cur.line ?? ''} ${next.line ?? ''}`.trim(),
      intent: cur.intent || next.intent,
    });
    i += 2;
  }

  const durationSec = toNumber(cloned?.meta?.duration_sec ?? cloned?.meta?.durationSec, 60);
  let resequenced = resequence(merged, durationSec).map((beat) => {
    const line = normalizeLine(beat.line ?? beat.text ?? '', maxWordsPerLine, maxLines);
    return {...beat, line, text: line};
  });

  cloned.beats = resequenced;
  cloned.meta = cloned.meta || {};
  cloned.meta.duration_sec = durationSec;
  cloned.meta.durationSec = durationSec;
  return cloned;
};

const main = () => {
  const args = parseArgs(process.argv.slice(2));
  const specPath = path.resolve(process.cwd(), args.spec ?? 'src/specs/skill.timeline.json');
  const qualityPath = path.resolve(process.cwd(), args.quality ?? 'src/config/quality.json');
  const outPath = path.resolve(process.cwd(), args.out ?? 'out/spec.normalized.json');

  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const quality = JSON.parse(fs.readFileSync(qualityPath, 'utf8'));

  const normalized = normalize(spec, quality);
  fs.mkdirSync(path.dirname(outPath), {recursive: true});
  fs.writeFileSync(outPath, `${JSON.stringify(normalized, null, 2)}\n`, 'utf8');
  console.log(`Normalized storyboard: ${path.relative(process.cwd(), outPath)}`);
};

main();
