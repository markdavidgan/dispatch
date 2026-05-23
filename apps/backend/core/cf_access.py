"""Cloudflare Access verification — service token OR Access JWT.

The collector exposes private endpoints (/live, /brief/refresh, etc.)
that the Vercel frontend reaches through Cloudflare Tunnel + Access.
Two acceptable proofs:

  1. Cf-Access-Client-Id + Cf-Access-Client-Secret — service token used
     by Vercel's server-side routes when they call the collector.
  2. Cf-Access-Jwt-Assertion — signed JWT issued by Cloudflare for a
     human session. Presence-accepted for MVP since the tunnel already
     filters out unauthenticated requests; full JWKS verification is a
     Phase 1.5 hardening.
"""
import os

from fastapi import Header, HTTPException, status


async def verify_cf_access(
    cf_access_client_id: str | None = Header(default=None, alias="Cf-Access-Client-Id"),
    cf_access_client_secret: str | None = Header(default=None, alias="Cf-Access-Client-Secret"),
    cf_access_jwt_assertion: str | None = Header(default=None, alias="Cf-Access-Jwt-Assertion"),
) -> None:
    expected_id = os.environ.get("CF_ACCESS_CLIENT_ID")
    expected_secret = os.environ.get("CF_ACCESS_CLIENT_SECRET")

    if cf_access_client_id is not None or cf_access_client_secret is not None:
        if expected_id is None or expected_secret is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "cf-access not configured",
            )
        if cf_access_client_id != expected_id or cf_access_client_secret != expected_secret:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid service token")
        return

    if cf_access_jwt_assertion is not None:
        # Phase 1.5: verify the JWT against the team's JWKS.
        # For MVP we accept presence (since the tunnel only forwards
        # CF-validated requests).
        return

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "cf-access credentials required")
