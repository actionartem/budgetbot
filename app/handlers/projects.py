from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.services import users as users_service
from app.services import projects as projects_service

router = Router()


class NewProjectStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_currency = State()


def register(dp):
    dp.include_router(router)


@router.message(Command("newproject"))
async def cmd_newproject(message: types.Message, state: FSMContext):
    await state.set_state(NewProjectStates.waiting_for_name)
    await message.answer("Как назовём новый проект? (например: «Поездка в Китай»)")


@router.message(NewProjectStates.waiting_for_name)
async def newproject_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(NewProjectStates.waiting_for_currency)
    await message.answer("В какой валюте по умолчанию считать траты? (например: RUB, CNY, EUR)")


@router.message(NewProjectStates.waiting_for_currency)
async def newproject_currency(message: types.Message, state: FSMContext):
    currency = message.text.strip().upper() or "RUB"
    data = await state.get_data()
    name = data.get("name") or "Без названия"

    tg_user = message.from_user
    user = await users_service.get_or_create_user_by_telegram_id(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

    project = await projects_service.create_project(user_id=user["id"], name=name, base_currency=currency)

    await state.clear()

    await message.answer(
        f"Готово, создал проект <b>«{project['name']}»</b> с базовой валютой <b>{currency}</b> "
        f"и сделал его активным.\n\n"
        f"Теперь просто присылай траты сообщениями, например:\n"
        f"<code>отели 65000</code> или <code>сувенир 10 юаней</code>."
    )


@router.message(Command("projects"))
async def cmd_projects(message: types.Message):
    tg_user = message.from_user
    user = await users_service.get_or_create_user_by_telegram_id(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

    projects = await projects_service.get_projects(user["id"])
    active = await projects_service.get_active_project(user["id"])

    if not projects:
        await message.answer(
            "У тебя пока нет проектов.\nСоздай первый через /newproject."
        )
        return

    lines = ["Твои проекты:"]
    for p in projects:
        mark = " (активен)" if active and active["id"] == p["id"] else ""
        lines.append(f"{p['id']}. {p['name']}{mark}")
    lines.append("")
    lines.append("Сделать проект активным: /setproject <id>")
    lines.append("Удалить проект: /deleteproject <id>")

    await message.answer("\n".join(lines))


@router.message(Command("setproject"))
async def cmd_setproject(message: types.Message):
    args = message.text.strip().split()
    if len(args) < 2:
        await message.answer("Укажи ID проекта: /setproject <id>")
        return
    try:
        project_id = int(args[1])
    except ValueError:
        await message.answer("ID проекта должен быть числом, например: /setproject 1")
        return

    tg_user = message.from_user
    user = await users_service.get_or_create_user_by_telegram_id(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

    project = await projects_service.set_active_project(user_id=user["id"], project_id=project_id)
    if not project:
        await message.answer("Проект с таким ID не найден или не принадлежит тебе.")
        return

    await message.answer(f"Активный проект теперь: <b>«{project['name']}»</b>.")


@router.message(Command("deleteproject"))
async def cmd_deleteproject(message: types.Message):
    args = message.text.strip().split()
    if len(args) < 2:
        await message.answer("Укажи ID проекта: /deleteproject <id>")
        return
    try:
        project_id = int(args[1])
    except ValueError:
        await message.answer("ID проекта должен быть числом, например: /deleteproject 1")
        return

    tg_user = message.from_user
    user = await users_service.get_or_create_user_by_telegram_id(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

    ok = await projects_service.delete_project(user_id=user["id"], project_id=project_id)
    if not ok:
        await message.answer("Проект с таким ID не найден или не принадлежит тебе.")
        return

    await message.answer("Проект удалён. Можешь создать новый через /newproject.")
