"""Shared fixtures for dispatch tests."""
import asyncio
import pytest
from core.db import Database
from dispatch import schema_init


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    database = Database(path)

    async def _setup():
        await database.connect()
        await schema_init.apply(database)

    asyncio.run(_setup())
    yield database

    async def _teardown():
        await database.close()

    asyncio.run(_teardown())
