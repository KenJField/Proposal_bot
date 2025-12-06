"""Project-related schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project status in the workflow."""

    PLANNING = "planning"
    RESOURCING = "resourcing"
    VALIDATING = "validating"
    AWAITING_VALIDATION = "awaiting_validation"
    AWAITING_LEAD_APPROVAL = "awaiting_lead_approval"
    FINALIZING = "finalizing"
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"


class ResourceAssignment(BaseModel):
    """Assignment of a resource to a project."""

    resource_id: str = Field(..., description="Resource identifier")
    resource_name: str = Field(..., description="Resource name")
    resource_type: str = Field(..., description="Type of resource")
    role: str = Field(..., description="Role in the project")
    allocation: float = Field(
        ..., ge=0.0, le=1.0, description="Allocation (0-1, where 1 = full-time)"
    )
    hours_estimated: Optional[float] = Field(
        default=None, description="Estimated hours for this resource"
    )
    rate: float = Field(..., description="Billing rate for this resource")
    cost: float = Field(..., description="Total cost for this resource assignment")

    # Validation status
    validated: bool = Field(default=False, description="Whether resource has been validated")
    validation_response: Optional[str] = Field(
        default=None, description="Validation response from resource manager"
    )
    validated_rate: Optional[float] = Field(
        default=None, description="Rate confirmed during validation"
    )
    validated_availability: Optional[bool] = Field(
        default=None, description="Availability confirmed during validation"
    )


class ProjectPlan(BaseModel):
    """Detailed project plan."""

    # Overview
    title: str = Field(..., description="Project title")
    summary: str = Field(..., description="Executive summary")
    objectives: list[str] = Field(..., description="Project objectives")

    # Methodology
    approach: str = Field(..., description="Overall research approach")
    methodology: str = Field(..., description="Detailed methodology")
    phases: list[dict[str, Any]] = Field(
        default_factory=list, description="Project phases with timelines"
    )

    # Resources
    resource_assignments: list[ResourceAssignment] = Field(
        default_factory=list, description="Assigned resources"
    )
    project_lead_id: Optional[str] = Field(default=None, description="Assigned project lead")
    project_lead_name: Optional[str] = Field(default=None, description="Project lead name")

    # Timeline
    duration_weeks: int = Field(..., description="Project duration in weeks")
    start_date: Optional[str] = Field(default=None, description="Planned start date")
    end_date: Optional[str] = Field(default=None, description="Planned end date")
    milestones: list[dict[str, Any]] = Field(
        default_factory=list, description="Key project milestones"
    )

    # Deliverables
    deliverables: list[dict[str, Any]] = Field(
        default_factory=list, description="Project deliverables"
    )

    # Budget
    estimated_cost: float = Field(..., description="Total estimated cost")
    cost_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Cost breakdown by category"
    )

    # Risks and assumptions
    risks: list[str] = Field(default_factory=list, description="Identified risks")
    assumptions: list[str] = Field(default_factory=list, description="Project assumptions")
    mitigation_strategies: list[str] = Field(
        default_factory=list, description="Risk mitigation strategies"
    )


class Project(BaseModel):
    """Project instance for a proposal."""

    id: str = Field(..., description="Unique project identifier")
    brief_id: str = Field(..., description="Associated brief ID")

    # Status
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING, description="Current status")

    # Project plan
    plan: Optional[ProjectPlan] = Field(default=None, description="Detailed project plan")

    # Validation tracking
    validations_sent: int = Field(default=0, description="Number of validation emails sent")
    validations_received: int = Field(default=0, description="Number of validation responses received")
    validation_complete: bool = Field(default=False, description="Whether validation is complete")

    # Lead approval tracking
    lead_approval_requested: bool = Field(
        default=False, description="Whether lead approval has been requested"
    )
    lead_approval_received: bool = Field(
        default=False, description="Whether lead approval has been received"
    )
    lead_feedback: Optional[str] = Field(default=None, description="Feedback from project lead")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
