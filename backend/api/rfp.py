"""
RFP API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import tempfile
import os
import logging

from models.database import get_db
from models.orm import RFP, User
from models.schemas import (
    RFPResponse,
    RFPListResponse,
    ExtractedRequirements,
    RFPStatus,
)
from utils.auth import get_current_user
from utils.file_storage import FileStorage
from services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rfp", tags=["RFP"])


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_rfp(
    client_name: Optional[str] = Form(None),
    client_email: Optional[str] = Form(None),
    raw_content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Submit a new RFP for processing.

    Args:
        client_name: Optional client name
        client_email: Optional client email
        raw_content: Optional pasted text content
        file: Optional uploaded file (PDF/DOCX)
        db: Database session
        current_user: Authenticated user

    Returns:
        RFP submission confirmation

    Raises:
        HTTPException: If neither content nor file is provided
    """
    if not raw_content and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either raw_content or file must be provided",
        )

    # Create RFP record
    rfp = RFP(
        submitted_by=UUID(current_user["sub"]),
        client_name=client_name,
        client_email=client_email,
        status=RFPStatus.RECEIVED,
    )

    # Handle file upload
    if file:
        file_storage = FileStorage()
        file_type = file.filename.split(".")[-1].lower()

        # Upload file to storage
        file_path = file_storage.upload_file(
            file.file, file.filename, file.content_type, folder="rfps"
        )

        rfp.file_path = file_path
        rfp.file_type = file_type

        # Save temp file for extraction
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{file_type}"
        ) as temp_file:
            file.file.seek(0)
            temp_file.write(file.file.read())
            temp_path = temp_file.name

    elif raw_content:
        rfp.raw_content = raw_content
        rfp.file_type = "text"

    # Save RFP to database
    db.add(rfp)
    db.commit()
    db.refresh(rfp)

    # Start extraction process (async in production)
    try:
        extraction_service = ExtractionService()

        if file:
            # Extract from file
            requirements = await extraction_service.extract_from_file(
                temp_path, file_type
            )
            # Clean up temp file
            os.unlink(temp_path)
        else:
            # Extract from text
            requirements = await extraction_service.extract_from_text(raw_content)

        # Update RFP with extracted requirements
        rfp.extracted_requirements = requirements.model_dump()
        rfp.extraction_confidence = requirements.extraction_confidence
        rfp.status = RFPStatus.EXTRACTED

        db.commit()
        db.refresh(rfp)

        logger.info(f"RFP {rfp.id} extracted successfully")

    except Exception as e:
        logger.error(f"Error extracting RFP {rfp.id}: {e}")
        # RFP is saved but extraction failed
        rfp.status = RFPStatus.RECEIVED
        db.commit()

    return {
        "id": rfp.id,
        "status": rfp.status,
        "message": "RFP received and processing started",
    }


@router.get("/{rfp_id}", response_model=RFPResponse)
async def get_rfp(
    rfp_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get RFP details including extracted requirements.

    Args:
        rfp_id: RFP ID
        db: Database session
        current_user: Authenticated user

    Returns:
        RFP details

    Raises:
        HTTPException: If RFP not found
    """
    rfp = db.query(RFP).filter(RFP.id == rfp_id).first()

    if not rfp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="RFP not found"
        )

    # Convert extracted_requirements dict to ExtractedRequirements if present
    extracted = None
    if rfp.extracted_requirements:
        extracted = ExtractedRequirements(**rfp.extracted_requirements)

    return RFPResponse(
        id=rfp.id,
        client_name=rfp.client_name,
        client_email=rfp.client_email,
        raw_content=rfp.raw_content,
        file_path=rfp.file_path,
        file_type=rfp.file_type,
        extracted_requirements=extracted,
        extraction_confidence=rfp.extraction_confidence,
        status=rfp.status,
        created_at=rfp.created_at,
        updated_at=rfp.updated_at,
    )


@router.get("/list", response_model=RFPListResponse)
async def list_rfps(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all RFPs with optional filtering.

    Args:
        status: Optional status filter
        limit: Results per page
        offset: Pagination offset
        db: Database session
        current_user: Authenticated user

    Returns:
        List of RFPs
    """
    query = db.query(RFP)

    if status:
        query = query.filter(RFP.status == status)

    total = query.count()

    rfps = query.order_by(RFP.created_at.desc()).limit(limit).offset(offset).all()

    items = []
    for rfp in rfps:
        extracted = None
        if rfp.extracted_requirements:
            extracted = ExtractedRequirements(**rfp.extracted_requirements)

        items.append(
            RFPResponse(
                id=rfp.id,
                client_name=rfp.client_name,
                client_email=rfp.client_email,
                raw_content=rfp.raw_content,
                file_path=rfp.file_path,
                file_type=rfp.file_type,
                extracted_requirements=extracted,
                extraction_confidence=rfp.extraction_confidence,
                status=rfp.status,
                created_at=rfp.created_at,
                updated_at=rfp.updated_at,
            )
        )

    return RFPListResponse(items=items, total=total, limit=limit, offset=offset)
