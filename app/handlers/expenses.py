from __future__ import annotations

from typing import Optional, Dict, Any, List
import re

from aiogram import Router, types, F
from aiogram.filters import Command

from app.services import users as users_service
from app.services import projects as projects_service
from app.services import expenses as expenses_service
from app.services.currency import get_rate_to_rub
from app.services.gpt_client import gpt_parse_expense

router = Router()


def register(dp):
    dp.include_router(router)


# --- Тексты кнопок главного меню, которые НЕ должны попадать в парсер трат ---

MAIN_MENU_BUTTONS = {
    "Новый проект",
    "Список проектов",
    "Удалить проект",
    "Получить сводку по текущему проекту",
}


# --- Нормализация валют -------------------------------------------------------

CURRENCY_SYNONYMS = {
    "RUB": (
        "rub",
        "руб",
        "рубль",
        "рубля",
        "рублей",
        "рубли",
        "₽",
    ),
    "USD": (
        "usd",
        "доллар",
        "доллара",
        "долларов",
        "бакс",
        "бакса",
        "баксов",
        "$",
        "дол",
        "долл",
    ),
    "EUR": (
        "eur",
        "евро",
        "€",
    ),
    "CNY": (
        "cny",
        "юань",
        "юаня",
        "юаней",
        "юани",
        "юан",
        "yuan",
    ),
    "JPY": (
        "jpy",
        "йена",
        "йены",
        "йен",
        "иена",
        "иены",
        "иен",
        "yen",
    ),
}


def normalize_currency_token(token: str) -> Optional[str]:
    """
    Приводим слово типа 'рублей', 'юаней', 'usd', '$' -> ISO-коду.
    """
    t = token.strip().lower()
    t = t.strip(".,;:()[]{}")

    for code, variants in CURRENCY_SYNONYMS.items():
        if t == code.lower() or t in variants:
            return code

    return None


# --- Простейший парсер текста траты ------------------------------------------


def basic_parse_expense_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Пытаемся вытащить категорию, сумму и валюту из простого текста:
    - "отели 65000"
    - "яблоки 1 доллар"
    - "ягоды 20 юаней"
    - "сахар 2 CNY"
    """
    s = (text or "").strip()
    if not s:
        return None

    # Ищем ПОСЛЕДНЕЕ число в строке
    m = re.search(
        r"(?P<prefix>.*?)(?P<amount>\d+(?:[.,]\d+)?)(?P<suffix>.*)$",
        s,
    )
    if not m:
        return None

    prefix = (m.group("prefix") or "").strip()
    suffix = (m.group("suffix") or "").strip()
    amount_str = m.group("amount").replace(",", ".")
    try:
        amount = float(amount_str)
    except ValueError:
        return None

    # Категория — всё, что до числа (например, "отель Пекин")
    category = prefix if prefix else "прочее"
    category = category.strip("•-–").strip()

    currency: Optional[str] = None
    if suffix:
        # Берём первое слово после числа ("юаней", "рублей", "CNY" и т.п.)
        first_word = suffix.split()[0]
        currency = normalize_currency_token(first_word)

    return {
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": text,
    }


# --- Основная логика обработки трат ------------------------------------------


async def _process_expense_message(message: types.Message):
    text = (message.text or "").strip()

    # На всякий случай: если вдруг сюда всё-таки пролезла кнопка — выходим.
    if text in MAIN_MENU_BUTTONS:
        return

    tg_user = message.from_user

    user = await users_service.get_or_create_user_by_telegram_id(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

    project = await projects_service.get_active_project(user["id"])
    if not project:
        await message.answer(
            "У тебя пока нет активного проекта.\n"
            "Создай новый через /newproject, затем пришли трату ещё раз."
        )
        return

    # 1. Пытаемся распарсить сами
    parsed = basic_parse_expense_text(text)

    # 2. Если не получилось или нет суммы — пробуем GPT
    use_gpt = parsed is None or parsed.get("amount") is None
    if use_gpt:
        gpt_result = await gpt_parse_expense(text)
        if gpt_result and gpt_result.get("amount"):
            # Если GPT не указал валюту, но в тексте она есть — попробуем добрать сами
            if not gpt_result.get("currency"):
                m_cur = re.search(r"\d+(?:[.,]\d+)?\s+(\S+)", text)
                if m_cur:
                    cur = normalize_currency_token(m_cur.group(1))
                    if cur:
                        gpt_result["currency"] = cur
            parsed = gpt_result

    if not parsed or not parsed.get("amount"):
        await message.answer(
            "Не смог понять сумму траты 😔\n"
            "Попробуй формат типа: <code>отели 65000</code> "
            "или <code>сувенир 10 юаней</code>."
        )
        return

    amount = float(parsed["amount"])

    # Выбираем валюту: из парсера -> из проекта -> из пользователя -> RUB
    raw_currency = (
        (parsed.get("currency") or "")
        or (project.get("base_currency") or "")
        or (user.get("base_currency") or "")
    )
    currency = raw_currency.upper() if raw_currency else "RUB"

    # Нормализуем, если это русское слово типа "юаней"
    norm_from_word = normalize_currency_token(currency)
    if norm_from_word:
        currency = norm_from_word

    supported_currencies = {"RUB", "USD", "EUR", "CNY", "JPY"}
    if currency not in supported_currencies:
        currency = "RUB"

    category_name = (parsed.get("category") or "прочее").strip().lower()
    description = parsed.get("description") or text

    # Категория
    category = await expenses_service.get_or_create_category(
        user_id=user["id"],
        name=category_name,
    )

    # Пересчёт в рубли
    if currency == "RUB":
        amount_rub = amount
    else:
        rate = await get_rate_to_rub(currency)
        amount_rub = float(rate) * amount

    # Сохраняем трату с оригинальной валютой и суммой в рублях
    await expenses_service.create_expense(
        user_id=user["id"],
        project_id=project["id"],
        category_id=category["id"],
        amount_original=amount,
        currency_original=currency,
        amount_rub=amount_rub,
        description=description,
    )

    # Итоги по проекту
    totals = await expenses_service.get_project_totals(project["id"])
    by_currency = totals["by_currency"]
    total_rub = totals["total_rub"]

    lines: List[str] = []

    pretty_amount_original = f"{amount:.2f}".rstrip("0").rstrip(".")
    pretty_amount_rub = f"{amount_rub:.2f}".rstrip("0").rstrip(".")

    lines.append(f"Записал трату в проект <b>«{project['name']}»</b> ✅")
    lines.append(f"Категория: <b>{category_name.capitalize()}</b>")
    if currency == "RUB":
        lines.append(f"Сумма: <b>{pretty_amount_original} RUB</b>")
    else:
        lines.append(
            f"Сумма: <b>{pretty_amount_original} {currency}</b> "
            f"≈ <b>{pretty_amount_rub} RUB</b>"
        )

    lines.append("")
    lines.append("Итоги по проекту:")

    for curr_code, total_val in by_currency.items():
        pretty_total = f"{float(total_val):.2f}".rstrip("0").rstrip(".")
        lines.append(f"• {curr_code}: <b>{pretty_total}</b>")

    pretty_total_rub = f"{float(total_rub):.2f}".rstrip("0").rstrip(".")
    lines.append("")
    lines.append(f"Общий бюджет в RUB: <b>{pretty_total_rub} RUB</b>")

    await message.answer("\n".join(lines))


@router.message(Command("add"))
async def cmd_add(message: types.Message):
    await _process_expense_message(message)


# ВАЖНО: здесь мы фильтром исключаем ВСЕ кнопки главного меню.
# Тогда сообщение "Получить сводку по текущему проекту" вообще не попадёт
# в этот хендлер и спокойно дойдёт до reports.py.
@router.message(
    F.text
    & ~F.text.startswith("/")
    & ~F.text.in_(list(MAIN_MENU_BUTTONS))
)
async def any_text(message: types.Message):
    await _process_expense_message(message)
