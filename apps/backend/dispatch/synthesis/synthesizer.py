import os
from typing import Protocol, TypeVar
from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class Synthesizer(Protocol):
    name: str
    async def filing(self, prompt: str, schema: type[M]) -> M: ...


def select_primary() -> str:
    return os.environ.get("DISPATCH_AI_PROVIDER", "kimi").lower()
