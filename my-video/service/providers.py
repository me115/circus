from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .settings import LLMSettings, TTSSettings


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    content = text.strip()
    if not content:
        raise ValueError("empty model response")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no json object found in model response")
    return json.loads(content[start : end + 1])


class OpenAICompatibleLLM:
    def __init__(self, cfg: LLMSettings):
        self.cfg = cfg
        api_key = os.getenv(cfg.api_key_env, "").strip()
        if cfg.enabled and not api_key:
            raise RuntimeError(
                f"LLM enabled but missing env var: {cfg.api_key_env}"
            )
        self.api_key = api_key

    def is_enabled(self) -> bool:
        return self.cfg.enabled and bool(self.api_key)

    def chat_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.is_enabled():
            raise RuntimeError("llm disabled")
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.cfg.timeout_sec,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return _extract_json_from_text(str(text))


class OpenAICompatibleTTS:
    def __init__(self, cfg: TTSSettings):
        self.cfg = cfg
        api_key = os.getenv(cfg.api_key_env, "").strip()
        if cfg.enabled and not api_key:
            raise RuntimeError(
                f"TTS enabled but missing env var: {cfg.api_key_env}"
            )
        self.api_key = api_key

    def is_enabled(self) -> bool:
        return self.cfg.enabled and bool(self.api_key)

    def synthesize(self, text: str, out_file: Path) -> Path:
        if not self.is_enabled():
            raise RuntimeError("tts disabled")
        url = self.cfg.base_url.rstrip("/") + "/audio/speech"
        payload = {
            "model": self.cfg.model,
            "voice": self.cfg.voice,
            "input": text,
            "format": self.cfg.audio_format,
        }
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.cfg.timeout_sec,
        )
        resp.raise_for_status()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(resp.content)
        return out_file


def build_llm_client(cfg: LLMSettings) -> Optional[OpenAICompatibleLLM]:
    if cfg.provider != "openai_compatible":
        return None
    return OpenAICompatibleLLM(cfg)


def build_tts_client(cfg: TTSSettings) -> Optional[OpenAICompatibleTTS]:
    if cfg.provider != "openai_compatible":
        return None
    return OpenAICompatibleTTS(cfg)

