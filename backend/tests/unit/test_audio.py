"""Unit tests for audio module."""
import pytest
from dispatch.audio.cartesia import _chunk_text, _estimate_duration


def test_chunk_text_short():
    assert _chunk_text("Hello world.") == ["Hello world."]


def test_chunk_text_splits_at_boundary():
    long_text = "Hello world. " * 1000  # way over 4000 chars
    chunks = _chunk_text(long_text)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 4000


def test_estimate_duration():
    assert _estimate_duration("" * 10) == 1
    assert _estimate_duration("x" * 250) == 100


@pytest.mark.asyncio
async def test_generate_brief_audio_skips_without_key(monkeypatch):
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    from dispatch.audio.cartesia import generate_brief_audio
    with pytest.raises(RuntimeError, match="CARTESIA_API_KEY"):
        await generate_brief_audio("Test text.")
