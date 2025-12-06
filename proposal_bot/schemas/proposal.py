"""Proposal-related schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProposalSection(BaseModel):
    """A section of the proposal document."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content (markdown format)")
    order: int = Field(..., description="Display order")
    subsections: list["ProposalSection"] = Field(
        default_factory=list, description="Nested subsections"
    )


class Proposal(BaseModel):
    """Final proposal document."""

    id: str = Field(..., description="Unique proposal identifier")
    project_id: str = Field(..., description="Associated project ID")
    brief_id: str = Field(..., description="Associated brief ID")

    # Client information
    client_name: str = Field(..., description="Client organization name")
    client_contact: str = Field(..., description="Primary contact name")
    client_email: str = Field(..., description="Contact email")

    # Proposal metadata
    title: str = Field(..., description="Proposal title")
    version: int = Field(default=1, description="Proposal version number")
    status: str = Field(default="draft", description="Proposal status (draft/final/sent/approved)")

    # Document structure
    sections: list[ProposalSection] = Field(
        default_factory=list, description="Proposal sections"
    )

    # Pricing
    pricing_summary: dict[str, Any] = Field(
        default_factory=dict, description="Pricing summary"
    )
    total_price: float = Field(..., description="Total proposal price")
    payment_terms: str = Field(
        default="Net 30", description="Payment terms"
    )

    # Team
    project_team: list[dict[str, Any]] = Field(
        default_factory=list, description="Project team members"
    )
    project_lead: str = Field(..., description="Project lead name")

    # Timeline
    timeline_summary: str = Field(..., description="Timeline summary")
    key_milestones: list[dict[str, str]] = Field(
        default_factory=list, description="Key milestones"
    )

    # Compliance and terms
    terms_and_conditions: str = Field(
        default="Standard T&C apply", description="Terms and conditions"
    )
    validity_period_days: int = Field(
        default=30, description="Proposal validity in days"
    )

    # Attachments
    attachments: list[str] = Field(
        default_factory=list, description="Attachment file paths"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = Field(default=None, description="When proposal was sent")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def increment_version(self) -> None:
        """Increment the version number."""
        self.version += 1
        self.updated_at = datetime.utcnow()

    def mark_as_sent(self) -> None:
        """Mark proposal as sent."""
        self.status = "sent"
        self.sent_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


# Allow forward references for recursive models
ProposalSection.model_rebuild()
