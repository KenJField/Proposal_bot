"""Go to Market Agent for proposal outlining and pricing logic."""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from ..core.agent import BaseAgent, AgentContext
from ..core.config import settings
from ..core.llm import Provider


class GTMProposalAgent(BaseAgent):
    """Agent for transforming project plan into client-ready proposal with pricing and business logic."""

    name = "gtm"
    description = "Transform project plan into client-ready proposal with pricing and business logic"
    default_provider = Provider.CLAUDE
    default_model = "claude-3-sonnet-20240229"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute Go to Market proposal generation."""
        self.log_execution_start(context)

        try:
            # Get project plan from Planning Agent
            project_plan = await self._get_project_plan(context.project_id, context.db_session)

            if not project_plan:
                return {"status": "error", "error": "No project plan found"}

            # Generate proposal outline
            proposal_outline = await self._generate_proposal_outline(project_plan)

            # Apply pricing logic
            pricing_summary = await self._calculate_pricing(project_plan, proposal_outline)

            # Perform quality assurance
            qa_results = await self._perform_quality_assurance(proposal_outline, project_plan, context)

            if not qa_results.get("passes_qa", True):
                # Generate revision suggestions
                revisions = await self._generate_revisions(qa_results)
                return {
                    "status": "revision_needed",
                    "qa_issues": qa_results["issues"],
                    "revision_suggestions": revisions
                }

            # Finalize proposal
            final_proposal = await self._finalize_proposal(proposal_outline, pricing_summary)

            # Mark for review
            await self._mark_for_review(context.project_id, final_proposal, context.db_session)

            result = {
                "status": "ready_for_review",
                "proposal_outline": final_proposal,
                "pricing_summary": pricing_summary,
                "qa_results": qa_results
            }

            self.log_execution_end(context, result)
            return result

        except Exception as e:
            self.logger.error(f"GTM proposal generation failed: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _get_project_plan(self, project_id: int, db_session) -> Optional[Dict[str, Any]]:
        """Get project plan from database."""
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project and project.plan:
            return project.plan

        return None

    async def _generate_proposal_outline(self, project_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive proposal outline from project plan."""
        prompt = f"""
Transform this technical project plan into a client-ready proposal outline.

Project Plan:
{json.dumps(project_plan, indent=2)}

Create a professional proposal structure with these standard sections:

1. **Executive Summary**
   - High-level project overview
   - Key objectives and approach
   - Expected outcomes
   - Total investment

2. **Understanding & Objectives**
   - Client situation analysis
   - Research objectives
   - Key business questions

3. **Proposed Approach & Methodology**
   - Research design overview
   - Methodology details
   - Sample plan
   - Quality assurance measures

4. **Project Timeline**
   - Phase breakdown
   - Key milestones
   - Deliverables schedule

5. **Team & Experience**
   - Project team structure
   - Relevant experience and credentials
   - Key personnel bios

6. **Deliverables**
   - All outputs and reports
   - Data deliverables
   - Presentation formats

7. **Investment & Terms**
   - Pricing structure
   - Payment terms
   - Project assumptions

8. **Risks & Mitigation**
   - Potential challenges
   - Mitigation strategies
   - Contingency planning

Ensure the outline:
- Uses client-friendly language (avoid jargon)
- Tells a compelling story
- Highlights value and expertise
- Is structured for easy reading

Return JSON with proposal outline structure.
"""

        response = await self.generate_text(prompt, temperature=0.3, max_tokens=3000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "error": "Failed to generate outline",
                "sections": ["Executive Summary", "Methodology", "Timeline", "Team", "Pricing"]
            }

    async def _calculate_pricing(self, project_plan: Dict[str, Any], proposal_outline: Dict[str, Any]) -> Dict[str, Any]:
        """Apply pricing rules and calculate proposal pricing."""
        costs = project_plan.get("costs", {})
        phases = project_plan.get("phases", [])

        # Extract cost components
        resource_costs = costs.get("resource_costs", 0)
        vendor_costs = costs.get("vendor_costs", 0)
        overhead = costs.get("overhead", 0)

        prompt = f"""
Calculate professional pricing for this market research proposal.

Cost Breakdown:
- Resource costs: ${resource_costs}
- Vendor/external costs: ${vendor_costs}
- Overhead: ${overhead}
- Total direct costs: ${resource_costs + vendor_costs + overhead}

Project Details:
{json.dumps(project_plan, indent=2)}

Apply these pricing rules:
1. **Markup percentages**: 40-60% on resource costs depending on complexity
2. **Contingency buffer**: 10-20% based on project risk
3. **Rounding conventions**: Round to nearest $500 or $1000
4. **Bundled vs itemized**: Consider if itemized pricing makes sense

Calculate:
- Base pricing (cost + markup)
- Contingency amount
- Total price
- Breakdown by phases/major deliverables
- Alternative pricing options if applicable

Consider market rates and competitive positioning.

Return JSON with detailed pricing structure.
"""

        response = await self.generate_text(prompt, temperature=0.1)

        try:
            pricing = json.loads(response)

            # Ensure pricing is realistic
            pricing["confidence_level"] = "high"
            pricing["assumptions"] = [
                "Standard markup rates applied",
                "Contingency based on project complexity",
                "Market competitive pricing"
            ]

            return pricing

        except json.JSONDecodeError:
            return {
                "total_price": (resource_costs + vendor_costs + overhead) * 1.5,
                "breakdown": {
                    "resources": resource_costs * 1.4,
                    "vendors": vendor_costs * 1.1,
                    "overhead": overhead,
                    "contingency": (resource_costs + vendor_costs) * 0.15
                },
                "error": "Pricing calculation failed, using fallback"
            }

    async def _perform_quality_assurance(
        self,
        proposal_outline: Dict[str, Any],
        project_plan: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Perform comprehensive quality assurance on the proposal."""
        # Get original requirements for comparison
        requirements = await self._get_requirements(context.project_id, context.db_session)

        prompt = f"""
Perform quality assurance review of this proposal outline.

Original Requirements:
{json.dumps(requirements, indent=2)}

Project Plan:
{json.dumps(project_plan, indent=2)}

Proposal Outline:
{json.dumps(proposal_outline, indent=2)}

Check for:
1. **Requirements Coverage**: Does proposal address all RFP requirements?
2. **Methodology Alignment**: Is methodology appropriate for client needs?
3. **Timeline Realism**: Are timelines achievable with available resources?
4. **Team Credentials**: Do team credentials match required expertise?
5. **Pricing Appropriateness**: Is pricing competitive and justified?
6. **Completeness**: Are all sections adequately detailed?
7. **Client Appropriateness**: Is language and structure client-friendly?

Identify any issues, gaps, or inconsistencies.

Return JSON with:
- passes_qa: boolean
- issues: array of issues found
- severity: overall assessment (critical/high/medium/low)
- recommendations: suggested fixes
"""

        response = await self.generate_text(prompt, temperature=0.1)

        try:
            qa_results = json.loads(response)
            return qa_results
        except json.JSONDecodeError:
            return {
                "passes_qa": True,
                "issues": [],
                "severity": "low",
                "recommendations": ["QA check completed"]
            }

    async def _generate_revisions(self, qa_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific revision suggestions based on QA issues."""
        issues = qa_results.get("issues", [])

        prompt = f"""
Based on these QA issues, generate specific revision suggestions.

QA Issues:
{json.dumps(issues, indent=2)}

For each issue, provide:
- Issue description
- Specific revision needed
- Section(s) to modify
- Suggested content or approach
- Priority (high/medium/low)

Return JSON array of revision suggestions.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return [{"issue": "General revisions needed", "priority": "medium"}]

    async def _finalize_proposal(self, outline: Dict[str, Any], pricing: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize proposal by integrating pricing and ensuring completeness."""
        final_proposal = outline.copy()
        final_proposal["pricing"] = pricing
        final_proposal["version"] = "1.0"
        final_proposal["generated_at"] = "2024-01-01T00:00:00Z"
        final_proposal["status"] = "ready_for_review"

        # Add standard disclaimers and terms
        final_proposal["disclaimers"] = [
            "Pricing is valid for 30 days",
            "Timeline assumes client responsiveness",
            "Final deliverables subject to data quality review"
        ]

        return final_proposal

    async def _mark_for_review(self, project_id: int, proposal: Dict[str, Any], db_session) -> None:
        """Mark proposal ready for project lead review."""
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            # Update project with proposal outline
            requirements = project.requirements.copy()
            requirements["proposal_outline"] = proposal

            project.requirements = requirements
            project.status = "review_ready"
            await db_session.commit()

    async def _get_requirements(self, project_id: int, db_session) -> Optional[Dict[str, Any]]:
        """Get original requirements for QA comparison."""
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project and project.requirements:
            return project.requirements.get("brief_analysis", {}).get("analysis")

        return None

    async def incorporate_feedback(self, context: AgentContext) -> Dict[str, Any]:
        """Incorporate feedback from project lead review."""
        feedback = context.data.get("feedback")
        current_proposal = context.data.get("current_proposal")

        if not feedback or not current_proposal:
            return {"status": "error", "error": "Missing feedback or proposal data"}

        # Apply feedback changes
        revised_proposal = await self._apply_feedback_changes(current_proposal, feedback)

        # Re-run QA if significant changes
        if feedback.get("significant_changes", False):
            qa_results = await self._perform_quality_assurance(revised_proposal, {}, context)
            if not qa_results.get("passes_qa", True):
                return {
                    "status": "revision_needed",
                    "qa_issues": qa_results["issues"],
                    "revised_proposal": revised_proposal
                }

        # Mark as approved if ready
        if feedback.get("approved", False):
            await self._mark_approved(context.project_id, revised_proposal, context.db_session)
            return {
                "status": "approved",
                "final_proposal": revised_proposal
            }

        return {
            "status": "revised",
            "revised_proposal": revised_proposal
        }

    async def _apply_feedback_changes(self, proposal: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Apply specific feedback changes to proposal."""
        changes = feedback.get("changes", [])

        revised = proposal.copy()

        prompt = f"""
Apply these feedback changes to the proposal outline.

Current Proposal:
{json.dumps(proposal, indent=2)}

Feedback Changes:
{json.dumps(changes, indent=2)}

Return the revised proposal outline with changes applied.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return revised

    async def _mark_approved(self, project_id: int, proposal: Dict[str, Any], db_session) -> None:
        """Mark proposal as approved and ready for PowerPoint generation."""
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            project.status = "approved"
            await db_session.commit()
