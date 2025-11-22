import os
import asyncio
from typing import Dict

import aiohttp

BASE_CURRENCY = os.getenv("BASE_CURRENCY", "RUB").upper()
CURRENCY_API_URL = os.getenv("CURRENCY_API_URL", "https://api.exchangerate.host/latest")

# Простейший кэш курсов, чтобы не дёргать API на каждый чих
_rates_cache: Dict[str, float] = {}
_cache_lock = asyncio.Lock()


async def get_rate_to_rub(currency: str) -> float:
    """
    Возвращает курс: сколько RUB за 1 единицу валюты currency.
    Если что-то пошло не так с API — возвращаем 1.0, чтобы не ломать логику.
    """
    currency = (currency or BASE_CURRENCY).upper()

    # Если и так RUB — курс 1:1
    if currency == BASE_CURRENCY:
        return 1.0

    cache_key = f"{currency}->{BASE_CURRENCY}"

    async with _cache_lock:
        # Если уже запрашивали — берём из кэша
        if cache_key in _rates_cache:
            return _rates_cache[cache_key]

        params = {
            "base": currency,
            "symbols": BASE_CURRENCY,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(CURRENCY_API_URL, params=params, timeout=5) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            rate = float(data["rates"][BASE_CURRENCY])
        except Exception as e:
            # Логируем в консоль и фоллбэк на 1.0, чтобы бот не падал
            print(f"[currency] error fetching rate {currency}->{BASE_CURRENCY}: {e}")
            rate = 1.0

        _rates_cache[cache_key] = rate
        return rate
