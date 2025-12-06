"""Validation-related schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Status of a validation request."""

    PENDING = "pending"
    SENT = "sent"
    RECEIVED = "received"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ValidationRequest(BaseModel):
    """Request for resource validation."""

    id: str = Field(..., description="Unique validation request identifier")
    project_id: str = Field(..., description="Associated project ID")
    resource_id: str = Field(..., description="Resource being validated")
    resource_type: str = Field(..., description="Type of resource")

    # Validation details
    questions: list[str] = Field(..., description="Validation questions")
    context: dict[str, Any] = Field(default_factory=dict, description="Context for validation")

    # Communication
    recipient_email: str = Field(..., description="Email address for validation request")
    recipient_name: str = Field(..., description="Recipient name")
    email_thread_id: Optional[str] = Field(default=None, description="Email thread ID")
    email_message_id: Optional[str] = Field(default=None, description="Email message ID")

    # Status
    status: ValidationStatus = Field(default=ValidationStatus.PENDING, description="Current status")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = Field(default=None, description="When request was sent")
    expires_at: Optional[datetime] = Field(default=None, description="When request expires")
    responded_at: Optional[datetime] = Field(default=None, description="When response was received")

    # Response tracking
    response_received: bool = Field(default=False, description="Whether response was received")
    reminder_count: int = Field(default=0, description="Number of reminder emails sent")
    last_reminder_at: Optional[datetime] = Field(
        default=None, description="When last reminder was sent"
    )


class ValidationResponse(BaseModel):
    """Response to a validation request."""

    validation_id: str = Field(..., description="Associated validation request ID")
    project_id: str = Field(..., description="Associated project ID")
    resource_id: str = Field(..., description="Resource being validated")

    # Response content
    confirmed: bool = Field(..., description="Whether resource is confirmed available")
    availability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Resource availability (0-1)"
    )
    confirmed_rate: Optional[float] = Field(
        default=None, description="Confirmed pricing/rate"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Any constraints or conditions"
    )
    notes: Optional[str] = Field(default=None, description="Additional notes from validator")

    # Alternative suggestions
    alternative_resources: list[str] = Field(
        default_factory=list, description="Alternative resource suggestions"
    )
    alternative_approaches: list[str] = Field(
        default_factory=list, description="Alternative approach suggestions"
    )

    # Email metadata
    email_message_id: Optional[str] = Field(default=None, description="Response email message ID")
    respondent_email: str = Field(..., description="Email address of respondent")

    # Timestamp
    received_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
