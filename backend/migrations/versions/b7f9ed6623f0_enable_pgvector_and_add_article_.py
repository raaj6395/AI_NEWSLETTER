"""enable pgvector and add article embedding

Revision ID: b7f9ed6623f0
Revises: 71636b66f5e3
Create Date: 2026-05-30 11:51:25.126521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'b7f9ed6623f0'
down_revision: Union[str, None] = '71636b66f5e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Matches Settings.embedding_dim (OpenAI text-embedding-3-small).
EMBEDDING_DIM = 1536


def upgrade() -> None:
    # The extension must exist before the vector column/index are created.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "articles",
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
    )

    # HNSW index for approximate nearest-neighbour search via cosine distance
    # (the `<=>` operator). Builds fine on an empty table.
    op.create_index(
        "ix_articles_embedding_hnsw",
        "articles",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_articles_embedding_hnsw", table_name="articles")
    op.drop_column("articles", "embedding")
    # The `vector` extension is left in place; dropping it could affect other
    # objects and is not necessary to revert this migration.
