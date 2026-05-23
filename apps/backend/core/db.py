"""Async SQLite helpers shared by services. Each service owns its own DB file."""
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncIterator


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @asynccontextmanager
    async def cursor(self) -> AsyncIterator[aiosqlite.Cursor]:
        assert self._conn is not None, "call connect() first"
        async with self._conn.cursor() as cur:
            yield cur
        await self._conn.commit()
