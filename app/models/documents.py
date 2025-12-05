"""Document and knowledge base models."""

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector

from .base import BaseModel


class Document(BaseModel):
    """Full-text storage of proposals, resumes, case studies, bios."""

    __tablename__ = "documents"

    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Metadata
    document_type = Column(String(100), nullable=False, index=True)  # proposal, resume, case_study, bio, etc.
    source = Column(String(255))  # file path, URL, etc.
    mime_type = Column(String(100))

    # Relationships
    client_id = Column(String(255), index=True)
    project_id = Column(Integer, index=True)
    resource_id = Column(Integer, index=True)

    # Content metadata
    metadata = Column(JSONB, nullable=False, default=dict)

    # Full-text search vector
    search_vector = Column(TSVECTOR)

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', type='{self.document_type}')>"


class DocumentEmbedding(BaseModel):
    """Vector embeddings for semantic document search."""

    __tablename__ = "document_embeddings"

    document_id = Column(Integer, nullable=False, index=True)
    embedding = Column(Vector(768), nullable=False)  # Dimension for text-embedding-004

    __table_args__ = (
        Index('ix_document_embeddings_vector', embedding, postgresql_using='ivfflat'),
    )

    def __repr__(self) -> str:
        return f"<DocumentEmbedding(document_id={self.document_id})>"


class DocumentChunk(BaseModel):
    """Chunks of documents for better retrieval."""

    __tablename__ = "document_chunks"

    document_id = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)

    # Chunk metadata
    metadata = Column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<DocumentChunk(document_id={self.document_id}, index={self.chunk_index})>"


class DocumentChunkEmbedding(BaseModel):
    """Embeddings for document chunks."""

    __tablename__ = "document_chunk_embeddings"

    chunk_id = Column(Integer, nullable=False, index=True)
    embedding = Column(Vector(768), nullable=False)

    __table_args__ = (
        Index('ix_document_chunk_embeddings_vector', embedding, postgresql_using='ivfflat'),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunkEmbedding(chunk_id={self.chunk_id})>"
