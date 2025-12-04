"""
Service for generating and managing proposals.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from .llm_service import LLMService
from .prompts import (
    PROPOSAL_GENERATION_SYSTEM,
    PROPOSAL_REVISION_SYSTEM,
    get_proposal_prompt,
    get_revision_prompt,
)
from models.schemas import ExtractedRequirements, ProposalContent
from models.orm import Capability, Resource

logger = logging.getLogger(__name__)


class ProposalService:
    """Service for generating proposals from RFP requirements."""

    def __init__(self):
        """Initialize the proposal service."""
        self.llm_service = LLMService()

    async def match_capabilities(
        self, requirements: ExtractedRequirements, db: Session, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find relevant capabilities using semantic search.

        Args:
            requirements: Extracted RFP requirements
            db: Database session
            limit: Maximum number of capabilities to return

        Returns:
            List of matched capabilities with similarity scores
        """
        logger.info("Matching capabilities to requirements")

        # Create search query from requirements
        search_text = f"""
        Project: {requirements.project_title or ''}
        Objectives: {', '.join(requirements.objectives)}
        Methodologies: {', '.join(requirements.methodologies_requested)}
        Target: {requirements.target_audience or ''}
        Geography: {', '.join(requirements.geography)}
        """

        # Generate embedding for search query
        query_embedding = await self.llm_service.generate_embedding(search_text)

        # Vector similarity search in database
        # Using pgvector's <=> operator for cosine distance
        query = text("""
            SELECT
                id,
                category,
                name,
                description,
                detailed_description,
                typical_duration_weeks,
                typical_cost_range,
                tags,
                1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM capabilities
            WHERE is_active = true
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        result = db.execute(
            query, {"query_embedding": str(query_embedding), "limit": limit}
        )

        capabilities = []
        for row in result:
            # Filter by similarity threshold
            if row.similarity > 0.6:  # Only include reasonably similar capabilities
                capabilities.append(
                    {
                        "id": str(row.id),
                        "category": row.category,
                        "name": row.name,
                        "description": row.description,
                        "detailed_description": row.detailed_description,
                        "typical_duration_weeks": row.typical_duration_weeks,
                        "typical_cost_range": row.typical_cost_range,
                        "tags": row.tags,
                        "similarity_score": float(row.similarity),
                    }
                )

        logger.info(f"Found {len(capabilities)} matching capabilities")
        return capabilities

    async def get_available_resources(
        self, db: Session, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get available resources for proposal team.

        Args:
            db: Database session
            limit: Maximum number of resources to return

        Returns:
            List of available resources
        """
        logger.info("Fetching available resources")

        resources = (
            db.query(Resource)
            .filter(Resource.is_active == True)
            .order_by(Resource.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": str(r.id),
                "name": r.name,
                "title": r.title,
                "bio": r.bio,
                "skills": r.skills or [],
                "expertise_areas": r.expertise_areas or [],
                "hourly_rate": float(r.hourly_rate) if r.hourly_rate else 0.0,
                "currency": r.currency,
            }
            for r in resources
        ]

    async def generate_proposal(
        self,
        requirements: ExtractedRequirements,
        db: Session,
        firm_info: Optional[Dict[str, Any]] = None,
    ) -> ProposalContent:
        """
        Generate a complete proposal from requirements.

        Args:
            requirements: Extracted RFP requirements
            db: Database session
            firm_info: Optional firm information override

        Returns:
            Generated proposal content
        """
        logger.info("Generating proposal")

        # Match capabilities
        capabilities = await self.match_capabilities(requirements, db)

        if not capabilities:
            logger.warning("No matching capabilities found, using generic approach")
            capabilities = [
                {
                    "name": "Custom Research Solution",
                    "category": "methodology",
                    "description": "Tailored research approach designed specifically for your needs",
                    "detailed_description": "Our team will design a custom research methodology that addresses your specific objectives and requirements.",
                }
            ]

        # Get available resources
        resources = await self.get_available_resources(db)

        if not resources:
            logger.warning("No resources found, using placeholder team")
            resources = [
                {
                    "name": "Senior Research Director",
                    "title": "Project Lead",
                    "bio": "Experienced research professional",
                    "skills": ["research design", "project management"],
                    "expertise_areas": [],
                    "hourly_rate": 200.0,
                    "currency": "USD",
                }
            ]

        # Default firm info
        if firm_info is None:
            firm_info = {
                "name": "Research Solutions Group",
                "tagline": "Insights that drive decisions",
                "differentiators": [
                    "Proven track record in market research",
                    "Experienced team of researchers",
                    "Client-focused approach",
                    "Advanced methodologies",
                ],
            }

        # Generate proposal using LLM
        prompt = get_proposal_prompt(requirements, capabilities, resources, firm_info)

        response = await self.llm_service.generate_completion(
            prompt=prompt,
            system_prompt=PROPOSAL_GENERATION_SYSTEM,
            temperature=0.7,
            max_tokens=4000,
            response_format="json",
        )

        # Parse JSON response
        proposal_data = await self.llm_service.parse_json_response(response)

        # Validate and create ProposalContent object
        proposal = ProposalContent(**proposal_data)

        logger.info("Proposal generation completed successfully")

        return proposal

    async def revise_proposal(
        self, current_proposal: ProposalContent, feedback: str
    ) -> ProposalContent:
        """
        Revise a proposal based on feedback.

        Args:
            current_proposal: Current proposal content
            feedback: Revision feedback

        Returns:
            Revised proposal content
        """
        logger.info("Revising proposal based on feedback")

        # Convert current proposal to dict
        current_dict = current_proposal.model_dump()

        # Generate revision prompt
        prompt = get_revision_prompt(current_dict, feedback)

        response = await self.llm_service.generate_completion(
            prompt=prompt,
            system_prompt=PROPOSAL_REVISION_SYSTEM,
            temperature=0.7,
            max_tokens=4000,
            response_format="json",
        )

        # Parse JSON response
        revised_data = await self.llm_service.parse_json_response(response)

        # Validate and create revised ProposalContent object
        revised_proposal = ProposalContent(**revised_data)

        logger.info("Proposal revision completed successfully")

        return revised_proposal
