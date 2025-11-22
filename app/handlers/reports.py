from __future__ import annotations

from typing import Dict, Any

from aiogram import Router, types, F
from aiogram.filters import Command

from app.services import users as users_service
from app.services import projects as projects_service
from app.services import expenses as expenses_service
from app.services.gpt_client import gpt_summarize_report

router = Router()

# Текст кнопки из главного меню
BUTTON_REPORT_TEXT = "Получить сводку по текущему проекту"


def register(dp):
    dp.include_router(router)


async def _send_report(message: types.Message) -> None:
    """
    Общая функция: строит отчёт и отправляет его.
    Вызывается и из /report, и из кнопки.
    """
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
            "У тебя нет активного проекта.\n"
            "Создай проект через /newproject."
        )
        return

    totals: Dict[str, Any] = await expenses_service.get_project_totals(project["id"])
    cat_totals: Dict[str, Any] = await expenses_service.get_project_category_totals_rub(
        project["id"]
    )

    by_currency = totals["by_currency"]
    total_rub = totals["total_rub"]

    lines = [f"Отчёт по проекту <b>«{project['name']}»</b>"]

    # Блок по валютам
    if by_currency:
        lines.append("")
        lines.append("По валютам:")
        for code, val in by_currency.items():
            pretty = f"{float(val):.2f}".rstrip("0").rstrip(".")
            lines.append(f"• {code}: <b>{pretty}</b>")

    # Блок по категориям
    if cat_totals:
        lines.append("")
        lines.append("Разбивка по категориям (в RUB):")
        for cat_name, val in cat_totals.items():
            pretty = f"{float(val):.2f}".rstrip("0").rstrip(".")
            lines.append(f"• {cat_name.capitalize()}: <b>{pretty}</b>")

    # Итог в рублях
    pretty_total_rub = f"{float(total_rub):.2f}".rstrip("0").rstrip(".")
    lines.append("")
    lines.append(f"Итоговый бюджет в RUB: <b>{pretty_total_rub} RUB</b>")

    await message.answer("\n".join(lines))

    # Структура для GPT-сводки
    structured = {
        "project_name": project["name"],
        "totals_by_currency": by_currency,
        "categories_in_rub": cat_totals,
        "total_in_rub": total_rub,
    }
    summary = await gpt_summarize_report(structured)
    if summary:
        await message.answer(summary)


# Команда /report
@router.message(Command("report"))
async def cmd_report(message: types.Message):
    await _send_report(message)


# Нажатие кнопки "Получить сводку по текущему проекту"
# Ловим ЛЮБОЙ текст и фильтруем уже внутри
@router.message(F.text)
async def report_button(message: types.Message):
    if message.text != BUTTON_REPORT_TEXT:
        return

    await _send_report(message)
