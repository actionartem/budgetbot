from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

import httpx

from app.config import settings
from .db import fetch_one, fetch_one_returning

CACHE_TTL_HOURS = 24


async def _get_cached_rate(currency_code: str) -> Optional[Dict[str, Any]]:
    return await fetch_one(
        """
        SELECT * FROM exchange_rates
        WHERE currency_code = :code
        """
        ,
        {"code": currency_code},
    )


async def _save_rate(currency_code: str, rate: Decimal) -> Dict[str, Any]:
    record = await fetch_one_returning(
        """
        INSERT INTO exchange_rates (currency_code, rate_to_rub, fetched_at)
        VALUES (:code, :rate, now())
        ON CONFLICT (currency_code) DO UPDATE
        SET rate_to_rub = EXCLUDED.rate_to_rub,
            fetched_at = EXCLUDED.fetched_at
        RETURNING *
        """
        ,
        {"code": currency_code, "rate": rate},
    )
    return record


async def _fetch_rate_from_api(currency_code: str) -> Decimal:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            settings.currency_api_url,
            params={"base": currency_code, "symbols": "RUB"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        rate = data["rates"]["RUB"]
        return Decimal(str(rate))


async def get_rate_to_rub(currency_code: str) -> Decimal:
    code = currency_code.upper()
    if code == "RUB":
        return Decimal("1.0")

    cached = await _get_cached_rate(code)
    if cached:
        fetched_at = cached["fetched_at"]
        if isinstance(fetched_at, datetime):
            age = datetime.now(timezone.utc) - fetched_at
            if age < timedelta(hours=CACHE_TTL_HOURS):
                return Decimal(str(cached["rate_to_rub"]))

    rate = await _fetch_rate_from_api(code)
    await _save_rate(code, rate)
    return rate
