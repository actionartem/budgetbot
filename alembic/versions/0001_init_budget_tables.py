from alembic import op
import sqlalchemy as sa

revision = "0001_init_budget_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("telegram_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("username", sa.Text),
        sa.Column("first_name", sa.Text),
        sa.Column("last_name", sa.Text),
        sa.Column("base_currency", sa.String(3), server_default="RUB", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("base_currency", sa.String(3), server_default="RUB", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index(
        "idx_projects_user",
        "projects",
        ["user_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.Text),
        sa.Column("is_system", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_categories_user_name",
        "categories",
        ["user_id", "name"],
    )

    op.create_table(
        "expenses",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.BigInteger, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.BigInteger, sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("amount_original", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency_original", sa.String(3), nullable=False),
        sa.Column("amount_rub", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_expenses_project", "expenses", ["project_id"])
    op.create_index("idx_expenses_project_category", "expenses", ["project_id", "category_id"])

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("currency_code", sa.String(3), nullable=False, unique=True),
        sa.Column("rate_to_rub", sa.Numeric(18, 6), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("exchange_rates")
    op.drop_index("idx_expenses_project_category", table_name="expenses")
    op.drop_index("idx_expenses_project", table_name="expenses")
    op.drop_table("expenses")
    op.drop_constraint("uq_categories_user_name", "categories", type_="unique")
    op.drop_table("categories")
    op.drop_index("idx_projects_user", table_name="projects")
    op.drop_table("projects")
    op.drop_index("idx_users_telegram_id", table_name="users")
    op.drop_table("users")
