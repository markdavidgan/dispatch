"""Self-critique passes. Two-pass for quality, single-pass for speed."""
from typing import TypeVar
from pydantic import BaseModel
from dispatch.synthesis.synthesizer import Synthesizer

M = TypeVar("M", bound=BaseModel)

RUBRIC = """\
Review your previous draft against this rubric (6 items) and revise:

1. Specificity — each project mention names what *actually* happened, not generic "made progress".
2. No clichés — no "excited to announce", "in today's fast-paced", "leverage", "robust".
3. No hype — energy is calm. Sentences make claims, not pitches.
4. Sentence rhythm — vary length. Don't write three same-shape sentences in a row.
5. Monocle restraint — short headline, restrained body. No exclamation marks.
6. Schema fidelity — every required field present, length limits respected.

Return the revised JSON object — same schema, no prose, no code fences.
If the draft was already perfect, return it unchanged.
"""


async def single_pass(synth: Synthesizer, prompt: str, schema: type[M]) -> M:
    """One-shot synthesis. Fast. Use for daily briefs where latency matters."""
    return await synth.filing(prompt, schema)


async def two_pass(synth: Synthesizer, prompt: str, schema: type[M]) -> M:
    """Draft → revise(draft) → return revised. Slower but higher quality."""
    draft = await synth.filing(prompt, schema)
    revise_prompt = (
        prompt
        + "\n\n## Previous draft\n"
        + draft.model_dump_json(indent=2)
        + "\n\n## Revision instruction\n"
        + RUBRIC
    )
    revised = await synth.filing(revise_prompt, schema)
    return revised
