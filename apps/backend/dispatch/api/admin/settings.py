"""Admin settings API — CRUD for encrypted DB-backed settings."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/admin/settings")


class SettingItem(BaseModel):
    key: str
    value: str


class SettingBulk(BaseModel):
    settings: dict[str, str]


@router.get("")
async def list_settings(request: Request, prefix: str = "") -> dict[str, Any]:
    """List all settings (decrypted). Optionally filter by key prefix."""
    store = request.app.state.settings_store
    keys = await store.list_keys(prefix)
    result: dict[str, str] = {}
    for k in keys:
        val = await store.get(k)
        if val is not None:
            result[k] = val
    return {"settings": result}


@router.get("/{key:path}")
async def get_setting(request: Request, key: str) -> dict[str, Any]:
    store = request.app.state.settings_store
    val = await store.get(key)
    if val is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": key, "value": val}


@router.put("/{key:path}")
async def put_setting(request: Request, key: str, body: SettingItem) -> dict[str, Any]:
    store = request.app.state.settings_store
    await store.set(key, body.value)
    return {"key": key, "value": body.value}


@router.delete("/{key:path}")
async def delete_setting(request: Request, key: str) -> dict[str, Any]:
    store = request.app.state.settings_store
    await store.delete(key)
    return {"key": key, "deleted": True}


@router.post("/bulk")
async def bulk_update(request: Request, body: SettingBulk) -> dict[str, Any]:
    """Update multiple settings at once. Useful for the setup wizard."""
    store = request.app.state.settings_store
    for k, v in body.settings.items():
        await store.set(k, v)
    return {"updated": list(body.settings.keys())}
