# apps/backend/dispatch/tests/unit/test_anthropic_synth.py
import pytest
import respx
import httpx
from dispatch.synthesis.anthropic import AnthropicSynthesizer
from dispatch.synthesis.schema import LeadFiling


@pytest.mark.asyncio
async def test_anthropic_returns_parsed_filing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    canned = '''{
      "lead_headline": "h", "lead_body": "b", "active_count": "01",
      "project_lines": [{"slug":"a","name":"A","status":"active","stat":"s","bullet":"red"}]
    }'''
    with respx.mock(base_url="https://api.anthropic.com") as mock:
        mock.post("/v1/messages").mock(return_value=httpx.Response(200, json={
            "content": [{"type": "text", "text": canned}],
        }))
        s = AnthropicSynthesizer()
        f = await s.filing("p", LeadFiling)
        assert f.lead_headline == "h"
