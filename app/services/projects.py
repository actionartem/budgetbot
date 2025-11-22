from typing import Optional, Dict, Any, List

from .db import fetch_one, fetch_all, execute, fetch_one_returning


async def get_active_project(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить текущий активный проект пользователя (или None, если его нет).
    """
    return await fetch_one(
        """
        SELECT *
        FROM projects
        WHERE user_id = :user_id
          AND is_deleted = FALSE
          AND is_active = TRUE
        """,
        {"user_id": user_id},
    )


async def get_projects(user_id: int) -> List[Dict[str, Any]]:
    """
    Получить список всех НЕ удалённых проектов пользователя.
    """
    return await fetch_all(
        """
        SELECT *
        FROM projects
        WHERE user_id = :user_id
          AND is_deleted = FALSE
        ORDER BY id
        """,
        {"user_id": user_id},
    )


async def create_project(user_id: int, name: str, base_currency: str) -> Dict[str, Any]:
    """
    Создать новый проект и сделать его активным.
    Все остальные проекты пользователя становятся неактивными.
    """
    # Сбрасываем активность у всех проектов пользователя
    await execute(
        """
        UPDATE projects
        SET is_active = FALSE
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )

    # Создаём новый проект и сразу делаем его активным
    project = await fetch_one_returning(
        """
        INSERT INTO projects (user_id, name, base_currency, is_active, is_deleted)
        VALUES (:user_id, :name, :base_currency, TRUE, FALSE)
        RETURNING *
        """,
        {
            "user_id": user_id,
            "name": name,
            "base_currency": base_currency,
        },
    )
    return project


async def set_active_project(user_id: int, project_id: int) -> Optional[Dict[str, Any]]:
    """
    Сделать выбранный проект активным.
    Возвращает проект, если всё ок, или None, если проект не найден / чужой / удалён.
    """
    project = await fetch_one(
        """
        SELECT *
        FROM projects
        WHERE id = :id
          AND user_id = :user_id
          AND is_deleted = FALSE
        """,
        {"id": project_id, "user_id": user_id},
    )
    if not project:
        return None

    # Сбрасываем активность у всех проектов пользователя
    await execute(
        """
        UPDATE projects
        SET is_active = FALSE
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )

    # Делаем активным только выбранный проект
    await execute(
        """
        UPDATE projects
        SET is_active = TRUE
        WHERE id = :id
        """,
        {"id": project_id},
    )

    return await get_active_project(user_id)


async def delete_project(user_id: int, project_id: int) -> bool:
    """
    Помечает проект как удалённый (soft delete) и снимает с него флаг is_active.
    Ничего физически не удаляем из БД, просто is_deleted = TRUE.
    Возвращает True, если проект реально существовал и был помечен как удалённый.
    """
    project = await fetch_one(
        """
        SELECT *
        FROM projects
        WHERE id = :id
          AND user_id = :user_id
          AND is_deleted = FALSE
        """,
        {"id": project_id, "user_id": user_id},
    )
    if not project:
        return False

    await execute(
        """
        UPDATE projects
        SET is_deleted = TRUE,
            is_active  = FALSE
        WHERE id = :id
        """,
        {"id": project_id},
    )

    return True
