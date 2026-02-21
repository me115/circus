const CJK_RE = /[\u3400-\u9fff]/;

const isCjk = (text: string): boolean => {
  return CJK_RE.test(text);
};

const tokenize = (text: string): string[] => {
  const normalized = text.trim().replace(/\s+/g, " ");
  if (!normalized) {
    return [];
  }
  if (isCjk(normalized)) {
    return normalized.split("").filter((ch) => ch.trim().length > 0);
  }
  return normalized.split(" ");
};

type WrapOptions = {
  maxCharsPerLine: number;
  maxLines: number;
};

export type WrappedText = {
  lines: string[];
  overflow: boolean;
};

export const wrapText = (text: string, options: WrapOptions): WrappedText => {
  const units = tokenize(text);
  const lines: string[] = [];
  const maxChars = Math.max(4, options.maxCharsPerLine);
  const maxLines = Math.max(1, options.maxLines);
  const cjk = isCjk(text);

  let cursor: string[] = [];
  const flush = () => {
    if (cursor.length === 0) {
      return;
    }
    lines.push(cjk ? cursor.join("") : cursor.join(" "));
    cursor = [];
  };

  units.forEach((unit) => {
    const candidate = cjk ? [...cursor, unit].join("") : [...cursor, unit].join(" ");
    if (candidate.length <= maxChars) {
      cursor.push(unit);
      return;
    }
    flush();
    cursor.push(unit);
  });
  flush();

  if (lines.length <= maxLines) {
    return {
      lines,
      overflow: false,
    };
  }

  return {
    lines: lines.slice(0, maxLines),
    overflow: true,
  };
};
