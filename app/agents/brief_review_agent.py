"""Brief Review Agent for RFP analysis and requirements extraction."""

import json
import logging
from typing import Any, Dict, List, Optional

from ..core.agent import BaseAgent, AgentContext
from ..core.config import settings
from ..core.llm import Provider


class BriefReviewAgent(BaseAgent):
    """Agent for analyzing incoming research briefs and extracting structured requirements."""

    name = "brief_review"
    description = "Analyze incoming research briefs and decompose into structured project requirements"
    default_provider = Provider.CLAUDE
    default_model = "claude-3-sonnet-20240229"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute brief review analysis."""
        self.log_execution_start(context)

        try:
            # Get RFP content from project
            rfp_content = await self._get_rfp_content(context.project_id, context.db_session)

            if not rfp_content:
                return {"status": "error", "error": "No RFP content found"}

            # Analyze the brief
            analysis = await self._analyze_brief(rfp_content)

            # Enrich with context
            enriched_analysis = await self._enrich_with_context(analysis, context)

            # Calculate go/no-go decision
            go_no_go = await self._calculate_go_no_go_score(enriched_analysis)

            # Generate clarification questions
            clarification_questions = await self._generate_clarification_questions(analysis)

            # Recommend project lead
            project_lead = await self._recommend_project_lead(enriched_analysis)

            # Save analysis results
            await self._save_analysis_results(context.project_id, {
                "analysis": enriched_analysis,
                "go_no_go": go_no_go,
                "clarification_questions": clarification_questions,
                "recommended_lead": project_lead
            }, context.db_session)

            # Create Notion page
            await self._create_notion_page(context.project_id, enriched_analysis)

            result = {
                "status": "completed",
                "analysis": enriched_analysis,
                "go_no_go_score": go_no_go["score"],
                "go_no_go_recommendation": go_no_go["recommendation"],
                "clarification_questions": clarification_questions,
                "recommended_lead": project_lead,
                "needs_clarification": len(clarification_questions) > 0
            }

            self.log_execution_end(context, result)
            return result

        except Exception as e:
            self.logger.error(f"Brief review failed: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _get_rfp_content(self, project_id: int, db_session) -> Optional[str]:
        """Get RFP content from project."""
        from sqlalchemy import select
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project and project.requirements:
            return project.requirements.get("rfp_content")

        return None

    async def _analyze_brief(self, rfp_content: str) -> Dict[str, Any]:
        """Analyze the RFP content and extract structured information."""
        prompt = f"""
Analyze this market research RFP and extract structured information.

RFP Content:
{rfp_content}

Extract and structure the following information:

1. **Project Overview**:
   - Title/summary
   - Client name and industry
   - Research objectives
   - Key business questions

2. **Methodology Requirements**:
   - Primary research methods needed
   - Sample size requirements
   - Geographic scope
   - Target audience details

3. **Timeline & Deliverables**:
   - Project start/end dates
   - Key milestones
   - Deliverable types (reports, presentations, datasets)
   - Delivery format preferences

4. **Budget & Pricing**:
   - Budget range or expectations
   - Pricing structure preferences
   - Payment terms

5. **Quality & Compliance**:
   - Required certifications or standards
   - Data privacy requirements
   - Quality assurance needs

6. **Success Criteria**:
   - Key performance indicators
   - Acceptance criteria
   - Decision-making process

Identify any:
- Critical ambiguities
- Missing information
- Unclear requirements
- Potential risks or challenges

Return a comprehensive JSON structure with all extracted information.
"""

        response = await self.generate_text(prompt, temperature=0.1, max_tokens=4000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse analysis response: {response}")
            return {"error": "Failed to parse analysis", "raw_response": response}

    async def _enrich_with_context(self, analysis: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Enrich analysis with contextual information."""
        enriched = analysis.copy()

        # Query knowledge base for past projects
        client_history = await self._query_client_history(analysis.get("client_name"), context.db_session)

        # Perform web research on client
        client_research = await self._perform_client_research(analysis.get("client_name"))

        # Identify past similar projects
        similar_projects = await self._find_similar_projects(analysis, context.db_session)

        enriched.update({
            "client_history": client_history,
            "client_research": client_research,
            "similar_projects": similar_projects,
            "enrichment_timestamp": "2024-01-01T00:00:00Z"  # Current timestamp
        })

        return enriched

    async def _calculate_go_no_go_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate go/no-go decision based on firm capabilities and strategic fit."""
        prompt = f"""
Evaluate this market research project for go/no-go decision.

Analysis Summary:
{json.dumps(analysis, indent=2)}

Evaluate based on:
1. **Technical Feasibility**: Do we have the required methodologies and capabilities?
2. **Resource Availability**: Can we staff this project adequately?
3. **Strategic Fit**: Does this align with our strengths and target markets?
4. **Profitability**: Is the budget sufficient for the scope and risk?
5. **Risk Level**: What are the key risks and can we mitigate them?
6. **Competition**: How competitive is this bid?

Provide:
- Overall score (0-100)
- Recommendation (GO/NO-GO/CONDITIONAL)
- Key factors influencing the decision
- Required conditions (if conditional)
- Risk mitigation strategies

Return JSON with score, recommendation, factors, conditions, and risks.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                "score": 50,
                "recommendation": "CONDITIONAL",
                "factors": ["Analysis failed"],
                "conditions": ["Manual review required"],
                "risks": ["Unknown"]
            }

    async def _generate_clarification_questions(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific clarification questions for missing information."""
        ambiguities = analysis.get("ambiguities", [])
        missing_info = analysis.get("missing_information", [])

        if not ambiguities and not missing_info:
            return []

        prompt = f"""
Based on this RFP analysis, generate specific clarification questions for the client.

Analysis:
{json.dumps(analysis, indent=2)}

Generate questions that are:
- Specific and actionable
- Prioritized by criticality (blocking vs. nice-to-have)
- Client-appropriate language
- Focused on information needed to provide accurate proposal

For each question include:
- Question text
- Category (methodology, timeline, budget, scope, etc.)
- Priority (high/medium/low)
- Why it's needed

Return JSON array of question objects.
"""

        response = await self.generate_text(prompt, temperature=0.3)

        try:
            questions = json.loads(response)
            return questions if isinstance(questions, list) else []
        except json.JSONDecodeError:
            return []

    async def _recommend_project_lead(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend project lead based on methodology expertise and availability."""
        methodologies = analysis.get("methodology_requirements", [])
        timeline = analysis.get("timeline", {})

        prompt = f"""
Recommend a project lead for this market research project.

Required Methodologies:
{json.dumps(methodologies, indent=2)}

Timeline:
{json.dumps(timeline, indent=2)}

Consider:
- Methodology expertise match
- Current availability
- Past project success with similar work
- Team leadership experience
- Client relationship skills

Return JSON with recommended person details, reasoning, and confidence score.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "name": "TBD",
                "reasoning": "Analysis failed - manual assignment needed",
                "confidence_score": 0.0
            }

    async def _query_client_history(self, client_name: str, db_session) -> Dict[str, Any]:
        """Query knowledge base for past projects with this client."""
        if not client_name:
            return {"past_projects": [], "notes": "No client name provided"}

        # In a real implementation, this would search the document database
        # For now, return mock data
        return {
            "past_projects": [],
            "relationship_level": "new",
            "notes": f"First project with {client_name}"
        }

    async def _perform_client_research(self, client_name: str) -> Dict[str, Any]:
        """Perform web research on client."""
        if not client_name:
            return {"research": "No client name provided"}

        # In a real implementation, this would use Google Search API
        # For now, return mock data
        return {
            "industry": "Unknown",
            "recent_news": [],
            "competitors": [],
            "research_notes": f"Web research needed for {client_name}"
        }

    async def _find_similar_projects(self, analysis: Dict[str, Any], db_session) -> List[Dict[str, Any]]:
        """Find past projects with similar requirements."""
        # In a real implementation, this would use vector search
        # For now, return mock data
        return []

    async def _save_analysis_results(self, project_id: int, results: Dict[str, Any], db_session) -> None:
        """Save analysis results to project."""
        from sqlalchemy import select
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            requirements = project.requirements.copy()
            requirements.update({
                "brief_analysis": results,
                "analysis_completed_at": "2024-01-01T00:00:00Z"
            })
            project.requirements = requirements
            await db_session.commit()

    async def _create_notion_page(self, project_id: int, analysis: Dict[str, Any]) -> None:
        """Create Notion page with analysis summary."""
        # TODO: Implement Notion integration
        # For now, just log
        self.logger.info(f"Would create Notion page for project {project_id} with analysis summary")
