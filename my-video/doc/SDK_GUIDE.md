# 视频生成 SDK 使用说明

本文档说明如何以 SDK 方式调用当前视频生成能力，不依赖你自己手写 HTTP 请求。

当前提供两种 SDK 调用模式：

- `HttpPipelineClient`：调用已启动的 FastAPI 服务（推荐给多进程/跨机器调用）。
- `LocalPipelineClient`：进程内直接调用 `service.pipeline.run_pipeline`（推荐给后端单体内嵌）。

## 1. 目录与入口

SDK 代码位置：

- `sdk/client.py`
- `sdk/__init__.py`

核心类：

- `sdk.HttpPipelineClient`
- `sdk.LocalPipelineClient`
- `sdk.PipelineRequest`（复用 `service.pipeline.PipelineRequest`）

## 2. 依赖安装

```bash
cd my-video
python3 -m pip install -r qa/requirements.txt
```

## 3. HTTP 模式（调用独立服务）

### 3.1 启动服务

```bash
cd my-video
npm run service:start
```

### 3.2 最小示例

```python
from sdk import HttpPipelineClient, PipelineRequest

client = HttpPipelineClient(base_url="http://127.0.0.1:8080")

req = PipelineRequest(
    topic="What is a vector database?",
    ratio="16:9",
    mode="optimize",
    target_score=70,
    max_iter=5,
    use_llm=False,
    enable_tts=False,
)

# submit + wait（同步拿最终结果）
final_status = client.run(req, wait_timeout_sec=7200)
print(final_status.status)
print(final_status.result.score_total if final_status.result else None)
print(final_status.result.video_path if final_status.result else None)
```

### 3.3 分步调用

```python
from sdk import HttpPipelineClient

client = HttpPipelineClient("http://127.0.0.1:8080")
submitted = client.submit({"topic": "RAG basics", "ratio": "16:9", "mode": "render_and_eval"})
status = client.wait(submitted.job_id)
print(status.status)
```

可用方法：

- `healthz()`
- `submit(req)`
- `get(job_id)`
- `list(limit=20)`
- `wait(job_id, timeout_sec=..., poll_interval_sec=...)`
- `run(req, wait_timeout_sec=...)`

## 4. Local 模式（进程内调用）

Local 模式不依赖 HTTP 服务，适合直接嵌入你后端业务逻辑。

```python
from sdk import LocalPipelineClient, PipelineRequest

client = LocalPipelineClient(config_path="service/config/service.yaml")

req = PipelineRequest(
    topic="What is a vector database?",
    ratio="16:9",
    mode="optimize",
    target_score=70,
    max_iter=5,
    use_llm=False,
    enable_tts=False,
)

resp = client.run(req)
print(resp.job_id)
print(resp.job_dir)
print(resp.result.status)
print(resp.result.video_path)
```

返回对象 `LocalRunResponse` 包含：

- `job_id`
- `job_dir`
- `result`（`PipelineResult`）

## 5. 参数约定（PipelineRequest）

常用字段：

- `topic`: 主题
- `audience`: 受众
- `tone`: 风格
- `duration_sec`: 视频时长
- `ratio`: `16:9` 或 `9:16`
- `mode`: `render_only` / `render_and_eval` / `optimize`
- `target_score`: 优化目标分
- `max_iter`: 最大迭代轮数
- `use_llm`: 是否使用大模型自动生成 spec/script
- `enable_tts`: 是否合成配音
- `quality_path`: 自定义 quality 配置路径
- `spec`: 直接传入 storyboard（传入后将优先使用）
- `expected_script`: 评测对齐脚本

## 6. 错误处理建议

- HTTP 模式：
  - SDK 会在非 2xx 时抛 `RuntimeError`（含 status/detail）。
  - `wait()` 超时会抛 `TimeoutError`。
- Local 模式：
  - SDK 正常返回 `PipelineResult`，失败时 `result.status=failed`，并包含 `error/traceback`。

## 7. 对外服务接入建议

如果你要开放给外部用户，推荐封装一个业务层 Service，统一：

- 鉴权与租户配额（API Key / JWT）
- 请求幂等（`client_request_id`）
- 输入模板校验（限制时长、分辨率、迭代次数）
- 产物 URL 映射（对象存储 + 签名链接）
- 审计与观测（trace_id、慢任务告警、失败分类）

## 8. 文档索引

- 后端服务化：`doc/BACKEND_SERVICE_GUIDE.md`
- QA 与优化：`qa/README_QA.md`
