"""Knowledge Base implementation with semantic search."""

import json
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.llm import llm_manager, Provider
from ..models import Resource, ResourceEmbedding, Document, DocumentEmbedding


class KnowledgeBase:
    """Knowledge base with semantic search capabilities."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def search_resources(
        self,
        query: str,
        top_k: int = 5,
        capability_filter: Optional[str] = None,
        availability_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for resources using semantic similarity."""
        # Generate embedding for query
        embedding = await self._generate_embedding(query)

        if not embedding:
            return []

        # Build query with filters
        query_builder = select(Resource, ResourceEmbedding).join(ResourceEmbedding)

        # Add capability filter if specified
        if capability_filter:
            # This would require more complex JSON querying
            # For now, we'll filter after retrieval
            pass

        # Add availability filter
        if availability_filter:
            query_builder = query_builder.where(Resource.attributes['availability'].astext == availability_filter)

        # Order by cosine similarity
        query_builder = query_builder.order_by(ResourceEmbedding.embedding.cosine_distance(embedding))

        # Execute query
        result = await self.db.execute(query_builder.limit(top_k * 2))  # Get more for filtering

        candidates = []
        for resource, embedding_record in result:
            # Calculate similarity score (cosine distance to similarity)
            distance = embedding_record.embedding.cosine_distance(embedding)
            similarity_score = 1 - distance  # Convert distance to similarity

            # Apply capability filter if specified
            if capability_filter:
                capabilities = resource.attributes.get('capabilities', [])
                if capability_filter.lower() not in [cap.lower() for cap in capabilities]:
                    continue

            candidates.append({
                "id": resource.id,
                "name": resource.name,
                "type": resource.type,
                "attributes": resource.attributes,
                "similarity_score": float(similarity_score),
                "confidence_score": resource.confidence_scores.get(query, 0.5)
            })

        # Sort by combined score and return top_k
        candidates.sort(key=lambda x: (x["similarity_score"] + x["confidence_score"]) / 2, reverse=True)
        return candidates[:top_k]

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search documents using semantic similarity."""
        # Generate embedding for query
        embedding = await self._generate_embedding(query)

        if not embedding:
            return []

        # Build query
        query_builder = select(Document, DocumentEmbedding).join(DocumentEmbedding)

        if document_type:
            query_builder = query_builder.where(Document.document_type == document_type)

        query_builder = query_builder.order_by(DocumentEmbedding.embedding.cosine_distance(embedding))

        # Execute query
        result = await self.db.execute(query_builder.limit(top_k))

        documents = []
        for document, embedding_record in result:
            distance = embedding_record.embedding.cosine_distance(embedding)
            similarity_score = 1 - distance

            documents.append({
                "id": document.id,
                "title": document.title,
                "content": document.content[:500] + "..." if len(document.content) > 500 else document.content,
                "document_type": document.document_type,
                "metadata": document.doc_metadata,
                "similarity_score": float(similarity_score)
            })

        return documents

    async def update_resource_embedding(self, resource_id: int) -> None:
        """Update or create embedding for a resource."""
        # Get resource
        result = await self.db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        resource = result.scalar_one_or_none()

        if not resource:
            return

        # Create searchable text from resource data
        searchable_text = self._create_searchable_text(resource)

        # Generate embedding
        embedding = await self._generate_embedding(searchable_text)

        if not embedding:
            return

        # Upsert embedding
        await self.db.execute(
            """
            INSERT INTO resource_embeddings (resource_id, embedding)
            VALUES ($1, $2)
            ON CONFLICT (resource_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """,
            resource_id, embedding
        )

        await self.db.commit()

    async def update_document_embedding(self, document_id: int) -> None:
        """Update or create embedding for a document."""
        # Get document
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            return

        # Use document content for embedding
        embedding = await self._generate_embedding(document.content)

        if not embedding:
            return

        # Upsert embedding
        await self.db.execute(
            """
            INSERT INTO document_embeddings (document_id, embedding)
            VALUES ($1, $2)
            ON CONFLICT (document_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """,
            document_id, embedding
        )

        await self.db.commit()

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using Google Gemini."""
        try:
            import google.generativeai as genai
            from ..core.config import settings

            if not settings.google_api_key:
                return None

            genai.configure(api_key=settings.google_api_key)

            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )

            return result['embedding']

        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return None

    def _create_searchable_text(self, resource: Resource) -> str:
        """Create searchable text from resource data."""
        parts = [
            resource.name,
            resource.type,
            resource.email or "",
        ]

        # Add attributes
        if resource.attributes:
            for key, value in resource.attributes.items():
                if isinstance(value, list):
                    parts.extend(value)
                elif isinstance(value, dict):
                    # Flatten nested dicts
                    for k, v in value.items():
                        parts.append(f"{k}: {v}")
                else:
                    parts.append(str(value))

        return " ".join(parts)

    async def get_resource_by_id(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get resource details by ID."""
        result = await self.db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        resource = result.scalar_one_or_none()

        if resource:
            return {
                "id": resource.id,
                "name": resource.name,
                "type": resource.type,
                "attributes": resource.attributes,
                "confidence_scores": resource.confidence_scores,
                "last_validated": resource.last_validated.isoformat() if resource.last_validated else None
            }

        return None

    async def update_resource_confidence(self, resource_id: int, attribute: str, new_score: float) -> None:
        """Update confidence score for a resource attribute."""
        result = await self.db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        resource = result.scalar_one_or_none()

        if resource:
            confidence_scores = resource.confidence_scores.copy()
            confidence_scores[attribute] = new_score
            resource.confidence_scores = confidence_scores
            await self.db.commit()
