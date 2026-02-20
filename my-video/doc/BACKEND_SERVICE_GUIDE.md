# 视频生成后端服务化接入说明

本文档说明如何把当前 `Remotion + QA + optimize_loop` 框架以后端服务方式对外提供。

## 1. 已完成的服务化改造

已新增 `service/` 模块，提供任务提交与异步执行能力：

- `service/app.py`
  - FastAPI 接口
  - 任务队列（单 worker 串行执行，避免共享 `out/` 目录并发冲突）
- `service/pipeline.py`
  - 流水线编排（render / eval / optimize）
  - 作业目录隔离（`out/service_jobs/{job_id}`）
  - 结果落盘（video / manifest / report / spec / log）
- `service/settings.py`
  - 统一配置加载（YAML + 环境变量）
- `service/providers.py`
  - OpenAI Compatible LLM 客户端
  - OpenAI Compatible TTS 客户端
- `service/prompts.py`
  - LLM 生成 storyboard 的提示词模板
- `service/config/service.example.yaml`
  - 服务配置模板（runtime、llm、tts）

同时新增启动命令：

```bash
npm run service:start
```

## 2. 依赖安装

服务依赖已加入 `qa/requirements.txt`，安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r qa/requirements.txt
```

## 3. 配置（LLM / TTS）

复制配置模板并按需修改：

```bash
cp service/config/service.example.yaml service/config/service.yaml
```

关键项：

- `llm.enabled`: `true` 时会用大模型生成 script + beats（没有传入 `spec` 时）
- `llm.base_url`: 兼容 OpenAI API 的地址
- `llm.api_key_env`: API Key 对应环境变量名
- `llm.model`: 例如 `gpt-4o-mini`
- `tts.enabled`: `true` 时根据脚本自动合成语音并写入 `public/tts/{job_id}.wav`

设置 API Key：

```bash
export OPENAI_API_KEY=xxxx
```

可用配置文件路径：

```bash
export VIDEO_SERVICE_CONFIG=service/config/service.yaml
```

## 4. 启动服务

```bash
npm run service:start
```

默认监听：

- `0.0.0.0:8080`

健康检查：

```bash
curl http://127.0.0.1:8080/healthz
```

## 5. API

### 5.1 提交任务

`POST /v1/jobs`

请求示例：

```json
{
  "topic": "What is a vector database?",
  "audience": "General audience",
  "tone": "Easy, friendly, fast-paced",
  "language": "en",
  "duration_sec": 60,
  "ratio": "16:9",
  "mode": "optimize",
  "target_score": 70,
  "max_iter": 8,
  "use_llm": true,
  "enable_tts": true
}
```

返回：

```json
{
  "job_id": "f4f3b2...",
  "status": "queued"
}
```

### 5.2 查询任务

`GET /v1/jobs/{job_id}`

返回包含：

- 当前状态：`queued/running/completed/failed`
- 原始请求
- 执行结果（`video_path`、`manifest_path`、`report_path`、`score_total`、`gate_pass`）

### 5.3 列表

`GET /v1/jobs?limit=20`

## 6. 运行模式

`mode` 支持：

- `render_only`: 仅渲染视频
- `render_and_eval`: 渲染 + 一次评测
- `optimize`: 渲染 + 自动迭代优化（调用 `qa/optimize_loop.py`）

## 7. 产物目录

每个任务产物目录：

`out/service_jobs/{job_id}/`

包含：

- `spec.json`
- `video.mp4`
- `manifest.json`
- `report.json`（若执行评测）
- `run.log`
- `job.json`

## 8. 建议的生产级增强（下一步）

当前实现适合单机 MVP。对外商用建议继续补齐：

1. 认证鉴权：API Key / JWT / 租户隔离。
2. 并发与调度：接入 Redis + Celery/RQ/Arq，支持多 worker 与重试。
3. 存储外部化：视频与报告写入 S3/OSS，接口返回签名 URL。
4. 任务幂等：支持 `client_request_id` 去重。
5. 限流与配额：按租户控制 QPS、时长、并发数。
6. 可观测性：Prometheus 指标 + 结构化日志 + TraceID。
7. 沙箱化执行：render/ffmpeg 子进程资源限制与超时隔离。
8. 模型策略管理：多模型路由、fallback、成本/延时监控。
9. 版本化：`stylekit/motionkit/quality/spec` 版本固定，保证可复现。
10. 合规：内容审核、PII 检测、审计日志。

## 9. 快速测试

```bash
curl -X POST http://127.0.0.1:8080/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "topic":"What is a vector database?",
    "ratio":"16:9",
    "mode":"optimize",
    "target_score":70,
    "max_iter":3,
    "use_llm":false,
    "enable_tts":false
  }'
```

然后轮询：

```bash
curl http://127.0.0.1:8080/v1/jobs/<job_id>
```

## 10. SDK 调用（HTTP/本地）

除独立服务模式外，项目已提供 SDK 封装，支持：

- HTTP SDK（调用 `/v1/jobs`）
- Local SDK（进程内直接调用 pipeline）

详细用法见：

- `doc/SDK_GUIDE.md`
