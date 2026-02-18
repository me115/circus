# my-video 编码规范约束与项目分层规范

本文档为 `circus/my-video` 仓库提供可执行的编码规范、分层边界与 AI 协作约束。  
规范强度分为：`MUST`（必须）、`SHOULD`（应当）、`RECOMMENDED`（推荐）。

版本：`1.0`  
最后更新：`2026-02-18`

---

## 1. 项目定位与总体架构

### 1.1 项目定位

`my-video` 是一个基于 Remotion 的“脚本化短视频生成 + 自动评测 + 自我优化”项目。

- `MUST`：服务核心是 **Spec 驱动的视频生成**，而不是手工逐帧编辑。
- `MUST`：视频质量由 `qa` 框架统一判定，`gate` 失败视为不合格，即使 `raw score` 很高。
- `SHOULD`：默认产出应面向“可直接使用”的短片（60 分及以上且 gate 全通过）。

### 1.2 总体架构

核心链路：`Timeline Spec -> Manifest -> Remotion Render -> QA Evaluate -> Patch Suggestions -> Optimize Loop`

- `scripts/emit_manifest.ts`：从 Spec 生成 manifest（结构与布局元数据）。
- `scripts/render_from_spec.ts`：渲染视频并输出 `out/video.mp4`。
- `qa/evaluate_video.py`：计算指标、执行 gate、输出 `out/report.json`。
- `qa/patcher.py`：基于 report 生成补丁建议。
- `qa/optimize_loop.py`：迭代执行 render/evaluate/patch 直到达标或迭代上限。

---

## 2. 目录结构与职责划分

| 目录 | 职责 | 新增规范 | AI 权限 |
|---|---|---|---|
| `my-video/src/specs/` | 时间线规格（beat、scene、layer） | `MUST`：作为视频语义真源；变更需保证时长、beat 连续性与组件可渲染性 | ✅ 重点修改 |
| `my-video/src/components/` | Remotion 组件库（视觉组件） | `MUST`：组件保持可复用，禁止耦合场景特定硬编码逻辑 | ✅ 重点修改 |
| `my-video/src/compositions/` | 组合层（把 spec/组件组装成最终画面） | `MUST`：仅做编排，不堆业务规则 | ✅ 可修改 |
| `my-video/src/theme/` | 视觉 token 与 motion 规范 | `SHOULD`：样式与动效参数集中管理，避免散落常量 | ✅ 可修改 |
| `my-video/src/config/quality.json` | QA 阈值与 gate 配置 | `MUST`：阈值调整要与评测逻辑同步；禁止无依据放宽 gate | ⚠️ 谨慎修改 |
| `my-video/scripts/` | 渲染与 manifest 生成脚本 | `MUST`：脚本失败必须快速退出并返回非零状态码 | ✅ 可修改 |
| `my-video/qa/` | 评测、打分、补丁、优化循环 | `MUST`：规则可解释；新增指标需可落地到 gate/score/report | ✅ 重点修改 |
| `my-video/out/` | 产物目录（视频、manifest、report） | `MUST`：只允许脚本生成，禁止手工“修文件过评测” | ❌ 禁止手改 |
| `my-video/public/` | 静态资产（logo、音频、图片） | `SHOULD`：保持可替换，路径稳定 | ⚠️ 谨慎修改 |

---

## 3. 核心概念术语表（Glossary）

| 术语 | 定义 | 代码对应 |
|---|---|---|
| Timeline Spec | 视频结构定义（meta/audio/beats/layers） | `src/specs/*.timeline.json` |
| Beat | 时间片段（通常 2–4s） | `beats[]` |
| Scene Layer | 画面层（如 `MediaFrame`、`LowerThird`） | `beat.scene.layers[]` |
| Render Manifest | 渲染期元数据（布局/边界/层类型） | `out/manifest.json` |
| Gate | 硬性通过条件集合 | `qa/scoring.py::gate_checks` |
| Raw Score | 不考虑 gate 的加权分 | `report.score.raw_total` |
| Final Score | gate 失败即置 0 的最终分 | `report.score.total` |
| Low-info Run | 连续低信息画面时长 | `metrics.video.maxLowInfoRunSec` |
| Sparse Beat | 组件占比过低的 beat | `metrics.manifest.layout.sparse_beat_rate` |
| Structure Integrity | 结构完整性（非纯文字、时长足够） | `metrics.manifest.structure.*` |

---

## 4. 详细分层规范

### 4.1 Spec 层（`src/specs`）

- `MUST`：`t0/t1` 单调递增，且全片覆盖连续、无无意空窗。
- `MUST`：每个非 hook/outro beat 必须包含至少一个结构化视觉层（如 `MediaFrame` / `PromptAnswerCard` / `HeroTitle`）。
- `SHOULD`：同一视频内组件类型与变体保持多样，避免连续重复导致审美疲劳。

### 4.2 Component 层（`src/components`）

- `MUST`：组件内任何布局不得越界（不可超出 1920x1080 安全边界）。
- `MUST`：文本在 1080p 目标下保持可读（遵守质量配置中的最小可读字号/占比）。
- `SHOULD`：组件提供可控 props（密度、字号、间距、动画强度）以支持自动 patch。

### 4.3 Composition 层（`src/compositions`）

- `MUST`：编排层只负责“按 beat 渲染”，不写隐式业务分支污染组件。
- `SHOULD`：过渡类型控制在有限集合，维持统一节奏与风格一致性。
- `RECOMMENDED`：首 3 秒默认带 hook（高对比文案/关键视觉）以提高留存。

### 4.4 Scripts 层（`scripts`）

- `MUST`：`emit_manifest -> render` 顺序固定，失败即终止。
- `MUST`：脚本输出路径与文件名稳定，便于 QA 自动读取。
- `SHOULD`：命令行参数与 README 保持一致，避免“文档可跑、脚本不可跑”。

### 4.5 QA 层（`qa`）

- `MUST`：新增评测指标必须同时定义：`metrics` 字段、`gate` 逻辑、`score` 权重（如需）。
- `MUST`：硬性不通过指标（例如黑屏/空窗/越界/长时间低信息）必须进入 gate，而非仅影响分数。
- `MUST`：补丁策略不得通过“降低阈值”绕过问题，应优先修正 spec/组件。
- `SHOULD`：`report.json` 需保持稳定字段，方便迭代脚本与外部系统消费。

---

## 5. 开发流程与规范

### 5.0 常用开发处理

- `MUST`：先复用现有组件与布局模式，禁止无依据新增重复组件。
- `MUST`：修改 `qa` 核心逻辑后，至少执行一次完整链路：
  - `npm run render:skill`
  - `python3 qa/evaluate_video.py ...`
- `SHOULD`：做完补丁策略改动后，执行 `python3 qa/optimize_loop.py ...` 验证可收敛。

### 5.1 测试与校验

- `MUST`：提交前通过 `npm run lint`。
- `MUST`：Python QA 脚本保持可编译（如 `python3 -m py_compile qa/*.py`）。
- `SHOULD`：对关键评测逻辑补充最小回归用例（可先用固定 report/manifest 夹具）。

### 5.2 错误处理

- `MUST`：禁止吞错；出现异常必须写入明确错误原因并返回非零退出码。
- `MUST`：路径/配置读取失败时给出可定位信息（文件路径 + 缺失字段）。
- `SHOULD`：评测失败信息优先面向“可修复动作”（哪个指标失败、建议改哪里）。

### 5.3 日志与可观测性

- `MUST`：核心流程日志至少包含：输入 spec、输出视频、输出 report、exit code。
- `MUST`：`report.json` 必须可解释，保留 `gate.checks` 与关键指标。
- `RECOMMENDED`：历史迭代结果落盘到 `out/history/` 便于回溯。

### 5.4 命名规范

- `MUST`：beat id 使用稳定格式（如 `b01`、`b02`）。
- `MUST`：组件类型名与文件名一致（`HeroTitle.tsx` -> `HeroTitle`）。
- `SHOULD`：新增 `reactContent` 变体命名遵循 `XxxBroll` 风格并体现语义。

### 5.5 并发控制

- `MUST`：避免并发写同一 `out/` 文件（视频、manifest、report）。
- `MUST`：批量处理帧/指标时确保资源可回收（文件句柄、VideoCapture）。
- `SHOULD`：若引入并发评测，需保证结果可复现（固定采样策略与随机种子）。

---

## 6. AI 交互准则（AI Interaction）

- `MUST`：禁止 AI 手工篡改 `out/*.mp4`、`out/report.json`、`out/manifest.json` 来“伪达标”。
- `MUST`：生成代码风格需与当前文件一致（命名、错误处理、字段风格）。
- `MUST`：引入 lint/type error 后必须在同次提交中修复。
- `SHOULD`：复杂规则修改需附带简要中文注释，说明“为什么这样判定/修复”。
- `RECOMMENDED`：每次修改核心逻辑后，检查并更新本文件对应条款。

