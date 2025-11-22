from aiogram import Router, types, F
from aiogram.filters import Command

from app.services import users as users_service
from app.services import projects as projects_service
from app.services import expenses as expenses_service
from app.services.parsing import basic_parse_expense_text
from app.services.exchange import get_rate_to_rub
from app.services.gpt_client import gpt_parse_expense

router = Router()


def register(dp):
    dp.include_router(router)


async def _process_expense_message(message: types.Message):
    text = message.text.strip()
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

    parsed = basic_parse_expense_text(text)

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
    currency = (parsed.get("currency") or project["base_currency"] or user["base_currency"] or "RUB").upper()
    category_name = (parsed.get("category") or "прочее").lower()
    description = parsed.get("description") or text

    category = await expenses_service.get_or_create_category(user_id=user["id"], name=category_name)

    if currency == "RUB":
        amount_rub = amount
    else:
        rate = await get_rate_to_rub(currency)
        amount_rub = float(rate) * amount

    await expenses_service.create_expense(
        user_id=user["id"],
        project_id=project["id"],
        category_id=category["id"],
        amount_original=amount,
        currency_original=currency,
        amount_rub=amount_rub,
        description=description,
    )

    totals = await expenses_service.get_project_totals(project["id"])
    by_currency = totals["by_currency"]
    total_rub = totals["total_rub"]

    lines = []

    pretty_amount_original = f"{amount:.2f}".rstrip("0").rstrip(".")
    pretty_amount_rub = f"{amount_rub:.2f}".rstrip("0").rstrip(".")

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


@router.message(Command("add"))
async def cmd_add(message: types.Message):
    await _process_expense_message(message)


@router.message(F.text & ~F.text.startswith("/"))
async def any_text(message: types.Message):
    await _process_expense_message(message)
