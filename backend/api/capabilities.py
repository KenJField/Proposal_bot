"""
Capabilities API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
import logging

from models.database import get_db
from models.orm import Capability
from models.schemas import (
    CapabilityCreate,
    CapabilityResponse,
    CapabilitySearchResponse,
    CapabilitySearchResult,
)
from utils.auth import get_current_user, require_role
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


@router.get("/search", response_model=CapabilitySearchResponse)
async def search_capabilities(
    q: str,
    category: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Search capabilities by query (semantic + keyword).

    Args:
        q: Search query
        category: Optional category filter
        limit: Results limit
        db: Database session
        current_user: Authenticated user

    Returns:
        Search results with similarity scores
    """
    logger.info(f"Searching capabilities for: {q}")

    try:
        # Generate embedding for search query
        llm_service = LLMService()
        query_embedding = await llm_service.generate_embedding(q)

        # Build query
        sql = """
            SELECT
                id,
                category,
                name,
                description,
                1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM capabilities
            WHERE is_active = true
        """

        params = {"query_embedding": str(query_embedding), "limit": limit}

        if category:
            sql += " AND category = :category"
            params["category"] = category

        sql += """
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """

        result = db.execute(text(sql), params)

        items = []
        for row in result:
            if row.similarity > 0.5:  # Similarity threshold
                items.append(
                    CapabilitySearchResult(
                        id=row.id,
                        category=row.category,
                        name=row.name,
                        description=row.description,
                        similarity_score=float(row.similarity),
                    )
                )

        return CapabilitySearchResponse(items=items, total=len(items))

    except Exception as e:
        logger.error(f"Error searching capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching capabilities: {str(e)}",
        )


@router.post("", response_model=CapabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_capability(
    capability: CapabilityCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin"])),
):
    """
    Add new capability to knowledge base.

    Args:
        capability: Capability data
        db: Database session
        current_user: Authenticated admin user

    Returns:
        Created capability

    Raises:
        HTTPException: If error generating embedding
    """
    logger.info(f"Creating capability: {capability.name}")

    try:
        # Generate embedding
        llm_service = LLMService()
        embedding_text = f"{capability.name} {capability.description}"
        embedding = await llm_service.generate_embedding(embedding_text)

        # Create capability
        new_capability = Capability(
            category=capability.category,
            name=capability.name,
            description=capability.description,
            detailed_description=capability.detailed_description,
            typical_duration_weeks=capability.typical_duration_weeks,
            typical_cost_range=capability.typical_cost_range,
            complexity_level=capability.complexity_level,
            tags=capability.tags,
            embedding=embedding,
        )

        db.add(new_capability)
        db.commit()
        db.refresh(new_capability)

        logger.info(f"Capability created: {new_capability.id}")

        return CapabilityResponse(
            id=new_capability.id,
            category=new_capability.category,
            name=new_capability.name,
            description=new_capability.description,
            detailed_description=new_capability.detailed_description,
            typical_duration_weeks=new_capability.typical_duration_weeks,
            typical_cost_range=new_capability.typical_cost_range,
            tags=new_capability.tags or [],
            times_used=new_capability.times_used or 0,
            avg_win_rate=new_capability.avg_win_rate,
        )

    except Exception as e:
        logger.error(f"Error creating capability: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating capability: {str(e)}",
        )


@router.get("/{capability_id}", response_model=CapabilityResponse)
async def get_capability(
    capability_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get capability by ID.

    Args:
        capability_id: Capability ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Capability details

    Raises:
        HTTPException: If capability not found
    """
    capability = db.query(Capability).filter(Capability.id == capability_id).first()

    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found"
        )

    return CapabilityResponse(
        id=capability.id,
        category=capability.category,
        name=capability.name,
        description=capability.description,
        detailed_description=capability.detailed_description,
        typical_duration_weeks=capability.typical_duration_weeks,
        typical_cost_range=capability.typical_cost_range,
        tags=capability.tags or [],
        times_used=capability.times_used or 0,
        avg_win_rate=capability.avg_win_rate,
    )
