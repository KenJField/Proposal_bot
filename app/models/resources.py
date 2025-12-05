"""Resource and capability models."""

from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from .base import BaseModel


class Resource(BaseModel):
    """Represents people, vendors, tools, and services."""

    __tablename__ = "resources"

    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # person, vendor, tool, service
    email = Column(String(255), index=True)
    phone = Column(String(50))

    # Flexible attributes stored as JSONB
    attributes = Column(JSONB, nullable=False, default=dict)

    # Search and filtering
    search_text = Column(Text, nullable=False, default="")

    # Availability and status
    is_active = Column(JSONB, nullable=False, default=True)
    last_validated = Column(DateTime(timezone=True))

    # Confidence scores for different attributes
    confidence_scores = Column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<Resource(id={self.id}, name='{self.name}', type='{self.type}')>"


class ResourceEmbedding(BaseModel):
    """Vector embeddings for semantic search."""

    __tablename__ = "resource_embeddings"

    resource_id = Column(Integer, nullable=False, index=True)
    embedding = Column(Vector(768), nullable=False)  # Dimension for text-embedding-004

    __table_args__ = (
        Index('ix_resource_embeddings_vector', embedding, postgresql_using='ivfflat'),
    )

    def __repr__(self) -> str:
        return f"<ResourceEmbedding(resource_id={self.resource_id})>"


class Capability(BaseModel):
    """Specific capabilities extracted from resources."""

    __tablename__ = "capabilities"

    resource_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text)

    # Capability metadata
    proficiency_level = Column(String(50))  # expert, advanced, intermediate, basic
    years_experience = Column(Float)
    last_used = Column(DateTime(timezone=True))

    # Validation info
    confidence_score = Column(Float, default=0.0)
    validated_at = Column(DateTime(timezone=True))
    validated_by = Column(String(255))

    def __repr__(self) -> str:
        return f"<Capability(resource_id={self.resource_id}, name='{self.name}', category='{self.category}')>"
