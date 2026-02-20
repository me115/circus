from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .pipeline import PipelineRequest, PipelineResult, run_pipeline
from .settings import ServiceSettings, load_settings


class SubmitJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: float
    updated_at: float
    request: PipelineRequest
    result: Optional[PipelineResult] = None


@dataclass
class JobState:
    job_id: str
    request: PipelineRequest
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: Optional[PipelineResult] = None


class JobManager:
    def __init__(self, settings: ServiceSettings):
        self.settings = settings
        self.jobs: Dict[str, JobState] = {}
        self.queue: "queue.Queue[str]" = queue.Queue()
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _job_dir(self, job_id: str) -> Path:
        return self.settings.abs_path(self.settings.runtime.data_dir) / job_id

    def _persist(self, state: JobState) -> None:
        job_dir = self._job_dir(state.job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "job_id": state.job_id,
            "status": state.status,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "request": state.request.model_dump(),
            "result": state.result.model_dump() if state.result else None,
        }
        with (job_dir / "job.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def submit(self, req: PipelineRequest) -> JobState:
        job_id = uuid.uuid4().hex
        state = JobState(job_id=job_id, request=req)
        with self.lock:
            self.jobs[job_id] = state
            self._persist(state)
        self.queue.put(job_id)
        return state

    def get(self, job_id: str) -> Optional[JobState]:
        with self.lock:
            return self.jobs.get(job_id)

    def list(self, limit: int = 20) -> list[JobState]:
        with self.lock:
            values = sorted(
                self.jobs.values(), key=lambda item: item.created_at, reverse=True
            )
            return values[: max(1, min(limit, 200))]

    def _worker_loop(self) -> None:
        while True:
            job_id = self.queue.get()
            state = self.get(job_id)
            if state is None:
                self.queue.task_done()
                continue
            with self.lock:
                state.status = "running"
                state.updated_at = time.time()
                self._persist(state)
            result = run_pipeline(self.settings, job_id, state.request)
            with self.lock:
                state.result = result
                state.status = "completed" if result.status == "completed" else "failed"
                state.updated_at = time.time()
                self._persist(state)
            self.queue.task_done()


settings = load_settings()
manager = JobManager(settings)
app = FastAPI(title="Video Generation Service", version="1.0.0")


def _to_response(state: JobState) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=state.job_id,
        status=state.status,
        created_at=state.created_at,
        updated_at=state.updated_at,
        request=state.request,
        result=state.result,
    )


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "queue_size": manager.queue.qsize(),
        "data_dir": str(settings.abs_path(settings.runtime.data_dir)),
    }


@app.post("/v1/jobs", response_model=SubmitJobResponse)
def submit_job(req: PipelineRequest) -> SubmitJobResponse:
    state = manager.submit(req)
    return SubmitJobResponse(job_id=state.job_id, status=state.status)


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    state = manager.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _to_response(state)


@app.get("/v1/jobs")
def list_jobs(limit: int = 20) -> dict:
    items = manager.list(limit=limit)
    return {"items": [_to_response(item).model_dump() for item in items]}

