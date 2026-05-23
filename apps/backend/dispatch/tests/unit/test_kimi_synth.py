# apps/backend/dispatch/tests/unit/test_kimi_synth.py
import pytest
from unittest.mock import patch, AsyncMock

from dispatch.synthesis.kimi import (
    KimiCLISynthesizer,
    _parse_json_to_schema,
    _extract_content,
)
from dispatch.synthesis.schema import LeadFiling


def _good_json():
    return """{
      "lead_headline": "Agos clears the import-cycle bug.",
      "lead_body": "A quiet day on Aether-Focus.",
      "active_count": "03",
      "project_lines": [{"slug":"agos","name":"Agos","status":"active","stat":"9 commits","bullet":"red"}]
    }"""


def test_parse_clean_json():
    f = _parse_json_to_schema(_good_json(), LeadFiling)
    assert f.lead_headline.startswith("Agos")
    assert f.active_count == "03"


def test_parse_strips_code_fence():
    wrapped = "```json\n" + _good_json() + "\n```"
    f = _parse_json_to_schema(wrapped, LeadFiling)
    assert f.active_count == "03"


def test_parse_extracts_from_prose():
    chatty = "Sure! Here's the brief:\n" + _good_json() + "\nLet me know if you want tweaks."
    f = _parse_json_to_schema(chatty, LeadFiling)
    assert f.active_count == "03"


def test_extract_content_from_payload():
    payload = {
        "choices": [
            {"message": {"content": "Hello", "role": "assistant"}},
            {"message": {"content": " world"}},
        ]
    }
    assert _extract_content(payload) == "Hello world"


@pytest.mark.asyncio
async def test_kimi_cli_success():
    s = KimiCLISynthesizer()
    fake_proc = AsyncMock()
    fake_proc.returncode = 0
    fake_proc.communicate = AsyncMock(return_value=(_good_json().encode(), b""))
    with patch("asyncio.create_subprocess_exec", return_value=fake_proc) as mock_exec:
        f = await s.filing("any prompt", LeadFiling)
        assert f.lead_headline.startswith("Agos")
        # Verify --no-thinking is passed by default
        cmd = mock_exec.call_args[0]
        assert "--no-thinking" in cmd


@pytest.mark.asyncio
async def test_kimi_cli_thinking_enabled():
    s = KimiCLISynthesizer(thinking=True)
    fake_proc = AsyncMock()
    fake_proc.returncode = 0
    fake_proc.communicate = AsyncMock(return_value=(_good_json().encode(), b""))
    with patch("asyncio.create_subprocess_exec", return_value=fake_proc) as mock_exec:
        await s.filing("any prompt", LeadFiling)
        cmd = mock_exec.call_args[0]
        assert "--no-thinking" not in cmd


@pytest.mark.asyncio
async def test_kimi_cli_generate_raw():
    s = KimiCLISynthesizer()
    fake_proc = AsyncMock()
    fake_proc.returncode = 0
    fake_proc.communicate = AsyncMock(return_value=(b"Hello world", b""))
    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        text = await s.generate("prompt")
        assert text == "Hello world"
