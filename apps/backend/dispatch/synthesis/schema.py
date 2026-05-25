"""Pydantic schemas the synthesizer returns; the orchestrator validates against these."""
from typing import Literal
from pydantic import BaseModel, Field


class ProjectLine(BaseModel):
    slug: str
    name: str
    status: Literal["active", "held"]
    stat: str
    bullet: Literal["red", "amber", "sand"]


class LeadFiling(BaseModel):
    # The spec targets a 50–80 word body (~350-500 chars including
    # punctuation). 400 was too tight on busy days — the synthesizer
    # consistently produced 410-450 chars and tripped Pydantic on every
    # backfill attempt over 7 historical windows. 600 keeps the cap
    # honest without rejecting legitimate prose.
    lead_headline: str = Field(max_length=160)
    lead_body: str = Field(max_length=600)
    active_count: str = Field(pattern=r"^\d{2}$")
    project_lines: list[ProjectLine]


class AddendumFiling(BaseModel):
    addendum_body: str = Field(max_length=600)


class ArticleFiling(BaseModel):
    # Short prose body that backs the briefing detail page and the Ava
    # TTS read. Target ~200 words / ~1200 chars (~80s audio at Chirp's
    # ~150 wpm); up to ~300 words / ~1800 chars when the synthesizer
    # enters explainer mode for a genuinely new concept. 600 floor
    # rejects single-paragraph stubs; 2200 ceiling leaves a little
    # headroom on top of the 300-word target without letting the brief
    # drift back into the old 3-4 minute slab.
    article: str = Field(min_length=600, max_length=2200)
