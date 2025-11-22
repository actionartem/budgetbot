from typing import Optional, Dict, Any

from .db import fetch_one, fetch_all, fetch_one_returning


async def get_or_create_category(user_id: int, name: str) -> Dict[str, Any]:
    lower_name = name.lower()
    category = await fetch_one(
        '''
        SELECT * FROM categories
        WHERE user_id = :user_id AND lower(name) = :name
        ''',
        {"user_id": user_id, "name": lower_name},
    )
    if category:
        return category

    category = await fetch_one_returning(
        '''
        INSERT INTO categories (user_id, name, slug, is_system)
        VALUES (:user_id, :name, :slug, FALSE)
        RETURNING *
        ''',
        {"user_id": user_id, "name": lower_name, "slug": lower_name},
    )
    return category


async def create_expense(
    user_id: int,
    project_id: int,
    category_id: Optional[int],
    amount_original: float,
    currency_original: str,
    amount_rub: float,
    description: str,
) -> Dict[str, Any]:
    exp = await fetch_one_returning(
        '''
        INSERT INTO expenses
        (user_id, project_id, category_id, amount_original, currency_original, amount_rub, description)
        VALUES
        (:user_id, :project_id, :category_id, :amount_original, :currency_original, :amount_rub, :description)
        RETURNING *
        ''',
        {
            "user_id": user_id,
            "project_id": project_id,
            "category_id": category_id,
            "amount_original": amount_original,
            "currency_original": currency_original,
            "amount_rub": amount_rub,
            "description": description,
        },
    )
    return exp


async def get_project_totals(project_id: int) -> Dict[str, Any]:
    rows_by_curr = await fetch_all(
        '''
        SELECT currency_original, SUM(amount_original) AS total
        FROM expenses
        WHERE project_id = :project_id
        GROUP BY currency_original
        ''',
        {"project_id": project_id},
    )

    by_currency = {row["currency_original"]: float(row["total"]) for row in rows_by_curr}

    row_total_rub = await fetch_one(
        '''
        SELECT SUM(amount_rub) AS total_rub
        FROM expenses
        WHERE project_id = :project_id
        ''',
        {"project_id": project_id},
    )

    total_rub = float(row_total_rub["total_rub"]) if row_total_rub and row_total_rub["total_rub"] is not None else 0.0

    return {
        "by_currency": by_currency,
        "total_rub": total_rub,
    }


async def get_project_category_totals_rub(project_id: int) -> Dict[str, float]:
    rows = await fetch_all(
        '''
        SELECT COALESCE(c.name, 'прочее') AS category_name, SUM(e.amount_rub) AS total_rub
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.project_id = :project_id
        GROUP BY category_name
        ''',
        {"project_id": project_id},
    )
    return {row["category_name"]: float(row["total_rub"]) for row in rows}
