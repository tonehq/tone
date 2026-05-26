"""Remove documents table, rename document_chunks to knowledge_base_chunks, add file_name/status/meta_data to uploads

Revision ID: e1f2a3b4c5d6
Revises: d5e6f7a8b9c0
Create Date: 2026-05-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns to uploads
    op.add_column('uploads', sa.Column('file_name', sa.String(512), nullable=True))
    op.add_column('uploads', sa.Column('status', sa.String(32), nullable=False, server_default='ready'))
    op.add_column('uploads', sa.Column('meta_data', JSONB, nullable=False, server_default='{}'))

    # 2. Migrate data from documents to uploads (file_name, status, meta_data)
    op.execute("""
        UPDATE uploads u
        SET file_name = d.file_name,
            status = d.status,
            meta_data = COALESCE(d.meta_data, '{}'::jsonb)
        FROM documents d
        WHERE d.upload_id = u.id
    """)

    # 3. Rename document_chunks -> knowledge_base_chunks
    op.rename_table('document_chunks', 'knowledge_base_chunks')

    # 4. Add upload_id column to knowledge_base_chunks, populate from documents, then drop document_id
    op.add_column('knowledge_base_chunks', sa.Column('upload_id', UUID(as_uuid=True), nullable=True))

    op.execute("""
        UPDATE knowledge_base_chunks kbc
        SET upload_id = d.upload_id
        FROM documents d
        WHERE kbc.document_id = d.id
    """)

    # Make upload_id NOT NULL and add FK + index
    op.alter_column('knowledge_base_chunks', 'upload_id', nullable=False)
    op.create_foreign_key(
        'fk_kb_chunks_upload_id', 'knowledge_base_chunks', 'uploads',
        ['upload_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index('ix_knowledge_base_chunks_upload_id', 'knowledge_base_chunks', ['upload_id'])

    # Drop old document_id column and its FK/index
    op.drop_constraint('document_chunks_document_id_fkey', 'knowledge_base_chunks', type_='foreignkey')
    op.drop_index('ix_document_chunks_document_id', table_name='knowledge_base_chunks')
    op.drop_column('knowledge_base_chunks', 'document_id')

    # 5. Drop documents table
    op.drop_table('documents')


def downgrade() -> None:
    # Recreate documents table
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('upload_id', UUID(as_uuid=True), sa.ForeignKey('uploads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_name', sa.String(512), nullable=False),
        sa.Column('content_type', sa.String(128), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(32), nullable=False, server_default='ready'),
        sa.Column('meta_data', JSONB, nullable=False, server_default='{}'),
    )

    # Restore document_id on knowledge_base_chunks
    op.add_column('knowledge_base_chunks', sa.Column('document_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'document_chunks_document_id_fkey', 'knowledge_base_chunks', 'documents',
        ['document_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index('ix_document_chunks_document_id', 'knowledge_base_chunks', ['document_id'])

    # Drop upload_id from knowledge_base_chunks
    op.drop_constraint('fk_kb_chunks_upload_id', 'knowledge_base_chunks', type_='foreignkey')
    op.drop_index('ix_knowledge_base_chunks_upload_id', table_name='knowledge_base_chunks')
    op.drop_column('knowledge_base_chunks', 'upload_id')

    # Rename back
    op.rename_table('knowledge_base_chunks', 'document_chunks')

    # Drop new columns from uploads
    op.drop_column('uploads', 'meta_data')
    op.drop_column('uploads', 'status')
    op.drop_column('uploads', 'file_name')
