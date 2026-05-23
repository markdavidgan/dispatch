import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from core.cf_access import verify_cf_access


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "markdavidgan.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD_API", "deadbeef")
    a = FastAPI()

    @a.get("/private", dependencies=[Depends(verify_cf_access)])
    async def private():
        return {"ok": True}

    return a


def test_rejects_unauth(app):
    r = TestClient(app).get("/private")
    assert r.status_code == 401


def test_accepts_service_token(app):
    r = TestClient(app).get("/private", headers={
        "Cf-Access-Client-Id": "test-client-id",
        "Cf-Access-Client-Secret": "test-client-secret",
    })
    assert r.status_code == 200


def test_rejects_wrong_service_token(app):
    r = TestClient(app).get("/private", headers={
        "Cf-Access-Client-Id": "test-client-id",
        "Cf-Access-Client-Secret": "wrong",
    })
    assert r.status_code == 403


def test_accepts_jwt_presence(app):
    # MVP: presence-accepted. Full JWKS verification is Phase 1.5.
    r = TestClient(app).get("/private", headers={
        "Cf-Access-Jwt-Assertion": "eyJ.fake-jwt.body",
    })
    assert r.status_code == 200
