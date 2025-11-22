from typing import Optional, Dict, Any, List

from .db import fetch_one, fetch_all, execute, fetch_one_returning


async def get_active_project(user_id: int) -> Optional[Dict[str, Any]]:
    return await fetch_one(
        "SELECT * FROM projects WHERE user_id = :user_id AND is_deleted = FALSE AND is_active = TRUE",
        {"user_id": user_id},
    )


async def get_projects(user_id: int) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM projects WHERE user_id = :user_id AND is_deleted = FALSE ORDER BY id",
        {"user_id": user_id},
    )


async def create_project(user_id: int, name: str, base_currency: str) -> Dict[str, Any]:
    await execute(
        "UPDATE projects SET is_active = FALSE WHERE user_id = :user_id",
        {"user_id": user_id},
    )

    project = await fetch_one_returning(
        '''
        INSERT INTO projects (user_id, name, base_currency, is_active, is_deleted)
        VALUES (:user_id, :name, :base_currency, TRUE, FALSE)
        RETURNING *
        ''',
        {
            "user_id": user_id,
            "name": name,
            "base_currency": base_currency,
        },
    )
    return project


async def set_active_project(user_id: int, project_id: int) -> Optional[Dict[str, Any]]:
    project = await fetch_one(
        "SELECT * FROM projects WHERE id = :id AND user_id = :user_id AND is_deleted = FALSE",
        {"id": project_id, "user_id": user_id},
    )
    if not project:
        return None

    await execute(
        "UPDATE projects SET is_active = FALSE WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    await execute(
        "UPDATE projects SET is_active = TRUE WHERE id = :id",
        {"id": project_id},
    )

    return await get_active_project(user_id)


async def delete_project(user_id: int, project_id: int) -> bool:
    project = await fetch_one(
        "SELECT * FROM projects WHERE id = :id AND user_id = :user_id AND is_deleted = FALSE",
        {"id": project_id, "user_id": user_id},
    )
    if not project:
        return False

    await execute(
        "UPDATE projects SET is_deleted = TRUE, is_active = FALSE WHERE id = :id",
        {"id": project_id},
    )
    return True
