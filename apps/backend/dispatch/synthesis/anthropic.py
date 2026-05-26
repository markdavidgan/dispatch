"""AnthropicSynthesizer — REST against /v1/messages."""
import os
from typing import TypeVar
import httpx
from pydantic import BaseModel
import json
import re

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


def _parse_json_to_schema(text: str, schema: type[M]) -> M:
    """Extract JSON from markdown fences and parse into schema."""
    # Try fenced code block first
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence:
        raw = fence.group(1)
    else:
        # Try bare JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in response")
        raw = text[start:end + 1]
    data = json.loads(raw)
    return schema(**data)
