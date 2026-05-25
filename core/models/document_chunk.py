from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from pgvector.sqlalchemy import Vector

from core.models.base import OrgScopedModel


class DocumentChunk(OrgScopedModel):
    """A chunk of text extracted from a Document, with its embedding vector."""

    __tablename__ = "document_chunks"

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)

    document = relationship("Document", back_populates="chunks")
