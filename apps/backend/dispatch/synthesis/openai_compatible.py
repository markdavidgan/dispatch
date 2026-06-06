"""OpenAI-compatible synthesizer — works with Kimi, Gemini, and Groq.

All three providers expose an OpenAI-compatible /chat/completions endpoint.
This avoids duplicating the same HTTP logic across three nearly-identical classes.
"""
from __future__ import annotations

import json
import os
import re
from typing import TypeVar

import httpx
from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class OpenAiCompatibleSynthesizer:
    """Synthesizer that speaks OpenAI Chat Completions to any compatible endpoint."""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str | None = None,
        model: str | None = None,
        env_api_key: str,
        env_model: str | None = None,
        timeout_s: int = 60,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get(env_api_key)
        self.model = model or (os.environ.get(env_model) if env_model else None)
        self.timeout_s = timeout_s

    async def filing(self, prompt: str, schema: type[M]) -> M:
        if not self.api_key:
            raise RuntimeError(f"{self.name}: API key not configured")

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,
                },
            )
            r.raise_for_status()
            payload = r.json()

        text = payload["choices"][0]["message"]["content"]
        return _parse_json_to_schema(text, schema)


def _parse_json_to_schema(text: str, schema: type[M]) -> M:
    """Extract JSON from markdown fences and parse into schema."""
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence:
        raw = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in response")
        raw = text[start : end + 1]
    data = json.loads(raw)
    return schema(**data)


class KimiSynthesizer(OpenAiCompatibleSynthesizer):
    """Kimi For Coding — uses the Kimi Code API (OpenAI-compatible)."""

    def __init__(self, model: str | None = None, timeout_s: int = 60):
        super().__init__(
            name="kimi-for-coding",
            base_url="https://api.kimi.com/coding/v1",
            model=model or "kimi-for-coding",
            env_api_key="KIMI_API_KEY",
            timeout_s=timeout_s,
        )


class GeminiSynthesizer(OpenAiCompatibleSynthesizer):
    """Gemini via the OpenAI-compatible endpoint."""

    def __init__(self, model: str | None = None, timeout_s: int = 60):
        super().__init__(
            name="gemini-2.5-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            model=model,
            env_api_key="GEMINI_API_KEY",
            env_model="GEMINI_MODEL",
            timeout_s=timeout_s,
        )


class GroqSynthesizer(OpenAiCompatibleSynthesizer):
    """Groq Llama via the OpenAI-compatible endpoint."""

    def __init__(self, model: str | None = None, timeout_s: int = 60):
        super().__init__(
            name="groq-llama-3.3-70b",
            base_url="https://api.groq.com/openai/v1",
            model=model,
            env_api_key="GROQ_API_KEY",
            env_model="GROQ_MODEL",
            timeout_s=timeout_s,
        )
