"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


# Enums
class RFPStatus(str, Enum):
    RECEIVED = "received"
    EXTRACTED = "extracted"
    PROPOSAL_GENERATED = "proposal_generated"
    ARCHIVED = "archived"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SENT = "sent"
    WON = "won"
    LOST = "lost"


class ResourceType(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    VENDOR = "vendor"


class UserRole(str, Enum):
    ADMIN = "admin"
    BD_MANAGER = "bd_manager"
    SME = "sme"


# Auth Schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# RFP Schemas
class ExtractedRequirements(BaseModel):
    project_title: Optional[str] = None
    objectives: List[str] = Field(default_factory=list)
    methodologies_requested: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    sample_size: Optional[str] = None
    geography: List[str] = Field(default_factory=list)
    timeline: Optional[Dict[str, Any]] = None
    budget: Optional[Dict[str, Any]] = None
    deliverables: List[str] = Field(default_factory=list)
    evaluation_criteria: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)


class RFPSubmit(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    raw_content: Optional[str] = None  # If pasted text


class RFPResponse(BaseModel):
    id: UUID
    client_name: Optional[str]
    client_email: Optional[str]
    raw_content: Optional[str]
    file_path: Optional[str]
    file_type: Optional[str]
    extracted_requirements: Optional[ExtractedRequirements]
    extraction_confidence: Optional[float]
    status: RFPStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RFPListResponse(BaseModel):
    items: List[RFPResponse]
    total: int
    limit: int
    offset: int


# Proposal Schemas
class ProposalPhase(BaseModel):
    name: str
    description: str
    duration_weeks: int
    deliverables: List[str]


class ProposalMethodology(BaseModel):
    overview: str
    approach: str
    phases: List[ProposalPhase]


class TeamMember(BaseModel):
    name: str
    role: str
    bio: str
    hours_allocated: float


class PricingLineItem(BaseModel):
    description: str
    quantity: float
    unit_cost: float
    total: float


class ProposalPricing(BaseModel):
    line_items: List[PricingLineItem]
    subtotal: float
    tax: float
    total: float
    currency: str = "USD"


class ProposalTimeline(BaseModel):
    total_duration_weeks: int
    milestones: List[Dict[str, str]] = Field(default_factory=list)


class ProposalContent(BaseModel):
    executive_summary: str
    understanding_of_needs: str
    proposed_methodology: ProposalMethodology
    timeline: ProposalTimeline
    team: List[TeamMember]
    pricing: ProposalPricing
    why_us: str
    case_studies: List[Dict[str, Any]] = Field(default_factory=list)


class ProposalGenerate(BaseModel):
    rfp_id: UUID


class ProposalUpdate(BaseModel):
    content: Optional[ProposalContent] = None
    status: Optional[ProposalStatus] = None
    feedback: Optional[str] = None


class ProposalResponse(BaseModel):
    id: UUID
    rfp_id: UUID
    version: int
    status: ProposalStatus
    content: Optional[ProposalContent]
    total_price: Optional[float]
    currency: str
    pdf_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProposalListResponse(BaseModel):
    items: List[ProposalResponse]
    total: int
    limit: int
    offset: int


class ProposalRegenerateRequest(BaseModel):
    feedback: str


class PDFGenerateResponse(BaseModel):
    pdf_path: str
    download_url: str
    expires_at: datetime


# Capability Schemas
class CapabilityCreate(BaseModel):
    category: str
    name: str
    description: str
    detailed_description: Optional[str] = None
    typical_duration_weeks: Optional[int] = None
    typical_cost_range: Optional[Dict[str, Any]] = None
    complexity_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CapabilityResponse(BaseModel):
    id: UUID
    category: str
    name: str
    description: str
    detailed_description: Optional[str]
    typical_duration_weeks: Optional[int]
    typical_cost_range: Optional[Dict[str, Any]]
    tags: List[str]
    times_used: int
    avg_win_rate: Optional[float]

    class Config:
        from_attributes = True


class CapabilitySearchResult(BaseModel):
    id: UUID
    category: str
    name: str
    description: str
    similarity_score: float


class CapabilitySearchResponse(BaseModel):
    items: List[CapabilitySearchResult]
    total: int


# Resource Schemas
class ResourceCreate(BaseModel):
    type: ResourceType
    name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    expertise_areas: List[str] = Field(default_factory=list)
    hourly_rate: Optional[float] = None
    currency: str = "USD"
    email: Optional[EmailStr] = None


class ResourceResponse(BaseModel):
    id: UUID
    type: ResourceType
    name: str
    title: Optional[str]
    bio: Optional[str]
    skills: List[str]
    expertise_areas: List[str]
    hourly_rate: Optional[float]
    currency: str

    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    items: List[ResourceResponse]
    total: int
    limit: int
    offset: int


# Error Response
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
