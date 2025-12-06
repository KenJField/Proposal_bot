"""Planning Agent for resource discovery and validation orchestration."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from ..core.agent import BaseAgent, AgentContext
from ..core.config import settings
from ..core.llm import Provider


class PlanningAgent(BaseAgent):
    """Agent for creating detailed project plans by matching requirements to available resources."""

    name = "planning"
    description = "Create detailed project plans by matching requirements to available resources"
    default_provider = Provider.CLAUDE
    default_model = "claude-3-sonnet-20240229"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute planning workflow."""
        self.log_execution_start(context)

        try:
            # Get requirements from brief analysis
            requirements = await self._get_requirements(context.project_id, context.db_session)

            if not requirements:
                return {"status": "error", "error": "No requirements found"}

            # Discover and match resources
            resource_matches = await self._discover_resources(requirements)

            # Identify validation needs
            validation_plan = await self._identify_validation_needs(resource_matches, requirements)

            # Create initial project plan
            project_plan = await self._create_project_plan(requirements, resource_matches)

            # Trigger validations
            validation_results = await self._orchestrate_validations(validation_plan, context)

            # Refine plan based on validation results
            refined_plan = await self._refine_plan_with_validations(project_plan, validation_results)

            # Handle design questions if needed
            if refined_plan.get("needs_design_decisions"):
                design_questions = await self._generate_design_questions(refined_plan)
                await self._send_design_questions(design_questions, context)
                return {"status": "design_questions_sent", "questions": design_questions}

            # Save final plan
            await self._save_project_plan(context.project_id, refined_plan, context.db_session)

            result = {
                "status": "completed",
                "plan": refined_plan,
                "resource_matches": resource_matches,
                "validations_completed": len(validation_results.get("completed", [])),
                "validations_pending": len(validation_results.get("pending", []))
            }

            self.log_execution_end(context, result)
            return result

        except Exception as e:
            self.logger.error(f"Planning failed: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _get_requirements(self, project_id: int, db_session) -> Optional[Dict[str, Any]]:
        """Get requirements from project brief analysis."""
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project and project.requirements:
            return project.requirements.get("brief_analysis", {}).get("analysis")

        return None

    async def _discover_resources(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Discover and match resources to requirements."""
        methodologies = requirements.get("methodology_requirements", [])
        sample_size = requirements.get("sample_requirements", {})
        timeline = requirements.get("timeline", {})

        # Query knowledge base for matching resources
        resource_candidates = await self._query_resource_candidates(methodologies)

        # Calculate match scores
        scored_matches = await self._calculate_match_scores(
            resource_candidates, methodologies, sample_size, timeline
        )

        # Identify gaps
        gaps = await self._identify_resource_gaps(scored_matches, requirements)

        return {
            "matched_resources": scored_matches,
            "resource_gaps": gaps,
            "total_candidates": len(resource_candidates)
        }

    async def _query_resource_candidates(self, methodologies: List[str]) -> List[Dict[str, Any]]:
        """Query knowledge base for resources with required capabilities."""
        try:
            # Import here to avoid circular imports
            from ..knowledge.kb import KnowledgeBase
            from ..database.connection import async_session_factory

            async with async_session_factory() as db_session:
                kb = KnowledgeBase(db_session)

                # Search for each methodology and aggregate results
                all_candidates = {}
                for methodology in methodologies:
                    try:
                        candidates = await kb.search_resources(
                            query=f"experienced in {methodology}",
                            top_k=3
                        )

                        # Aggregate by resource ID to avoid duplicates
                        for candidate in candidates:
                            resource_id = candidate["id"]
                            if resource_id not in all_candidates:
                                all_candidates[resource_id] = candidate
                            else:
                                # Merge capabilities and update scores
                                existing = all_candidates[resource_id]
                                existing["capabilities"].extend(candidate.get("capabilities", []))
                                existing["capabilities"] = list(set(existing["capabilities"]))  # Remove duplicates
                                existing["similarity_score"] = max(
                                    existing.get("similarity_score", 0),
                                    candidate.get("similarity_score", 0)
                                )

                    except Exception as e:
                        self.logger.warning(f"KB search failed for {methodology}: {e}")
                        continue

                # Convert back to list and add fallback if no results
                candidates_list = list(all_candidates.values())
                if not candidates_list:
                    # Fallback to basic search
                    candidates_list = await self._fallback_resource_search(methodologies)

                return candidates_list

        except Exception as e:
            self.logger.error(f"KB query failed, using fallback: {e}")
            return await self._fallback_resource_search(methodologies)

    async def _fallback_resource_search(self, methodologies: List[str]) -> List[Dict[str, Any]]:
        """Fallback resource search when KB is unavailable."""
        # This would be removed once KB is fully populated
        # For now, return mock data representing the search results
        return [
            {
                "id": 1,
                "name": "Sarah Johnson",
                "type": "person",
                "capabilities": ["qualitative_research", "focus_groups", "interviews"],
                "availability": "available",
                "confidence_score": 0.9,
                "similarity_score": 0.8
            },
            {
                "id": 2,
                "name": "Mike Chen",
                "type": "person",
                "capabilities": ["quantitative_research", "survey_design", "conjoint_analysis"],
                "availability": "limited",
                "confidence_score": 0.8,
                "similarity_score": 0.7
            },
            {
                "id": 3,
                "name": "Research Panel Co",
                "type": "vendor",
                "capabilities": ["survey_hosting", "sample_recruitment"],
                "availability": "available",
                "confidence_score": 0.7,
                "similarity_score": 0.6
            }
        ]

    async def _calculate_match_scores(
        self,
        candidates: List[Dict[str, Any]],
        methodologies: List[str],
        sample_size: Dict[str, Any],
        timeline: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate how well each resource matches requirements."""
        prompt = f"""
Evaluate how well each resource candidate matches these project requirements.

Requirements:
- Methodologies: {json.dumps(methodologies, indent=2)}
- Sample Size: {json.dumps(sample_size, indent=2)}
- Timeline: {json.dumps(timeline, indent=2)}

Candidates:
{json.dumps(candidates, indent=2)}

For each candidate, calculate:
- Capability match score (0-100)
- Availability score (0-100)
- Overall suitability score (0-100)
- Key strengths for this project
- Potential concerns or limitations

Return JSON array with enhanced candidate objects including scores and analysis.
"""

        response = await self.generate_text(prompt, temperature=0.1)

        try:
            scored_candidates = json.loads(response)
            return scored_candidates
        except json.JSONDecodeError:
            # Return candidates with default scores
            for candidate in candidates:
                candidate.update({
                    "capability_match": 50,
                    "availability_score": 50,
                    "overall_score": 50,
                    "strengths": ["Unknown"],
                    "concerns": ["Needs validation"]
                })
            return candidates

    async def _identify_resource_gaps(
        self,
        resource_matches: List[Dict[str, Any]],
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify gaps where no suitable internal resource exists."""
        prompt = f"""
Analyze resource matches and identify gaps that may require external consultants or additional resources.

Resource Matches:
{json.dumps(resource_matches, indent=2)}

Requirements:
{json.dumps(requirements, indent=2)}

Identify:
- Critical capabilities not covered by matched resources
- Overloaded resources that may need backup
- Specialty skills that require external expertise
- Timeline conflicts or availability issues

For each gap, suggest:
- Gap description
- Severity (critical/high/medium/low)
- Recommended solutions (external hire, training, etc.)
- Estimated cost/time impact

Return JSON array of resource gaps.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return []

    async def _identify_validation_needs(
        self,
        resource_matches: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify which resource attributes need validation."""
        matched_resources = resource_matches.get("matched_resources", [])

        validation_candidates = []

        for resource in matched_resources:
            # Check for low confidence scores
            if resource.get("confidence_score", 1.0) < 0.8:
                validation_candidates.append({
                    "resource_id": resource["id"],
                    "attribute": "capability_confidence",
                    "reason": f"Low confidence score: {resource.get('confidence_score', 0)}",
                    "priority": "high"
                })

            # Check for stale data (mock - in real system would check timestamps)
            if resource.get("last_validated_days", 90) > 60:
                validation_candidates.append({
                    "resource_id": resource["id"],
                    "attribute": "availability",
                    "reason": "Data may be stale",
                    "priority": "medium"
                })

            # Check critical path resources
            if resource.get("overall_score", 0) > 80:
                validation_candidates.append({
                    "resource_id": resource["id"],
                    "attribute": "current_availability",
                    "reason": "Critical path resource",
                    "priority": "high"
                })

        # Prioritize validations
        prioritized = sorted(validation_candidates,
                           key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]],
                           reverse=True)

        return {
            "validations_needed": prioritized[:5],  # Limit to top 5
            "total_candidates": len(validation_candidates)
        }

    async def _orchestrate_validations(
        self,
        validation_plan: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Trigger concurrent validation emails."""
        validations_needed = validation_plan.get("validations_needed", [])

        # Create validation tasks in database
        validation_tasks = []
        for validation in validations_needed:
            task = await self._create_validation_task(validation, context)
            validation_tasks.append(task)

        # Trigger emails via Celery tasks for proper async execution
        for task in validation_tasks:
            from ..core.tasks import send_validation_email
            send_validation_email.apply_async(
                args=[{
                    "validation_id": task["id"],
                    "recipient_email": task.get("recipient_email"),
                    "recipient_name": task.get("recipient_name"),
                    "question": task.get("question"),
                    "attribute_path": task.get("attribute_path"),
                    "project_title": task.get("project_title", "Market Research Project"),
                    "priority": task.get("priority", "medium")
                }],
                countdown=5,  # Start in 5 seconds to avoid immediate load
                expires=settings.validation_timeout
            )

        return {
            "pending": validation_tasks,
            "completed": [],
            "status": "validations_triggered",
            "celery_tasks_queued": len(validation_tasks)
        }

    async def _create_validation_task(self, validation: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Create validation task in database."""
        from ..models import Validation

        # Generate contextual question
        question = await self._generate_validation_question(validation)

        validation_record = Validation(
            resource_id=validation["resource_id"],
            attribute_path=validation["attribute"],
            validation_type="capability",
            question=question,
            priority=validation["priority"],
            status="pending"
        )

        context.db_session.add(validation_record)
        await context.db_session.commit()
        await context.db_session.refresh(validation_record)

        return {
            "id": validation_record.id,
            "resource_id": validation["resource_id"],
            "question": question,
            "priority": validation["priority"]
        }

    async def _generate_validation_question(self, validation: Dict[str, Any]) -> str:
        """Generate contextual validation question."""
        prompt = f"""
Generate a specific validation question for this resource attribute.

Validation Details:
{json.dumps(validation, indent=2)}

Create a clear, actionable question that:
- Is specific to the attribute being validated
- Can be answered yes/no or with specific details
- Includes context about why validation is needed
- Is appropriate for email communication

Return just the question text.
"""

        response = await self.generate_text(prompt, temperature=0.3)
        return response.strip()

    async def _create_project_plan(
        self,
        requirements: Dict[str, Any],
        resource_matches: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create detailed project plan with phases, resources, costs, timeline."""
        matched_resources = resource_matches.get("matched_resources", [])

        prompt = f"""
Create a detailed project plan based on these requirements and available resources.

Requirements:
{json.dumps(requirements, indent=2)}

Available Resources:
{json.dumps(matched_resources, indent=2)}

Create a project plan with:

1. **Project Phases**:
   - Phase name and description
   - Key deliverables
   - Duration estimates
   - Dependencies

2. **Resource Allocation**:
   - Which resources assigned to which phases
   - Time allocation per resource
   - Roles and responsibilities

3. **Timeline**:
   - Overall project duration
   - Key milestones and deadlines
   - Critical path identification

4. **Cost Estimates**:
   - Resource costs by phase
   - External vendor costs
   - Total project cost
   - Cost breakdown and assumptions

5. **Risks and Dependencies**:
   - Key project risks
   - Dependency assumptions
   - Mitigation strategies

Return comprehensive JSON project plan.
"""

        response = await self.generate_text(prompt, temperature=0.2, max_tokens=3000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "error": "Failed to generate plan",
                "phases": [],
                "timeline": {},
                "costs": {"total": 0},
                "resources": matched_resources
            }

    async def _refine_plan_with_validations(
        self,
        initial_plan: Dict[str, Any],
        validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refine project plan based on validation results."""
        # For now, assume validations are pending and plan needs refinement
        # In real implementation, would check actual validation results

        refined_plan = initial_plan.copy()
        refined_plan["validation_status"] = validation_results.get("status", "pending")

        # Check if plan needs design decisions
        if validation_results.get("status") == "pending":
            refined_plan["needs_design_decisions"] = True
            refined_plan["design_decision_reason"] = "Awaiting validation results to confirm resource availability"

        return refined_plan

    async def _generate_design_questions(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate design questions for project lead."""
        prompt = f"""
Based on this project plan, identify areas that need design decisions from the project lead.

Project Plan:
{json.dumps(plan, indent=2)}

Generate specific questions about:
- Methodological choices or trade-offs
- Resource allocation decisions
- Timeline adjustments
- Scope clarifications
- Risk mitigation approaches

For each question:
- Question text
- Context/background
- Options or considerations
- Impact on project (high/medium/low)

Return JSON array of design questions.
"""

        response = await self.generate_text(prompt, temperature=0.3)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return []

    async def _send_design_questions(self, questions: List[Dict[str, Any]], context: AgentContext) -> None:
        """Send design questions to project lead via Email Agent."""
        from ..core.agent import agent_registry
        email_agent = agent_registry.get_agent("email")

        await email_agent.execute(AgentContext(
            await email_agent.execute(AgentContext(
                project_id=context.project_id,
                db_session=context.db_session,
                data={
                    "action": "send_design_questions",
                    "questions": questions,
                    "recipient": "project_lead@example.com"  # Would be determined from requirements
                }
            ))

    async def _save_project_plan(self, project_id: int, plan: Dict[str, Any], db_session) -> None:
        """Save project plan to database."""
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            project.plan = plan
            project.status = "planning"
            await db_session.commit()
