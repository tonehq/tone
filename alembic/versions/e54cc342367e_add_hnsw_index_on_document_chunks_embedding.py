"""add hnsw index on document_chunks embedding

Revision ID: e54cc342367e
Revises: 3e2379d411b5
Create Date: 2026-05-11 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e54cc342367e'
down_revision = '3e2379d411b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'ix_document_chunks_embedding_hnsw',
        'document_chunks',
        ['embedding'],
        unique=False,
        postgresql_using='hnsw',
        postgresql_with={'m': 16, 'ef_construction': 64},
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    op.drop_index('ix_document_chunks_embedding_hnsw', table_name='document_chunks')
