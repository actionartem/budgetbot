from typing import Optional, Dict, Any

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


# --- БАЗОВЫЙ ПАРСЕР ТЕКСТА ТРАТЫ ---


def basic_parse_expense_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Очень простой разбор фразы вида:
    - "отели 65000"
    - "сувенир 10 юаней"
    - "еда 2000 rub"

    Логика:
      - первое слово -> категория
      - последнее числовое значение -> amount
      - токен рядом с числом, похожий на валюту -> currency
      - всё остальное -> description

    Если не смогли найти число — возвращаем None.
    """
    if not text:
        return None

    raw = text.strip()
    if not raw:
        return None

    parts = raw.split()
    if len(parts) < 2:
        return None

    category = parts[0].lower()

    amount = None
    amount_idx = None
    for i in range(len(parts) - 1, -1, -1):
        p = parts[i].replace(",", ".")
        try:
            amount = float(p)
            amount_idx = i
            break
        except ValueError:
            continue

    if amount is None:
        return None

    currency = None
    if amount_idx + 1 < len(parts):
        cur_token = parts[amount_idx + 1].strip().upper()
        if len(cur_token) in (2, 3, 4):
            currency = cur_token

    description = raw

    return {
        "category": category,
        "amount": amount,
        "currency": currency,
        "description": description,
    }


# --- ОСНОВНАЯ ЛОГИКА ОБРАБОТКИ ТРАТЫ ---


async def _process_expense_message(message: types.Message):
    # Берём текст из сообщения или подписи
    raw_text = (message.text or message.caption or "").strip()

    # Если это /add ..., срежем саму команду и оставим только трату
    if raw_text.startswith("/add"):
        text = raw_text[len("/add"):].strip()
    else:
        text = raw_text

    if not text:
        await message.answer(
            "Пришли, пожалуйста, описание траты.\n"
            "Например: <code>отели 65000</code> или <code>сувенир 10 юаней</code>."
        )
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
            "Создай новый через /newproject или кнопку «Новый проект», "
            "затем пришли трату ещё раз."
        )
        return

    # 1) Пытаемся распарсить простым парсером
    parsed = basic_parse_expense_text(text)

    # 2) Если не вышло — пробуем GPT
    use_gpt = parsed is None or parsed.get("amount") is None
    if use_gpt:
        gpt_result = await gpt_parse_expense(text)
        if gpt_result and gpt_result.get("amount"):
            parsed = gpt_result

    if not parsed or not parsed.get("amount"):
        await message.answer(
            "Не смог понять сумму траты 😔\n"
            "Попробуй формат типа: <code>отели 65000</code> или <code>сувенир 10 юаней</code>."
        )
        return

    amount = float(parsed["amount"])
    currency = (
        parsed.get("currency")
        or project.get("base_currency")
        or user.get("base_currency")
        or "RUB"
    ).upper()
    category_name = (parsed.get("category") or "прочее").lower()
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

    # Сохраняем трату
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

    pretty_amount_original = f"{amount:.2f}".rstrip("0").rstrip(".")
    pretty_amount_rub = f"{amount_rub:.2f}".rstrip("0").rstrip(".")

    lines = []

    lines.append(f"Записал трату в проект <b>«{project['name']}»</b> ✅")
    lines.append(f"Категория: <b>{category_name.capitalize()}</b>")

    if currency == "RUB":
        lines.append(f"Сумма: <b>{pretty_amount_original} RUB</b>")
    else:
        lines.append(
            f"Сумма: <b>{pretty_amount_original} {currency}</b> ≈ <b>{pretty_amount_rub} RUB</b>"
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


# --- КОМАНДЫ И ОБРАБОТЧИКИ ---


@router.message(Command("add"))
async def cmd_add(message: types.Message):
    """
    Команда /add — можно писать так:
    /add отели 65000
    /add сувенир 10 юаней
    """
    await _process_expense_message(message)


@router.message(F.text & ~F.text.startswith("/"))
async def any_text(message: types.Message):
    """
    Любой текст без слэша спереди пытаемся трактовать как трату.
    Кнопку «Получить сводку по текущему проекту» перенаправляем в отчёт,
    остальные кнопки главного меню здесь просто игнорируем.
    """
    text = (message.text or "").strip()

    if text == "Получить сводку по текущему проекту":
        # Локальный импорт, чтобы не было проблем с циклическими импортами при старте
        from app.handlers.reports import cmd_report

        await cmd_report(message)
        return

    if text in ("Новый проект", "Список проектов", "Удалить проект"):
        # Эти кнопки обрабатываются в других хендлерах
        return

    await _process_expense_message(message)
