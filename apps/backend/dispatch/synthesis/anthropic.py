"""AnthropicSynthesizer — REST against /v1/messages, fallback when Kimi fails."""
import os
from typing import TypeVar
import httpx
from pydantic import BaseModel
from dispatch.synthesis.kimi import _parse_json_to_schema

M = TypeVar("M", bound=BaseModel)


class AnthropicSynthesizer:
    name = "claude-sonnet-4-6"

    def __init__(self, model: str | None = None, timeout_s: int = 60):
        self.model = model or os.environ.get("ANTHROPIC_FALLBACK_MODEL", "claude-sonnet-4-6")
        self.timeout_s = timeout_s

    async def filing(self, prompt: str, schema: type[M]) -> M:
        api_key = os.environ["ANTHROPIC_API_KEY"]
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            payload = r.json()
        text = "".join(b.get("text", "") for b in payload.get("content", []))
        return _parse_json_to_schema(text, schema)
