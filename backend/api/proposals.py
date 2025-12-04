"""
Proposal API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import logging
from datetime import datetime, timedelta

from models.database import get_db
from models.orm import Proposal, RFP
from models.schemas import (
    ProposalGenerate,
    ProposalResponse,
    ProposalUpdate,
    ProposalListResponse,
    ProposalRegenerateRequest,
    PDFGenerateResponse,
    ProposalContent,
    ExtractedRequirements,
    ProposalStatus,
)
from utils.auth import get_current_user
from utils.file_storage import FileStorage
from services.proposal_service import ProposalService
from services.pdf_service import PDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proposals", tags=["Proposals"])


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_proposal(
    request: ProposalGenerate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate proposal from RFP.

    Args:
        request: Proposal generation request
        db: Database session
        current_user: Authenticated user

    Returns:
        Proposal generation confirmation

    Raises:
        HTTPException: If RFP not found or extraction incomplete
    """
    # Get RFP
    rfp = db.query(RFP).filter(RFP.id == request.rfp_id).first()

    if not rfp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="RFP not found"
        )

    if not rfp.extracted_requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RFP requirements not yet extracted",
        )

    # Check if proposal already exists for this RFP
    existing_proposal = (
        db.query(Proposal).filter(Proposal.rfp_id == request.rfp_id).first()
    )

    if existing_proposal:
        # Return existing proposal
        return {
            "proposal_id": existing_proposal.id,
            "status": existing_proposal.status,
            "message": "Proposal already exists for this RFP",
            "estimated_time_seconds": 0,
        }

    # Create proposal record
    proposal = Proposal(
        rfp_id=request.rfp_id, version=1, status=ProposalStatus.DRAFT, currency="USD"
    )

    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    # Generate proposal content
    try:
        proposal_service = ProposalService()

        # Convert extracted requirements to ExtractedRequirements object
        requirements = ExtractedRequirements(**rfp.extracted_requirements)

        # Generate proposal
        content = await proposal_service.generate_proposal(requirements, db)

        # Update proposal with content
        proposal.content = content.model_dump()
        proposal.total_price = content.pricing.total
        proposal.currency = content.pricing.currency
        proposal.status = ProposalStatus.DRAFT

        # Update RFP status
        rfp.status = "proposal_generated"

        db.commit()
        db.refresh(proposal)

        logger.info(f"Proposal {proposal.id} generated successfully")

        return {
            "proposal_id": proposal.id,
            "status": proposal.status,
            "message": "Proposal generated successfully",
            "estimated_time_seconds": 0,
        }

    except Exception as e:
        logger.error(f"Error generating proposal {proposal.id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating proposal: {str(e)}",
        )


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get proposal details.

    Args:
        proposal_id: Proposal ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Proposal details

    Raises:
        HTTPException: If proposal not found
    """
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found"
        )

    # Convert content dict to ProposalContent if present
    content = None
    if proposal.content:
        content = ProposalContent(**proposal.content)

    return ProposalResponse(
        id=proposal.id,
        rfp_id=proposal.rfp_id,
        version=proposal.version,
        status=proposal.status,
        content=content,
        total_price=float(proposal.total_price) if proposal.total_price else None,
        currency=proposal.currency,
        pdf_path=proposal.pdf_path,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


@router.patch("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: UUID,
    update: ProposalUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update proposal (edit content, change status, add feedback).

    Args:
        proposal_id: Proposal ID
        update: Proposal update data
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated proposal

    Raises:
        HTTPException: If proposal not found
    """
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found"
        )

    # Update content if provided
    if update.content:
        proposal.content = update.content.model_dump()
        proposal.total_price = update.content.pricing.total
        proposal.currency = update.content.pricing.currency

    # Update status if provided
    if update.status:
        proposal.status = update.status

        # Track review
        if update.status == ProposalStatus.IN_REVIEW:
            proposal.reviewed_by = UUID(current_user["sub"])
            proposal.reviewed_at = datetime.utcnow()

        # Track send date
        if update.status == ProposalStatus.SENT:
            proposal.sent_at = datetime.utcnow()

    # Update feedback if provided
    if update.feedback:
        proposal.feedback = update.feedback

    db.commit()
    db.refresh(proposal)

    # Convert content dict to ProposalContent if present
    content = None
    if proposal.content:
        content = ProposalContent(**proposal.content)

    return ProposalResponse(
        id=proposal.id,
        rfp_id=proposal.rfp_id,
        version=proposal.version,
        status=proposal.status,
        content=content,
        total_price=float(proposal.total_price) if proposal.total_price else None,
        currency=proposal.currency,
        pdf_path=proposal.pdf_path,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


@router.post("/{proposal_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_proposal(
    proposal_id: UUID,
    request: ProposalRegenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Regenerate proposal with feedback applied.

    Args:
        proposal_id: Proposal ID
        request: Regeneration request with feedback
        db: Database session
        current_user: Authenticated user

    Returns:
        Regeneration confirmation

    Raises:
        HTTPException: If proposal not found
    """
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found"
        )

    if not proposal.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposal has no content to revise",
        )

    try:
        proposal_service = ProposalService()

        # Get current content
        current_content = ProposalContent(**proposal.content)

        # Revise proposal
        revised_content = await proposal_service.revise_proposal(
            current_content, request.feedback
        )

        # Create new version
        new_version = proposal.version + 1

        new_proposal = Proposal(
            rfp_id=proposal.rfp_id,
            version=new_version,
            status=ProposalStatus.DRAFT,
            content=revised_content.model_dump(),
            total_price=revised_content.pricing.total,
            currency=revised_content.pricing.currency,
        )

        db.add(new_proposal)
        db.commit()
        db.refresh(new_proposal)

        logger.info(f"Proposal {proposal_id} regenerated as version {new_version}")

        return {
            "proposal_id": new_proposal.id,
            "version": new_version,
            "status": new_proposal.status,
            "message": "Proposal regenerated successfully with feedback applied",
        }

    except Exception as e:
        logger.error(f"Error regenerating proposal {proposal_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating proposal: {str(e)}",
        )


@router.post("/{proposal_id}/generate-pdf", response_model=PDFGenerateResponse)
async def generate_pdf(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate PDF version of proposal.

    Args:
        proposal_id: Proposal ID
        db: Database session
        current_user: Authenticated user

    Returns:
        PDF file information

    Raises:
        HTTPException: If proposal not found or has no content
    """
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found"
        )

    if not proposal.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposal has no content to generate PDF",
        )

    try:
        # Get RFP for client info
        rfp = db.query(RFP).filter(RFP.id == proposal.rfp_id).first()

        # Generate PDF
        pdf_service = PDFService()
        content = ProposalContent(**proposal.content)

        local_pdf_path = pdf_service.generate_pdf(
            content,
            client_name=rfp.client_name or "Valued Client",
            project_title=rfp.extracted_requirements.get("project_title", "Research Project")
            if rfp.extracted_requirements
            else "Research Project",
        )

        # Upload to storage
        file_storage = FileStorage()
        storage_path = file_storage.upload_file_from_path(
            local_pdf_path,
            object_name=f"proposal_{proposal_id}_v{proposal.version}.pdf",
            content_type="application/pdf",
            folder="proposals",
        )

        # Update proposal with PDF path
        proposal.pdf_path = storage_path
        db.commit()

        # Generate presigned URL
        download_url = file_storage.generate_presigned_url(
            storage_path, expiration=3600
        )

        return PDFGenerateResponse(
            pdf_path=storage_path,
            download_url=download_url,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

    except Exception as e:
        logger.error(f"Error generating PDF for proposal {proposal_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating PDF: {str(e)}",
        )


@router.get("/list", response_model=ProposalListResponse)
async def list_proposals(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all proposals with optional filtering.

    Args:
        status: Optional status filter
        limit: Results per page
        offset: Pagination offset
        db: Database session
        current_user: Authenticated user

    Returns:
        List of proposals
    """
    query = db.query(Proposal)

    if status:
        query = query.filter(Proposal.status == status)

    total = query.count()

    proposals = query.order_by(Proposal.created_at.desc()).limit(limit).offset(offset).all()

    items = []
    for proposal in proposals:
        content = None
        if proposal.content:
            content = ProposalContent(**proposal.content)

        items.append(
            ProposalResponse(
                id=proposal.id,
                rfp_id=proposal.rfp_id,
                version=proposal.version,
                status=proposal.status,
                content=content,
                total_price=float(proposal.total_price)
                if proposal.total_price
                else None,
                currency=proposal.currency,
                pdf_path=proposal.pdf_path,
                created_at=proposal.created_at,
                updated_at=proposal.updated_at,
            )
        )

    return ProposalListResponse(items=items, total=total, limit=limit, offset=offset)
