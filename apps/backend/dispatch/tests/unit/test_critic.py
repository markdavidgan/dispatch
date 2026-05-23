# apps/backend/dispatch/tests/unit/test_critic.py
import pytest
from unittest.mock import AsyncMock
from dispatch.synthesis.critic import single_pass, two_pass
from dispatch.synthesis.schema import LeadFiling


def _make_filing(headline: str = "Draft") -> LeadFiling:
    return LeadFiling(
        lead_headline=headline,
        lead_body="x",
        active_count="01",
        project_lines=[
            {
                "slug": "a",
                "name": "A",
                "status": "active",
                "stat": "s",
                "bullet": "red",
            }
        ],
    )


@pytest.mark.asyncio
async def test_single_pass_calls_synth_once():
    f1 = _make_filing("OneShot")
    synth = type("S", (), {})()
    synth.filing = AsyncMock(return_value=f1)
    out = await single_pass(synth, "prompt", LeadFiling)
    assert out.lead_headline == "OneShot"
    assert synth.filing.await_count == 1


@pytest.mark.asyncio
async def test_two_pass_calls_synth_twice():
    f1 = _make_filing("Draft")
    f2 = _make_filing("Revised")
    synth = type("S", (), {})()
    synth.filing = AsyncMock(side_effect=[f1, f2])
    out = await two_pass(synth, "prompt", LeadFiling)
    assert out.lead_headline == "Revised"
    assert synth.filing.await_count == 2
