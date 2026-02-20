from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class LLMSettings(BaseModel):
    enabled: bool = False
    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-4o-mini"
    timeout_sec: int = 60
    temperature: float = 0.2
    max_tokens: int = 1800


class TTSSettings(BaseModel):
    enabled: bool = False
    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-4o-mini-tts"
    voice: str = "alloy"
    audio_format: str = "wav"
    timeout_sec: int = 90


class RuntimeSettings(BaseModel):
    data_dir: str = "out/service_jobs"
    public_tts_dir: str = "public/tts"
    queue_concurrency: int = 1
    command_timeout_sec: int = 3600
    default_quality_path: str = "src/config/quality.json"
    quality_169_path: str = "src/config/quality_presets/apple_keynote_169.json"
    stylekit_path: str = "src/style/stylekit.json"
    motionkit_path: str = "src/style/motionkit.json"
    default_spec_path: str = "src/specs/vector_db.timeline.json"
    expected_script_default: str = "qa/expected_script.txt"


class ServiceSettings(BaseModel):
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)

    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def abs_path(self, rel_or_abs: str) -> Path:
        path = Path(rel_or_abs)
        if path.is_absolute():
            return path
        return self.repo_root() / path

    def ensure_dirs(self) -> None:
        self.abs_path(self.runtime.data_dir).mkdir(parents=True, exist_ok=True)
        self.abs_path(self.runtime.public_tts_dir).mkdir(parents=True, exist_ok=True)


def _merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def load_settings(config_path: Optional[str] = None) -> ServiceSettings:
    env_path = os.getenv("VIDEO_SERVICE_CONFIG")
    cfg_path = config_path or env_path or "service/config/service.yaml"
    root = Path(__file__).resolve().parents[1]
    path = Path(cfg_path)
    if not path.is_absolute():
        path = root / path

    if not path.exists():
        # Fallback to example config for developer convenience.
        fallback = root / "service/config/service.example.yaml"
        if fallback.exists():
            path = fallback

    raw: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                raw = loaded

    default = ServiceSettings().model_dump()
    merged = _merge_dict(default, raw)
    settings = ServiceSettings.model_validate(merged)
    settings.ensure_dirs()
    return settings

