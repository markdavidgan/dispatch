import os
from typing import Protocol, TypeVar
from pydantic import BaseModel

from dispatch.synthesis.openai_compatible import (
    KimiSynthesizer,
    GeminiSynthesizer,
    GroqSynthesizer,
)

M = TypeVar("M", bound=BaseModel)


class Synthesizer(Protocol):
    name: str
    async def filing(self, prompt: str, schema: type[M]) -> M: ...


def select_primary() -> str:
    return os.environ.get("DISPATCH_AI_PROVIDER", "kimi").lower()


def make_synthesizer(provider: str | None = None) -> Synthesizer:
    """Factory — returns the synthesizer for the given (or configured) provider."""
    p = (provider or select_primary()).lower()

    if p == "kimi":
        return KimiSynthesizer()
    if p == "gemini":
        return GeminiSynthesizer()
    if p == "groq":
        return GroqSynthesizer()

    # Legacy fallback — Anthropic via the old class if available
    try:
        from dispatch.synthesis.anthropic import AnthropicSynthesizer
        return AnthropicSynthesizer()
    except Exception:
        pass

    raise ValueError(f"Unknown DISPATCH_AI_PROVIDER: {p}")
