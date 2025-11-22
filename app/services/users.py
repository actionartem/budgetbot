from typing import Optional, Dict, Any

from .db import fetch_one, fetch_one_returning
from app.config import settings


async def get_or_create_user_by_telegram_id(
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
) -> Dict[str, Any]:
    user = await fetch_one(
        "SELECT * FROM users WHERE telegram_id = :telegram_id",
        {"telegram_id": telegram_id},
    )
    if user:
        return user

    user = await fetch_one_returning(
        '''
        INSERT INTO users (telegram_id, username, first_name, last_name, base_currency)
        VALUES (:telegram_id, :username, :first_name, :last_name, :base_currency)
        RETURNING *
        ''',
        {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "base_currency": settings.base_currency,
        },
    )
    return user
