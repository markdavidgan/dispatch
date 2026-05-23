"""Kimi synthesizers — direct HTTP API (fast) and CLI fallback (slow).

KimiAPISynthesizer uses the OpenAI-compatible Kimi Code endpoint directly,
avoiding the multi-second cold-start overhead of spawning the `kimi` CLI
process for every call. OAuth tokens are read from $KIMI_OAUTH_JSON or the
on-disk credentials file and refreshed automatically when near expiry.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import re
import socket
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

M = TypeVar("M", bound=BaseModel)
log = logging.getLogger(__name__)

KIMI_BASE_URL = "https://api.kimi.com/coding/v1"
KIMI_AUTH_URL = "https://auth.kimi.com/api/oauth/token"
KIMI_CLIENT_ID = "17e5f671-d194-4dfb-9706-5516cb48c098"
KIMI_MODEL = "kimi-for-coding"


class KimiTokenError(RuntimeError):
    pass


def _load_oauth_token() -> dict:
    """Load OAuth token from env var or credentials file."""
    env_json = os.environ.get("KIMI_OAUTH_JSON")
    if env_json:
        try:
            return json.loads(env_json)
        except json.JSONDecodeError:
            log.warning("KIMI_OAUTH_JSON is invalid JSON")

    config_dir = os.environ.get("KIMI_CONFIG_DIR", os.path.expanduser("~/.kimi"))
    creds_path = os.path.join(config_dir, "credentials", "kimi-code.json")
    if os.path.exists(creds_path):
        with open(creds_path, encoding="utf-8") as f:
            return json.load(f)

    raise KimiTokenError(
        "No Kimi OAuth token found. Set KIMI_OAUTH_JSON or run kimi login."
    )


def _save_oauth_token(token: dict) -> None:
    """Persist refreshed token back to the credentials file."""
    config_dir = os.environ.get("KIMI_CONFIG_DIR", os.path.expanduser("~/.kimi"))
    creds_dir = os.path.join(config_dir, "credentials")
    creds_path = os.path.join(creds_dir, "kimi-code.json")
    os.makedirs(creds_dir, exist_ok=True)
    with open(creds_path, "w", encoding="utf-8") as f:
        json.dump(token, f)
    try:
        os.chmod(creds_path, 0o600)
    except OSError:
        pass


async def _refresh_oauth_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token."""
    headers = {
        "User-Agent": "kimi-cli/1.44.0",
        "X-Msh-Platform": "kimi_cli",
        "X-Msh-Version": "1.44.0",
        "X-Msh-Device-Name": platform.node() or socket.gethostname(),
        "X-Msh-Device-Model": f"{platform.system()} {platform.machine() or ''}".strip(),
        "X-Msh-Os-Version": platform.version(),
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            KIMI_AUTH_URL,
            data={
                "client_id": KIMI_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": time.time() + data["expires_in"],
            "scope": data.get("scope", "kimi-code"),
            "token_type": data.get("token_type", "Bearer"),
            "expires_in": data["expires_in"],
        }


async def _ensure_fresh_token() -> str:
    """Return a valid access token, refreshing if necessary."""
    token = _load_oauth_token()
    expires_at = token.get("expires_at", 0)
    if expires_at - time.time() < 300:
        if not token.get("refresh_token"):
            raise KimiTokenError("Token expired and no refresh token available")
        log.info("Refreshing Kimi OAuth token...")
        new_token = await _refresh_oauth_token(token["refresh_token"])
        _save_oauth_token(new_token)
        token = new_token
        log.info("Kimi token refreshed, valid for %.0fs", token["expires_at"] - time.time())
    return token["access_token"]


def _extract_content(payload: dict) -> str:
    """Extract text content from a Kimi chat completions response."""
    parts: list[str] = []
    for choice in payload.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content")
        if content:
            parts.append(content)
    return "".join(parts)


class KimiAPISynthesizer:
    """Direct HTTP API synthesizer. No subprocess overhead."""

    name = "kimi-k2.6"

    def __init__(
        self,
        model: str = KIMI_MODEL,
        base_url: str = KIMI_BASE_URL,
        timeout_s: int = 120,
        thinking: bool = False,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.thinking = thinking

    async def filing(self, prompt: str, schema: type[M]) -> M:
        """Generate structured output validated against *schema*."""
        text = await self.generate(prompt)
        return _parse_json_to_schema(text, schema)

    async def generate(self, prompt: str) -> str:
        """Generate raw text from *prompt*."""
        access_token = await _ensure_fresh_token()
        body: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.3,
        }
        if not self.thinking:
            body["thinking"] = {"type": "disabled"}

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if r.status_code == 401:
                # Token may have expired between check and request; retry once
                access_token = await _ensure_fresh_token()
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            r.raise_for_status()
            payload = r.json()

        return _extract_content(payload)


# ------------------------------------------------------------------
# CLI fallback — kept for emergencies or environments without HTTP
# access to the Kimi API.
# ------------------------------------------------------------------
class KimiCLISynthesizer:
    """Subprocess-based synthesizer using the local kimi CLI."""

    name = "kimi-k2.6"

    def __init__(
        self,
        config_file: str = "/app/dispatch/kimi-config.toml",
        timeout_s: int = 1200,
        thinking: bool = False,
    ):
        self.config_file = config_file
        self.timeout_s = timeout_s
        self.thinking = thinking

    async def generate(self, prompt: str) -> str:
        """Generate raw text from *prompt*."""
        cmd = [
            "kimi",
            "-p",
            prompt,
            "--print",
            "--final-message-only",
            "--config-file",
            self.config_file,
        ]
        if not self.thinking:
            cmd.append("--no-thinking")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"kimi timeout after {self.timeout_s}s")

        if proc.returncode != 0:
            raise RuntimeError(
                f"kimi exited {proc.returncode}: {stderr.decode()[:500]}"
            )

        return stdout.decode().strip()

    async def filing(self, prompt: str, schema: type[M]) -> M:
        """Generate structured output validated against *schema*."""
        text = await self.generate(prompt)
        return _parse_json_to_schema(text, schema)


def _extract_json(text: str) -> str:
    """Extract the first balanced JSON object from *text*."""
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON object found in model output: {text[:200]}")
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError(f"unbalanced braces in model output: {text[:200]}")


def _parse_json_to_schema(text: str, schema: type[M]) -> M:
    """Find JSON object in model reply, parse, validate against pydantic schema."""
    text = re.sub(
        r"^```(?:json)?\s*\n?|\n?```\s*$", "", text.strip(), flags=re.MULTILINE
    )
    if not text.startswith("{"):
        text = _extract_json(text)

    data = json.loads(text)
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        log.error("schema mismatch from kimi: %s", e)
        raise
