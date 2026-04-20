import uuid

from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from core.models.base import OrgScopedModel


class Document(OrgScopedModel):
    __tablename__ = 'documents'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    upload_id = Column(BigInteger, ForeignKey('uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    agent_id = Column(BigInteger, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    content_text = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='processing')
    meta_data = Column(JSONB, nullable=True, default=dict)


class DocumentChunk(OrgScopedModel):
    __tablename__ = 'document_chunks'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    document_id = Column(BigInteger, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
