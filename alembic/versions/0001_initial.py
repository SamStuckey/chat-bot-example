"""Penny's schema, created on an empty database.

Accounts, the catalog, saved user data, content, and conversation storage,
including the FTS5 history index and the partial unique indexes.

Revision ID: 0001
Revises:
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP = sa.String  # UTC ISO 8601 text (penny.db.UtcDateTime)


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("time_zone", sa.String(), nullable=True),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_users_school_id", "users", ["school_id"])
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("purchased_at", TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"])
    op.create_index("ix_purchases_product_id", "purchases", ["product_id"])
    op.create_table(
        "referral_codes",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("starts_at", TIMESTAMP(), nullable=False),
        sa.Column("ends_at", TIMESTAMP(), nullable=False),
    )
    op.create_table(
        "guidance_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("expires_at", TIMESTAMP(), nullable=True),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
        sa.Column("updated_at", TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_guidance_notes_user_id", "guidance_notes", ["user_id"])
    op.create_table(
        "avoided_products",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), primary_key=True),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_table(
        "content_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("content_class", sa.String(), nullable=False),
        sa.Column("load", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("ingested_at", sa.String(), nullable=False),
    )
    op.create_index(
        "uq_content_documents_active_name",
        "content_documents",
        ["name"],
        unique=True,
        sqlite_where=sa.text("active = 1"),
    )
    op.create_table(
        "turns",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("request_text_hash", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("content_version", sa.String(), nullable=False),
        sa.Column("app_version", sa.String(), nullable=False),
        sa.Column("started_at", TIMESTAMP(), nullable=False),
        sa.Column("ended_at", TIMESTAMP(), nullable=True),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_turns_user_idempotency_key"),
    )
    op.create_index("ix_turns_user_id", "turns", ["user_id"])
    op.create_index(
        "uq_turns_one_in_progress",
        "turns",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("status = 'in_progress'"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("turn_id", sa.String(), sa.ForeignKey("turns.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("parts", sa.JSON(), nullable=False),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_messages_turn_id", "messages", ["turn_id"])
    op.execute(
        "CREATE VIRTUAL TABLE messages_fts USING fts5("
        "text, user_id UNINDEXED, message_id UNINDEXED, tokenize = 'porter unicode61')"
    )
    op.create_table(
        "model_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("turn_id", sa.String(), sa.ForeignKey("turns.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("payload", sa.String(), nullable=False),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_model_messages_user_seq", "model_messages", ["user_id", "id"])
    op.create_index("ix_model_messages_turn_id", "model_messages", ["turn_id"])
    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "covers_through_model_message_id",
            sa.Integer(),
            sa.ForeignKey("model_messages.id"),
            nullable=False,
        ),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("payload", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("content_version", sa.String(), nullable=False),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_summaries_user_id", "summaries", ["user_id"])
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("turn_id", sa.String(), sa.ForeignKey("turns.id"), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_tool_calls_user_id", "tool_calls", ["user_id"])
    op.create_index("ix_tool_calls_turn_id", "tool_calls", ["turn_id"])
    op.create_table(
        "message_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message_id", sa.String(), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("created_at", TIMESTAMP(), nullable=False),
        sa.Column("updated_at", TIMESTAMP(), nullable=False),
        sa.UniqueConstraint("user_id", "message_id", name="uq_feedback_user_message"),
    )


def downgrade() -> None:
    op.drop_table("message_feedback")
    op.drop_table("tool_calls")
    op.drop_table("summaries")
    op.drop_table("model_messages")
    op.execute("DROP TABLE messages_fts")
    op.drop_table("messages")
    op.drop_table("turns")
    op.drop_table("content_documents")
    op.drop_table("avoided_products")
    op.drop_table("guidance_notes")
    op.drop_table("promotions")
    op.drop_table("referral_codes")
    op.drop_table("purchases")
    op.drop_table("products")
    op.drop_table("users")
    op.drop_table("schools")
