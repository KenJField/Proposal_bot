"""Validation workflow models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from .base import BaseModel


class Validation(BaseModel):
    """Tracks validation workflow state."""

    __tablename__ = "validations"

    # What is being validated
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False, index=True)
    attribute_path = Column(String(500), nullable=False)  # JSON path like "capabilities.advanced_analytics"
    validation_type = Column(String(100), nullable=False, index=True)  # availability, capability, pricing, etc.

    # Validation state
    status = Column(String(50), nullable=False, default="pending", index=True)
    # Statuses: pending, sent, responded, timeout, cancelled

    # Priority and scheduling
    priority = Column(String(20), default="medium", index=True)  # high, medium, low
    scheduled_at = Column(DateTime(timezone=True))

    # Email tracking
    email_thread_id = Column(String(500), index=True)
    sent_at = Column(DateTime(timezone=True))
    response_received_at = Column(DateTime(timezone=True))

    # Validation details
    question = Column(Text, nullable=False)
    expected_response_type = Column(String(100))  # yes_no, scale, text, etc.

    # Results
    response = Column(JSONB, nullable=False, default=dict)
    confidence_score = Column(Float)
    validated_by = Column(String(255))  # email address or name

    # Timeout management
    timeout_at = Column(DateTime(timezone=True))
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Alternative methods tried
    alternative_methods = Column(JSONB, nullable=False, default=list)  # web_research, etc.

    def __repr__(self) -> str:
        return f"<Validation(id={self.id}, resource_id={self.resource_id}, attribute='{self.attribute_path}', status='{self.status}')>"


class ValidationTemplate(BaseModel):
    """Templates for common validation questions."""

    __tablename__ = "validation_templates"

    name = Column(String(255), nullable=False, unique=True)
    validation_type = Column(String(100), nullable=False, index=True)
    template_text = Column(Text, nullable=False)

    # Template metadata
    context_required = Column(JSONB, nullable=False, default=list)  # required context variables
    expected_response_format = Column(String(100))

    # Usage tracking
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    def __repr__(self) -> str:
        return f"<ValidationTemplate(name='{self.name}', type='{self.validation_type}')>"


class ValidationResult(BaseModel):
    """Parsed and structured validation results."""

    __tablename__ = "validation_results"

    validation_id = Column(Integer, ForeignKey('validations.id'), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False, index=True)

    # Result data
    attribute_path = Column(String(500), nullable=False)
    old_value = Column(JSONB)
    new_value = Column(JSONB, nullable=False)

    # Quality metrics
    confidence_score = Column(Float, nullable=False)
    validation_method = Column(String(100), nullable=False)  # email, web_research, manual

    # Metadata
    validated_at = Column(DateTime(timezone=True), nullable=False)
    validated_by = Column(String(255))

    def __repr__(self) -> str:
        return f"<ValidationResult(validation_id={self.validation_id}, attribute='{self.attribute_path}')>"
