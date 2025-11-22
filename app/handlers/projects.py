from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services import users as users_service
from app.services import projects as projects_service

router = Router()


class NewProjectStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_currency = State()


def register(dp):
    dp.include_router(router)


# --- Вспомогательная функция для получения/создания пользователя ---


async def _get_or_create_user(tg_user: types.User) -> dict:
    return await users_service.get_or_create_user_by_telegram_id(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )


# --- СОЗДАНИЕ НОВОГО ПРОЕКТА ---


@router.message(Command("newproject"))
@router.message(F.text == "Новый проект")
async def cmd_newproject(message: types.Message, state: FSMContext):
    """Старт флоу создания проекта."""
    await state.set_state(NewProjectStates.waiting_for_name)
    await message.answer("Как назовём новый проект? (например: «Поездка в Китай»)")


@router.message(NewProjectStates.waiting_for_name)
async def newproject_name(message: types.Message, state: FSMContext):
    """Сохраняем имя проекта и спрашиваем валюту."""
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название проекта не может быть пустым. Введи ещё раз.")
        return

    await state.update_data(name=name)
    await state.set_state(NewProjectStates.waiting_for_currency)
    await message.answer(
        "В какой валюте по умолчанию считать траты? (например: RUB, CNY, EUR)"
    )


@router.message(NewProjectStates.waiting_for_currency)
async def newproject_currency(message: types.Message, state: FSMContext):
    """Создаём проект в базе и делаем его активным."""
    currency = (message.text or "").strip().upper() or "RUB"

    data = await state.get_data()
    name = data.get("name") or "Без названия"

    user = await _get_or_create_user(message.from_user)

    project = await projects_service.create_project(
        user_id=user["id"],
        name=name,
        base_currency=currency,
    )

    await state.clear()

    await message.answer(
        f"Готово, создал проект <b>«{project['name']}»</b> с базовой валютой <b>{currency}</b> "
        f"и сделал его активным.\n\n"
        f"Теперь просто присылай траты сообщениями, например:\n"
        f"<code>отели 65000</code> или <code>сувенир 10 юаней</code>."
    )


# --- СПИСКИ ПРОЕКТОВ (выбор активного / удаление) ---


async def _send_projects_inline_menu(
    message: types.Message,
    user_id: int,
    mode: str = "select",
):
    """
    Показываем список проектов инлайн-кнопками.

    mode:
      - 'select' — выбор активного проекта
      - 'delete' — удаление проекта
    """
    projects = await projects_service.get_projects(user_id)
    if not projects:
        if mode == "select":
            await message.answer(
                "У тебя пока нет проектов. Создай новый через кнопку «Новый проект»."
            )
        else:
            await message.answer("У тебя пока нет проектов, нечего удалять.")
        return

    if mode == "select":
        text = "Выбери проект, который сделать активным:"
        prefix = "setproj"
    else:
        text = "Выбери проект, который удалить (без подтверждения):"
        prefix = "delproj"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{p['name']} (ID {p['id']})",
                    callback_data=f"{prefix}:{p['id']}",
                )
            ]
            for p in projects
        ]
    )

    await message.answer(text, reply_markup=keyboard)


@router.message(Command("projects"))
@router.message(F.text == "Список проектов")
async def cmd_projects(message: types.Message):
    """Показать список проектов для выбора активного (кнопка или команда /projects)."""
    user = await _get_or_create_user(message.from_user)
    await _send_projects_inline_menu(message, user_id=user["id"], mode="select")


@router.message(F.text == "Удалить проект")
async def btn_delete_project_menu(message: types.Message):
    """Показать список проектов для удаления (кнопка «Удалить проект»)."""
    user = await _get_or_create_user(message.from_user)
    await _send_projects_inline_menu(message, user_id=user["id"], mode="delete")


# --- Команда /setproject (на всякий случай, если захочешь руками) ---


@router.message(Command("setproject"))
async def cmd_setproject(message: types.Message):
    """Старый способ выбрать активный проект по ID: /setproject 1"""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи ID проекта: например, <code>/setproject 1</code>.")
        return

    try:
        project_id = int(parts[1])
    except ValueError:
        await message.answer("ID проекта должен быть числом, пример: <code>/setproject 1</code>.")
        return

    user = await _get_or_create_user(message.from_user)

    project = await projects_service.set_active_project(
        user_id=user["id"],
        project_id=project_id,
    )
    if not project:
        await message.answer("Проект не найден или не принадлежит тебе.")
        return

    await message.answer(f"Активный проект теперь: <b>«{project['name']}»</b>.")


# --- CALLBACK-и от инлайн-кнопок ---


@router.callback_query(F.data.startswith("setproj:"))
async def cb_set_project(callback: types.CallbackQuery):
    """Обработка клика по проекту в режиме выбора активного."""
    try:
        project_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный ID проекта.", show_alert=True)
        return

    user = await _get_or_create_user(callback.from_user)

    project = await projects_service.set_active_project(
        user_id=user["id"],
        project_id=project_id,
    )
    if not project:
        await callback.answer("Проект не найден или не принадлежит тебе.", show_alert=True)
        return

    await callback.answer("Проект выбран.", show_alert=False)
    await callback.message.edit_text(
        f"Активный проект теперь: <b>«{project['name']}»</b>."
    )


@router.callback_query(F.data.startswith("delproj:"))
async def cb_delete_project(callback: types.CallbackQuery):
    """Обработка клика по проекту в режиме удаления."""
    try:
        project_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный ID проекта.", show_alert=True)
        return

    user = await _get_or_create_user(callback.from_user)

    # Эту функцию мы допишем в app/services/projects.py на следующем шаге
    ok = await projects_service.delete_project(
        user_id=user["id"],
        project_id=project_id,
    )
    if not ok:
        await callback.answer("Проект не найден или не принадлежит тебе.", show_alert=True)
        return

    await callback.answer("Проект удалён.", show_alert=False)
    await callback.message.edit_text("Проект удалён.")
