"""report citations

Revision ID: 0003_report_citations
Revises: 0002_memory_embeddings
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_report_citations"
down_revision: str | None = "0002_memory_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("citation_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_report_citations_task_id"), "report_citations", ["task_id"], unique=False)
    op.create_index(op.f("ix_report_citations_report_id"), "report_citations", ["report_id"], unique=False)
    op.create_index(op.f("ix_report_citations_source_id"), "report_citations", ["source_id"], unique=False)
    op.create_index(op.f("ix_report_citations_chunk_id"), "report_citations", ["chunk_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_citations_chunk_id"), table_name="report_citations")
    op.drop_index(op.f("ix_report_citations_source_id"), table_name="report_citations")
    op.drop_index(op.f("ix_report_citations_report_id"), table_name="report_citations")
    op.drop_index(op.f("ix_report_citations_task_id"), table_name="report_citations")
    op.drop_table("report_citations")
