from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Union

import requests
from pydantic import BaseModel

from service.app import JobStatusResponse, SubmitJobResponse
from service.pipeline import PipelineRequest, PipelineResult, run_pipeline
from service.settings import load_settings


PipelineRequestLike = Union[PipelineRequest, Dict[str, Any]]


class LocalRunResponse(BaseModel):
    job_id: str
    job_dir: str
    result: PipelineResult


def _to_request(req: PipelineRequestLike) -> PipelineRequest:
    if isinstance(req, PipelineRequest):
        return req
    if isinstance(req, dict):
        return PipelineRequest.model_validate(req)
    raise TypeError(f"unsupported request type: {type(req)}")


def _ensure_ok(resp: requests.Response) -> None:
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        try:
            detail = resp.json()
        except Exception:  # pylint: disable=broad-except
            detail = resp.text
        raise RuntimeError(
            f"http request failed: status={resp.status_code}, detail={detail}"
        ) from exc


class HttpPipelineClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        timeout_sec: int = 30,
        poll_interval_sec: float = 1.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.poll_interval_sec = poll_interval_sec

    def healthz(self) -> Dict[str, Any]:
        resp = requests.get(f"{self.base_url}/healthz", timeout=self.timeout_sec)
        _ensure_ok(resp)
        return resp.json()

    def submit(self, req: PipelineRequestLike) -> SubmitJobResponse:
        payload = _to_request(req).model_dump()
        resp = requests.post(
            f"{self.base_url}/v1/jobs",
            json=payload,
            timeout=self.timeout_sec,
        )
        _ensure_ok(resp)
        return SubmitJobResponse.model_validate(resp.json())

    def get(self, job_id: str) -> JobStatusResponse:
        resp = requests.get(
            f"{self.base_url}/v1/jobs/{job_id}",
            timeout=self.timeout_sec,
        )
        _ensure_ok(resp)
        return JobStatusResponse.model_validate(resp.json())

    def list(self, limit: int = 20) -> List[JobStatusResponse]:
        resp = requests.get(
            f"{self.base_url}/v1/jobs",
            params={"limit": limit},
            timeout=self.timeout_sec,
        )
        _ensure_ok(resp)
        data = resp.json()
        items = data.get("items", []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []
        return [JobStatusResponse.model_validate(item) for item in items]

    def wait(
        self,
        job_id: str,
        timeout_sec: int = 7200,
        poll_interval_sec: Optional[float] = None,
    ) -> JobStatusResponse:
        deadline = time.time() + timeout_sec
        interval = poll_interval_sec or self.poll_interval_sec
        while time.time() < deadline:
            status = self.get(job_id)
            if status.status in {"completed", "failed"}:
                return status
            time.sleep(max(0.2, interval))
        raise TimeoutError(f"wait timeout for job_id={job_id}")

    def run(
        self,
        req: PipelineRequestLike,
        wait_timeout_sec: int = 7200,
        poll_interval_sec: Optional[float] = None,
    ) -> JobStatusResponse:
        submitted = self.submit(req)
        return self.wait(
            submitted.job_id,
            timeout_sec=wait_timeout_sec,
            poll_interval_sec=poll_interval_sec,
        )


class LocalPipelineClient:
    def __init__(self, config_path: Optional[str] = None):
        self.settings = load_settings(config_path)

    def run(
        self,
        req: PipelineRequestLike,
        job_id: Optional[str] = None,
    ) -> LocalRunResponse:
        parsed = _to_request(req)
        actual_job_id = job_id or uuid.uuid4().hex
        result = run_pipeline(self.settings, actual_job_id, parsed)
        job_dir = self.settings.abs_path(self.settings.runtime.data_dir) / actual_job_id
        return LocalRunResponse(
            job_id=actual_job_id,
            job_dir=str(job_dir),
            result=result,
        )
