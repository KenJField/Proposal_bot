"""
SQLAlchemy ORM models for the database.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, TIMESTAMP,
    ForeignKey, DECIMAL, ARRAY, JSON, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

from .database import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'admin', 'bd_manager', 'sme'
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rfps_submitted = relationship("RFP", back_populates="submitter", foreign_keys="RFP.submitted_by")
    proposals_reviewed = relationship("Proposal", back_populates="reviewer", foreign_keys="Proposal.reviewed_by")


class RFP(Base):
    """Request for Proposal model."""

    __tablename__ = "rfps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    client_name = Column(String(255))
    client_email = Column(String(255))

    # Raw input
    raw_content = Column(Text)
    file_path = Column(String(500))  # S3 path if uploaded
    file_type = Column(String(50))  # 'pdf', 'docx', 'txt', 'email'

    # Extracted requirements (stored as JSONB)
    extracted_requirements = Column(JSONB)
    extraction_confidence = Column(Float)  # 0-100

    status = Column(String(50), default='received', index=True)
    # 'received', 'extracted', 'proposal_generated', 'archived'

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submitter = relationship("User", back_populates="rfps_submitted", foreign_keys=[submitted_by])
    proposals = relationship("Proposal", back_populates="rfp", cascade="all, delete-orphan")


class Proposal(Base):
    """Proposal model."""

    __tablename__ = "proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfp_id = Column(UUID(as_uuid=True), ForeignKey("rfps.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1)

    # Status tracking
    status = Column(String(50), default='draft', index=True)
    # 'draft', 'in_review', 'approved', 'sent', 'won', 'lost'

    # Generated content (structured as JSONB)
    content = Column(JSONB)

    # Pricing summary
    total_price = Column(DECIMAL(12, 2))
    currency = Column(String(3), default='USD')

    # File outputs
    pdf_path = Column(String(500))  # Generated PDF in S3

    # Review/feedback
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(TIMESTAMP)
    feedback = Column(Text)

    # Outcome tracking
    sent_at = Column(TIMESTAMP)
    outcome = Column(String(50))  # 'won', 'lost', 'no_response'
    outcome_notes = Column(Text)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rfp = relationship("RFP", back_populates="proposals")
    reviewer = relationship("User", back_populates="proposals_reviewed", foreign_keys=[reviewed_by])
    assigned_resources = relationship("ProposalResource", back_populates="proposal", cascade="all, delete-orphan")


class Capability(Base):
    """Capability library for methodologies and services."""

    __tablename__ = "capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Classification
    category = Column(String(100), index=True)  # 'methodology', 'service', 'industry_expertise'
    name = Column(String(255), nullable=False)

    # Description for matching
    description = Column(Text, nullable=False)
    detailed_description = Column(Text)  # For proposal inclusion

    # Vector embedding for semantic search
    embedding = Column(Vector(1536))  # OpenAI embedding dimension

    # Metadata
    typical_duration_weeks = Column(Integer)
    typical_cost_range = Column(JSONB)  # {"min": 10000, "max": 50000, "currency": "USD"}
    complexity_level = Column(String(50))  # 'simple', 'moderate', 'complex'

    # Usage tracking
    times_used = Column(Integer, default=0)
    avg_win_rate = Column(Float)

    tags = Column(ARRAY(String))  # Array of searchable tags

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resource(Base):
    """Resource model for team members and external resources."""

    __tablename__ = "resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    type = Column(String(50), nullable=False, index=True)  # 'internal', 'external', 'vendor'
    name = Column(String(255), nullable=False)
    title = Column(String(255))

    # Skills & expertise
    bio = Column(Text)
    skills = Column(ARRAY(String))  # Array of skill keywords
    expertise_areas = Column(ARRAY(String))  # Industries, methodologies

    # Rates & availability
    hourly_rate = Column(DECIMAL(10, 2))
    currency = Column(String(3), default='USD')
    typical_availability = Column(Float)  # 0-1, percentage of time available

    # Contact
    email = Column(String(255))

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    proposal_assignments = relationship("ProposalResource", back_populates="resource")


class ProposalResource(Base):
    """Junction table for proposal resource assignments."""

    __tablename__ = "proposal_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id"), nullable=False)

    role_in_project = Column(String(255))  # 'Project Lead', 'Senior Researcher', etc.
    hours_allocated = Column(DECIMAL(8, 2))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    proposal = relationship("Proposal", back_populates="assigned_resources")
    resource = relationship("Resource", back_populates="proposal_assignments")


class Asset(Base):
    """Asset library for templates, images, case studies."""

    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    type = Column(String(50), nullable=False, index=True)  # 'template', 'logo', 'case_study', etc.
    name = Column(String(255), nullable=False)
    description = Column(Text)

    file_path = Column(String(500))  # S3 path
    content = Column(Text)  # For text-based assets
    metadata = Column(JSONB)  # Flexible additional data

    tags = Column(ARRAY(String))

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
