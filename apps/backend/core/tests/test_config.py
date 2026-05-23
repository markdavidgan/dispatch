import os
import pytest
from core.config import Settings


def test_settings_reads_required_env(monkeypatch):
    monkeypatch.setenv("DB_PATH", "/tmp/test.db")
    monkeypatch.setenv("DISPATCH_TZ", "Asia/Manila")
    settings = Settings()
    assert settings.db_path == "/tmp/test.db"
    assert settings.dispatch_tz == "Asia/Manila"


def test_settings_defaults():
    settings = Settings()
    assert settings.host == "0.0.0.0"
    assert settings.port > 0
