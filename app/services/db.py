import asyncio
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings

engine: Engine = create_engine(settings.database_url, future=True)


async def fetch_one(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    def _run():
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            row = result.mappings().first()
            return dict(row) if row else None

    return await asyncio.to_thread(_run)


async def fetch_all(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    def _run():
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return [dict(row) for row in result.mappings().all()]

    return await asyncio.to_thread(_run)


async def execute(query: str, params: Optional[Dict[str, Any]] = None) -> None:
    def _run():
        with engine.begin() as conn:
            conn.execute(text(query), params or {})

    await asyncio.to_thread(_run)


async def fetch_one_returning(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Для INSERT ... RETURNING *"""
    def _run():
        with engine.begin() as conn:
            result = conn.execute(text(query), params or {})
            row = result.mappings().first()
            return dict(row) if row else None

    return await asyncio.to_thread(_run)
