"""
Resources API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
import logging

from models.database import get_db
from models.orm import Resource
from models.schemas import (
    ResourceCreate,
    ResourceResponse,
    ResourceListResponse,
    ResourceType,
)
from utils.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    type: Optional[ResourceType] = None,
    skills: Optional[str] = None,  # Comma-separated skills
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List available resources.

    Args:
        type: Optional resource type filter
        skills: Optional skills filter (comma-separated)
        limit: Results per page
        offset: Pagination offset
        db: Database session
        current_user: Authenticated user

    Returns:
        List of resources
    """
    query = db.query(Resource).filter(Resource.is_active == True)

    if type:
        query = query.filter(Resource.type == type)

    if skills:
        # Filter by skills (array contains any of the specified skills)
        skill_list = [s.strip() for s in skills.split(",")]
        for skill in skill_list:
            query = query.filter(Resource.skills.contains([skill]))

    total = query.count()

    resources = query.order_by(Resource.created_at.desc()).limit(limit).offset(offset).all()

    items = [
        ResourceResponse(
            id=r.id,
            type=r.type,
            name=r.name,
            title=r.title,
            bio=r.bio,
            skills=r.skills or [],
            expertise_areas=r.expertise_areas or [],
            hourly_rate=float(r.hourly_rate) if r.hourly_rate else None,
            currency=r.currency,
        )
        for r in resources
    ]

    return ResourceListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin"])),
):
    """
    Add new resource.

    Args:
        resource: Resource data
        db: Database session
        current_user: Authenticated admin user

    Returns:
        Created resource
    """
    logger.info(f"Creating resource: {resource.name}")

    try:
        new_resource = Resource(
            type=resource.type,
            name=resource.name,
            title=resource.title,
            bio=resource.bio,
            skills=resource.skills,
            expertise_areas=resource.expertise_areas,
            hourly_rate=resource.hourly_rate,
            currency=resource.currency,
            email=resource.email,
        )

        db.add(new_resource)
        db.commit()
        db.refresh(new_resource)

        logger.info(f"Resource created: {new_resource.id}")

        return ResourceResponse(
            id=new_resource.id,
            type=new_resource.type,
            name=new_resource.name,
            title=new_resource.title,
            bio=new_resource.bio,
            skills=new_resource.skills or [],
            expertise_areas=new_resource.expertise_areas or [],
            hourly_rate=float(new_resource.hourly_rate) if new_resource.hourly_rate else None,
            currency=new_resource.currency,
        )

    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating resource: {str(e)}",
        )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get resource by ID.

    Args:
        resource_id: Resource ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Resource details

    Raises:
        HTTPException: If resource not found
    """
    resource = db.query(Resource).filter(Resource.id == resource_id).first()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )

    return ResourceResponse(
        id=resource.id,
        type=resource.type,
        name=resource.name,
        title=resource.title,
        bio=resource.bio,
        skills=resource.skills or [],
        expertise_areas=resource.expertise_areas or [],
        hourly_rate=float(resource.hourly_rate) if resource.hourly_rate else None,
        currency=resource.currency,
    )
