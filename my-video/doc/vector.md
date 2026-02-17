下面给你一个**Remotion-only 的完整故事板（Timeline Spec）**，用于你的框架端到端验证：
输入这份 spec → 生成视频 → 用你的评测框架自我迭代直到达标。

我同时给出：

1. **结构化目标**
2. **60s 英文口播脚本（expected_script）**
3. **Remotion-only Timeline Spec JSON（0–60s，15个 beat，每个 4s）**
4. **如何接入你的 render + qa loop**

---

## 1) 结构化目标（给系统用）

```json
{
  "topic": "What is a vector database?",
  "audience": "Non-technical general audience",
  "tone": "Easy, friendly, fast-paced",
  "duration_sec": 60,
  "format": "B-roll + voiceover + kinetic captions (Remotion only)",
  "key_points": [
    "Traditional DB matches exact words; meaning mismatch happens",
    "Vector DB stores meaning as vectors (embeddings)",
    "Similar meanings are close in vector space",
    "Query becomes a vector; nearest neighbors retrieved",
    "Use cases: semantic search, chatbots, RAG for LLMs"
  ],
  "visual_style": "Minimal tech, clean, consistent motion recipes, 1-2 transition types"
}
```

---

## 2) 60s 口播脚本（保存为 `qa/expected_script.txt`）

```text
Ever searched by meaning, not keywords? That’s where vector databases shine.
Traditional databases match exact words. If you type “puppy”, they might miss “dog”.
A vector database stores content as numbers that represent meaning, called vectors.
Think of it like a map: similar ideas end up close together.
First, you break text, images, or audio into chunks.
An AI model turns each chunk into a vector, also called an embedding.
The database stores those vectors with links back to the original content.
When you ask a question, your question becomes a vector too.
Then it finds the nearest vectors, the closest meanings, super fast.
Ask “How do I reset my password?” and it finds relevant help articles even if the wording differs.
That powers semantic search, chatbots, and “ask your docs” tools.
It also helps LLMs: retrieve the right facts before answering, so fewer hallucinations.
Use it whenever you care about meaning: support tickets, notes, and product catalogs.
So: a vector database stores meaning as vectors, and searches by closeness.
Keywords find matches. Vectors find intent.
```

---

## 3) Remotion-only 故事板（Timeline Spec JSON）

> 保存为 `src/specs/vector_db.timeline.json`
> 说明：里面的 `reactContent` 是“程序化B-roll组件名”。如果你还没实现，可先都映射到你已有的 `PipelineBlocksBroll/SearchIconBroll/DashboardIconsBroll` 或简单占位。

```json
{
  "meta": {
    "title": "What is a Vector Database?",
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "duration_sec": 60,
    "style_preset": "gemini_minimal_tech"
  },
  "audio": {
    "src": "tts/vector_db_60s.wav",
    "startSec": 0
  },
  "beats": [
    {
      "id": "b01",
      "t0": 0,
      "t1": 4,
      "line": "Ever searched by meaning, not keywords?",
      "intent": "hook",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.9 },
        "layers": [
          { "type": "HeroTitle", "props": { "title": "Vector Database", "subtitle": "Search by meaning", "enterDelayFrames": 8 } }
        ]
      }
    },
    {
      "id": "b02",
      "t0": 4,
      "t1": 8,
      "line": "Traditional databases match exact words.",
      "intent": "problem",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.7 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "KeywordVsMeaningBroll", "fallbackReactContent": "DashboardIconsBroll" } },
          { "type": "LowerThird", "props": { "title": "Keywords ≠ Meaning", "source": "", "durationSec": 4, "align": "left" } }
        ]
      }
    },
    {
      "id": "b03",
      "t0": 8,
      "t1": 12,
      "line": "A vector database stores meaning as vectors.",
      "intent": "definition",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.65 },
        "layers": [
          { "type": "HeroTitle", "props": { "title": "Store meaning as numbers", "subtitle": "Vectors (embeddings)", "enterDelayFrames": 0 } }
        ]
      }
    },
    {
      "id": "b04",
      "t0": 12,
      "t1": 16,
      "line": "Think of a map: similar ideas end up close.",
      "intent": "analogy",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.65 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "VectorMapBroll", "fallbackReactContent": "PipelineBlocksBroll" } },
          { "type": "KineticWords", "props": { "words": ["Similar", "=", "Closer"], "mode": "pop", "emphasize": [2], "startFrameOffset": 6 } }
        ]
      }
    },
    {
      "id": "b05",
      "t0": 16,
      "t1": 20,
      "line": "First, split content into chunks.",
      "intent": "step1",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.6 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "ChunksBroll", "fallbackReactContent": "PipelineBlocksBroll" } },
          { "type": "LowerThird", "props": { "title": "Step 1: Chunk", "source": "", "durationSec": 4, "align": "left" } }
        ]
      }
    },
    {
      "id": "b06",
      "t0": 20,
      "t1": 24,
      "line": "An AI turns each chunk into an embedding.",
      "intent": "step2",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.6 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "EmbeddingsBroll", "fallbackReactContent": "PipelineBlocksBroll" } },
          { "type": "LowerThird", "props": { "title": "Step 2: Embed", "source": "", "durationSec": 4, "align": "left" } }
        ]
      }
    },
    {
      "id": "b07",
      "t0": 24,
      "t1": 28,
      "line": "Store vectors with links to the original content.",
      "intent": "step3",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.58 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "StoreAndLinkBroll", "fallbackReactContent": "DashboardIconsBroll" } },
          { "type": "LowerThird", "props": { "title": "Step 3: Store + Link", "source": "", "durationSec": 4, "align": "left" } }
        ]
      }
    },
    {
      "id": "b08",
      "t0": 28,
      "t1": 32,
      "line": "Your question becomes a vector too.",
      "intent": "query_embed",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.58 },
        "layers": [
          { "type": "PromptAnswerCard", "props": { "prompt": "User question", "answer": "→ query embedding", "appearMode": "slideUp", "typing": { "enabled": false } } }
        ]
      }
    },
    {
      "id": "b09",
      "t0": 32,
      "t1": 36,
      "line": "Find nearest vectors, super fast.",
      "intent": "nearest_neighbor",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.58 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "NearestNeighborsBroll", "fallbackReactContent": "SearchIconBroll" } },
          { "type": "KineticWords", "props": { "words": ["Nearest", "=", "Best match"], "mode": "slide", "startFrameOffset": 6 } }
        ]
      }
    },
    {
      "id": "b10",
      "t0": 36,
      "t1": 40,
      "line": "Example: reset password → relevant articles.",
      "intent": "example",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.56 },
        "layers": [
          { "type": "PromptAnswerCard", "props": { "prompt": "How do I reset my password?", "answer": "Top relevant help docs", "typing": { "enabled": true, "cps": 22 } } }
        ]
      }
    },
    {
      "id": "b11",
      "t0": 40,
      "t1": 44,
      "line": "This powers semantic search and chatbots.",
      "intent": "usecases",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.56 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "UseCasesIconsBroll", "fallbackReactContent": "DashboardIconsBroll" } },
          { "type": "LowerThird", "props": { "title": "Use cases: Search • Chat • Docs Q&A", "source": "", "durationSec": 4, "align": "left" } }
        ]
      }
    },
    {
      "id": "b12",
      "t0": 44,
      "t1": 48,
      "line": "LLMs retrieve facts first, fewer hallucinations.",
      "intent": "rag",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.56 },
        "layers": [
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "RetrieveThenAnswerBroll", "fallbackReactContent": "PipelineBlocksBroll" } },
          { "type": "KineticWords", "props": { "words": ["Retrieve", "→", "Answer"], "mode": "pop", "emphasize": [2], "startFrameOffset": 6 } }
        ]
      }
    },
    {
      "id": "b13",
      "t0": 48,
      "t1": 52,
      "line": "Use it when you care about meaning.",
      "intent": "when_to_use",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.54 },
        "layers": [
          { "type": "LowerThird", "props": { "title": "Great for: support • notes • catalogs", "source": "", "durationSec": 4, "align": "left" } },
          { "type": "MediaFrame", "props": { "kind": "react", "reactContent": "CatalogCardsBroll", "fallbackReactContent": "PipelineBlocksBroll" } }
        ]
      }
    },
    {
      "id": "b14",
      "t0": 52,
      "t1": 56,
      "line": "Recap: store meaning, search by closeness.",
      "intent": "recap",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.6 },
        "layers": [
          { "type": "HeroTitle", "props": { "title": "Store meaning. Search closeness.", "subtitle": "That’s a vector database.", "enterDelayFrames": 0 } }
        ]
      }
    },
    {
      "id": "b15",
      "t0": 56,
      "t1": 60,
      "line": "Keywords find matches. Vectors find intent.",
      "intent": "outro",
      "render_mode": "remotion_only",
      "scene": {
        "backdrop": { "preset": "gemini", "animate": true, "intensity": 0.7 },
        "layers": [
          { "type": "LogoOutro", "props": { "logoSrc": "logo.png", "tagline": "Keywords → Matches | Vectors → Intent", "chimeSrc": "chime.wav" } }
        ]
      }
    }
  ],
  "global_overlays": {
    "beatcut": {
      "enabled": true,
      "beatsInFrames": [120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1440, 1560],
      "flashOpacity": 0.06,
      "flashDurationFrames": 2
    }
  }
}
```

---

## 4) 怎么把它丢进你的“生成 + 自我迭代”闭环

### Step 1：生成 TTS

* 把上面的 `expected_script.txt` 转成 `public/tts/vector_db_60s.wav`
* 然后在 spec 里把 `audio.src` 指向它（我已写好：`tts/vector_db_60s.wav`）

### Step 2：渲染

```bash
npm run render:skill -- --spec src/specs/vector_db.timeline.json --out out/video.mp4
# 或你实际的 render 命令
```

### Step 3：评测

```bash
python3 qa/evaluate_video.py \
  --config src/config/quality.json \
  --video out/video.mp4 \
  --manifest out/manifest.json \
  --expected_text qa/expected_script.txt \
  --out out/report.json
```

### Step 4：自我迭代直到达标

```bash
python3 qa/optimize_loop.py \
  --spec src/specs/vector_db.timeline.json \
  --target 60 \
  --max_iter 10
```

---

## 一个重要提醒（否则你会“被自己配置卡死”）

你之前的 `maxCharsPerLine=12` 是偏中文的；英文字幕如果按“字符数”算，12 会非常苛刻，可能导致评测一直扣分、自动 patch 把字号越改越小。

建议你在 `src/config/quality.json` 针对英文先改成：

* `limits.maxCharsPerLine`: 24（或把“字符”改成“单词数”更合理）
* `limits.maxLines`: 2 保持不变

这样更容易先跑通“≥60分”闭环。

---

如果你愿意，我可以再给你一版**更“模板化”的 spec**：只让模型输出 `intent + 旁白句子`，其余 layers 由你的路由规则自动填充（更稳、更适合规模化）。
