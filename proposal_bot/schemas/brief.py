"""Brief-related schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class BriefStatus(str, Enum):
    """Status of a research brief."""

    RECEIVED = "received"
    ANALYZING = "analyzing"
    NEEDS_CLARIFICATION = "needs_clarification"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    COMPLETE = "complete"
    APPROVED = "approved"
    REJECTED = "rejected"


class Brief(BaseModel):
    """Research brief from a client."""

    id: str = Field(..., description="Unique identifier for the brief")
    client_name: str = Field(..., description="Name of the client organization")
    client_contact: str = Field(..., description="Primary contact person")
    client_email: str = Field(..., description="Contact email address")

    # Brief content
    title: str = Field(..., description="Brief title or project name")
    description: str = Field(..., description="Detailed brief description")
    objectives: list[str] = Field(default_factory=list, description="Research objectives")
    requirements: dict[str, Any] = Field(default_factory=dict, description="Specific requirements")

    # Metadata
    status: BriefStatus = Field(default=BriefStatus.RECEIVED, description="Current brief status")
    sales_rep: Optional[str] = Field(default=None, description="Assigned sales representative")

    # Extracted information
    budget_range: Optional[tuple[float, float]] = Field(
        default=None, description="Budget range (min, max)"
    )
    timeline: Optional[str] = Field(default=None, description="Project timeline")
    target_audience: Optional[str] = Field(default=None, description="Target research audience")
    methodology_preferences: list[str] = Field(
        default_factory=list, description="Preferred research methodologies"
    )
    deliverables: list[str] = Field(default_factory=list, description="Expected deliverables")

    # Additional context
    past_projects: list[str] = Field(
        default_factory=list, description="Related past project IDs"
    )
    crm_data: dict[str, Any] = Field(
        default_factory=dict, description="CRM-sourced client data"
    )
    web_research: dict[str, Any] = Field(
        default_factory=dict, description="Web research about client"
    )

    # Timestamps
    received_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "brief_2024_001",
                "client_name": "TechCorp Inc",
                "client_contact": "Jane Smith",
                "client_email": "jane.smith@techcorp.com",
                "title": "Customer Satisfaction Study",
                "description": "We need to understand customer satisfaction with our new product line",
                "objectives": [
                    "Measure overall satisfaction",
                    "Identify pain points",
                    "Gather feature requests",
                ],
                "budget_range": (50000, 75000),
                "timeline": "8 weeks",
                "target_audience": "B2B software users",
                "methodology_preferences": ["online surveys", "interviews"],
                "deliverables": ["executive summary", "detailed report", "presentation"],
            }
        }
