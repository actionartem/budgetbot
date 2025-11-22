import os
import time
import json
import asyncio
from typing import Dict, Tuple
from urllib.request import urlopen
from urllib.error import URLError

# Настройки API
API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "452867c7c0ecd5700db62526")
API_BASE = os.getenv("EXCHANGE_RATE_API_BASE", "https://v6.exchangerate-api.com/v6")

# Сколько секунд кэш считается свежим (по умолчанию 1 час)
CACHE_TTL = int(os.getenv("CURRENCY_CACHE_TTL", "3600"))

# Кэш курсов: храним "сколько RUB за 1 единицу валюты"
# Пример: {"USD": (79.5, 1732300000.0), ...}
_rates_cache: Dict[str, Tuple[float, float]] = {}


def _build_url() -> str:
    """
    Строим URL вида:
    https://v6.exchangerate-api.com/v6/<API_KEY>/latest/RUB
    """
    base = API_BASE.rstrip("/")
    return f"{base}/{API_KEY}/latest/RUB"


def _fetch_all_rates_sync() -> Dict[str, float]:
    """
    Синхронно ходим в exchangerate-api и получаем словарь:
    code -> RUB за 1 единицу code.

    Т.к. API отдаёт нам conversion_rates в виде
    "base_code": "RUB",
    "conversion_rates": { "USD": 0.01258, ... }

    Это значит: 1 RUB = 0.01258 USD.
    Нам нужно наоборот: 1 USD = 1 / 0.01258 RUB.
    """
    url = _build_url()

    with urlopen(url, timeout=5) as resp:
        data = json.load(resp)

    if data.get("result") != "success":
        raise ValueError(f"API error: {data.get('result')}")

    conv = data.get("conversion_rates") or {}
    if "RUB" not in conv:
        conv["RUB"] = 1.0

    result: Dict[str, float] = {}

    for code, rate in conv.items():
        code = str(code).upper()

        # API даёт: 1 RUB = rate * code
        # Нам надо: 1 code = X RUB
        # => X = 1 / rate
        if code == "RUB":
            result["RUB"] = 1.0
            continue

        try:
            r = float(rate)
            if r <= 0:
                continue
            rub_per_unit = 1.0 / r
            result[code] = rub_per_unit
        except (TypeError, ValueError):
            continue

    if not result:
        # На всякий случай хотя бы рубли
        result["RUB"] = 1.0

    return result


async def _ensure_cache() -> None:
    """
    Обновляем кэш, если он устарел или пустой.
    """
    global _rates_cache

    now = time.time()
    # если в кэше что-то есть и ещё не протухло — ничего не делаем
    if _rates_cache:
        # Берём любой элемент, чтобы проверить время
        _, (_, ts) = next(iter(_rates_cache.items()))
        if now - ts < CACHE_TTL:
            return

    # Иначе тянем новые курсы
    try:
        rates = await asyncio.to_thread(_fetch_all_rates_sync)
        _rates_cache = {code: (rate, now) for code, rate in rates.items()}
    except (URLError, OSError, ValueError) as e:
        print(f"[currency] failed to fetch rates from exchangerate-api: {e}")
        # Если кэша нет вообще — хотя бы RUB=1
        if not _rates_cache:
            _rates_cache = {"RUB": (1.0, now)}


async def get_rate_to_rub(currency: str) -> float:
    """
    Возвращает курс: сколько RUB за 1 единицу валюты.
    Примеры:
      get_rate_to_rub("USD") -> ~79.5
      get_rate_to_rub("CNY") -> ~11-12
    """
    if not currency:
        return 1.0

    code = currency.upper()
    if code == "RUB":
        return 1.0

    await _ensure_cache()

    pair = _rates_cache.get(code)
    if pair:
        rate, _ = pair
        return float(rate)

    # Если конкретной валюты нет в кэше — попробуем перезагрузить
    await _ensure_cache()
    pair = _rates_cache.get(code)
    if pair:
        rate, _ = pair
        return float(rate)

    # Совсем на крайний случай — считаем 1:1, чтобы не падать
    return 1.0
