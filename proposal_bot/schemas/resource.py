"""Resource-related schemas."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Type of resource."""

    STAFF = "staff"
    VENDOR = "vendor"
    TOOL = "tool"
    FACILITY = "facility"


class Resource(BaseModel):
    """Base resource model."""

    id: str = Field(..., description="Unique resource identifier")
    name: str = Field(..., description="Resource name")
    type: ResourceType = Field(..., description="Type of resource")
    capabilities: list[str] = Field(default_factory=list, description="Resource capabilities")
    availability: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Availability (0-1, where 1 = fully available)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class StaffMember(Resource):
    """Staff member resource."""

    type: Literal[ResourceType.STAFF] = ResourceType.STAFF

    # Professional details
    title: str = Field(..., description="Job title")
    department: str = Field(..., description="Department")
    seniority_level: str = Field(
        ..., description="Seniority level (junior/mid/senior/principal/director)"
    )

    # Skills and expertise
    skills: list[str] = Field(default_factory=list, description="Technical and soft skills")
    methodologies: list[str] = Field(
        default_factory=list, description="Research methodologies expertise"
    )
    industries: list[str] = Field(
        default_factory=list, description="Industry experience"
    )
    languages: list[str] = Field(default_factory=list, description="Languages spoken")

    # Rates and availability
    hourly_rate: float = Field(..., description="Hourly billing rate")
    internal_cost: float = Field(..., description="Internal hourly cost")
    current_utilization: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Current utilization rate"
    )

    # Project preferences
    can_lead_projects: bool = Field(default=False, description="Qualified to lead projects")
    preferred_project_types: list[str] = Field(
        default_factory=list, description="Preferred project types"
    )

    # Performance metrics
    successful_projects: int = Field(default=0, description="Number of successful projects")
    client_satisfaction_score: Optional[float] = Field(
        default=None, ge=1.0, le=5.0, description="Average client satisfaction (1-5)"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "staff_001",
                "name": "Dr. Sarah Johnson",
                "title": "Senior Research Director",
                "department": "Quantitative Research",
                "seniority_level": "senior",
                "skills": [
                    "survey design",
                    "statistical analysis",
                    "SPSS",
                    "Python",
                    "data visualization",
                ],
                "methodologies": ["online surveys", "CATI", "mixed methods"],
                "industries": ["technology", "healthcare", "finance"],
                "languages": ["English", "Spanish"],
                "hourly_rate": 225.0,
                "internal_cost": 125.0,
                "current_utilization": 0.65,
                "can_lead_projects": True,
                "successful_projects": 47,
                "client_satisfaction_score": 4.7,
            }
        }


class Vendor(Resource):
    """External vendor/supplier resource."""

    type: Literal[ResourceType.VENDOR] = ResourceType.VENDOR

    # Vendor details
    company_name: str = Field(..., description="Vendor company name")
    contact_person: str = Field(..., description="Primary contact person")
    contact_email: str = Field(..., description="Contact email")
    phone: Optional[str] = Field(default=None, description="Contact phone number")

    # Service details
    services: list[str] = Field(default_factory=list, description="Services provided")
    specializations: list[str] = Field(
        default_factory=list, description="Areas of specialization"
    )
    geographic_coverage: list[str] = Field(
        default_factory=list, description="Geographic regions covered"
    )

    # Pricing
    pricing_model: str = Field(
        default="per_complete", description="Pricing model (per_complete/hourly/fixed)"
    )
    base_rate: float = Field(..., description="Base rate (varies by pricing model)")
    volume_discounts: dict[str, float] = Field(
        default_factory=dict, description="Volume-based discount structure"
    )

    # Relationship
    relationship_status: str = Field(
        default="approved", description="Relationship status (approved/preferred/trial)"
    )
    last_project_date: Optional[str] = Field(default=None, description="Last project completion date")
    quality_rating: Optional[float] = Field(
        default=None, ge=1.0, le=5.0, description="Quality rating (1-5)"
    )
    on_time_delivery_rate: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="On-time delivery rate (0-1)"
    )

    # Capacity
    max_concurrent_projects: int = Field(default=5, description="Maximum concurrent projects")
    typical_turnaround_days: int = Field(default=14, description="Typical turnaround time in days")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "vendor_003",
                "name": "Global Panel Solutions",
                "company_name": "Global Panel Solutions LLC",
                "contact_person": "Michael Chen",
                "contact_email": "m.chen@globalpanel.com",
                "services": ["panel recruitment", "CATI", "data collection"],
                "specializations": ["B2B panels", "healthcare professionals"],
                "geographic_coverage": ["North America", "Europe", "APAC"],
                "pricing_model": "per_complete",
                "base_rate": 45.0,
                "relationship_status": "preferred",
                "quality_rating": 4.5,
                "on_time_delivery_rate": 0.92,
            }
        }
