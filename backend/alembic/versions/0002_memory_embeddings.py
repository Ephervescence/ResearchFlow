"""memory embeddings

Revision ID: 0002_memory_embeddings
Revises: 0001_initial_schema
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0002_memory_embeddings"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("memories", sa.Column("task_id", sa.Integer(), nullable=True))
    op.add_column("memories", sa.Column("embedding", Vector(384), nullable=True))
    op.create_index(op.f("ix_memories_task_id"), "memories", ["task_id"], unique=False)
    op.create_foreign_key("fk_memories_task_id_tasks", "memories", "tasks", ["task_id"], ["id"])
    op.drop_column("memories", "embedding_id")


def downgrade() -> None:
    op.add_column("memories", sa.Column("embedding_id", sa.String(length=255), nullable=True))
    op.drop_constraint("fk_memories_task_id_tasks", "memories", type_="foreignkey")
    op.drop_index(op.f("ix_memories_task_id"), table_name="memories")
    op.drop_column("memories", "embedding")
    op.drop_column("memories", "task_id")
