"""Proposal document formatter."""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from proposal_bot.schemas.brief import Brief
from proposal_bot.schemas.project import ProjectPlan
from proposal_bot.schemas.proposal import Proposal, ProposalSection


class ProposalFormatter:
    """
    Format proposals into professional documents.

    This service:
    - Creates standardized proposal structure
    - Formats sections with consistent styling
    - Generates executive summaries
    - Creates pricing tables
    - Formats team bios
    - Ensures brand compliance
    """

    def __init__(self, company_name: str = "Research Excellence Partners"):
        """
        Initialize proposal formatter.

        Args:
            company_name: Company name for branding
        """
        self.company_name = company_name

    def create_proposal_document(
        self,
        brief: Brief,
        project_plan: ProjectPlan,
        pricing_breakdown: Dict[str, Any],
        proposal_id: str,
    ) -> Proposal:
        """
        Create a complete proposal document.

        Args:
            brief: Research brief
            project_plan: Project plan
            pricing_breakdown: Pricing breakdown from PricingCalculator
            proposal_id: Unique proposal identifier

        Returns:
            Complete Proposal object
        """
        # Create proposal sections
        sections = [
            self._create_cover_section(brief),
            self._create_executive_summary(brief, project_plan),
            self._create_understanding_section(brief),
            self._create_objectives_section(brief),
            self._create_methodology_section(project_plan),
            self._create_approach_section(project_plan),
            self._create_timeline_section(project_plan),
            self._create_team_section(project_plan),
            self._create_deliverables_section(project_plan),
            self._create_pricing_section(pricing_breakdown),
            self._create_why_us_section(),
            self._create_terms_section(),
        ]

        # Create team summary
        project_team = self._format_team_members(project_plan.resource_assignments)

        # Calculate validity date
        validity_date = datetime.utcnow() + timedelta(days=30)

        proposal = Proposal(
            id=proposal_id,
            project_id=f"proj_{brief.id}",
            brief_id=brief.id,
            client_name=brief.client_name,
            client_contact=brief.client_contact,
            client_email=brief.client_email,
            title=f"Proposal: {brief.title}",
            version=1,
            status="draft",
            sections=sections,
            pricing_summary=pricing_breakdown,
            total_price=pricing_breakdown["total_price"],
            payment_terms="50% upon contract signing, 50% upon completion of fieldwork",
            project_team=project_team,
            project_lead=project_plan.project_lead_name or "To be assigned",
            timeline_summary=f"{project_plan.duration_weeks} weeks from project kickoff",
            key_milestones=[
                {"milestone": phase["name"], "timing": f"Week {i+1}"}
                for i, phase in enumerate(project_plan.phases)
            ] if project_plan.phases else [],
            terms_and_conditions="Standard terms and conditions apply. Full T&C available upon request.",
            validity_period_days=30,
        )

        return proposal

    def _create_cover_section(self, brief: Brief) -> ProposalSection:
        """Create proposal cover page section."""
        content = f"""
# {brief.title}

**Prepared for:**
{brief.client_name}
{brief.client_contact}

**Prepared by:**
{self.company_name}
Date: {datetime.utcnow().strftime('%B %d, %Y')}

**Project ID:** {brief.id}

---

*Confidential - For {brief.client_name} Use Only*
        """.strip()

        return ProposalSection(title="Cover Page", content=content, order=1)

    def _create_executive_summary(
        self, brief: Brief, project_plan: ProjectPlan
    ) -> ProposalSection:
        """Create executive summary section."""
        content = f"""
# Executive Summary

{self.company_name} is pleased to present this proposal for {brief.title}.

## Project Overview

{brief.description}

## Our Approach

{project_plan.summary}

## Key Highlights

- **Timeline:** {project_plan.duration_weeks} weeks from project kickoff
- **Methodology:** {project_plan.methodology[:200]}...
- **Team:** Led by {project_plan.project_lead_name or 'experienced research director'}
- **Deliverables:** Comprehensive insights package including analysis, reports, and presentations

## Investment

The total investment for this project is **${project_plan.estimated_cost:,.2f}**.

We look forward to partnering with {brief.client_name} on this important research initiative.
        """.strip()

        return ProposalSection(
            title="Executive Summary", content=content, order=2
        )

    def _create_understanding_section(self, brief: Brief) -> ProposalSection:
        """Create our understanding section."""
        content = f"""
# Our Understanding

Based on our discussions and review of your requirements, we understand that {brief.client_name} is seeking to:

{chr(10).join(f"- {obj}" for obj in brief.objectives)}

## Key Business Questions

The research will address the following key business questions:

1. {brief.objectives[0] if brief.objectives else 'To be defined'}
2. What are the critical success factors for this initiative?
3. How can we best position the offering in the market?
4. What insights will drive strategic decision-making?

## Success Criteria

This research will be successful when it provides:

- Actionable insights that inform strategic decisions
- Clear recommendations backed by robust data
- Deep understanding of the target audience
- Validated approach for market entry/optimization
        """.strip()

        return ProposalSection(
            title="Our Understanding", content=content, order=3
        )

    def _create_objectives_section(self, brief: Brief) -> ProposalSection:
        """Create research objectives section."""
        content = f"""
# Research Objectives

This research is designed to achieve the following objectives:

{chr(10).join(f"{i+1}. {obj}" for i, obj in enumerate(brief.objectives))}

Each objective will be addressed through carefully designed research activities that combine quantitative rigor with qualitative depth.
        """.strip()

        return ProposalSection(
            title="Research Objectives", content=content, order=4
        )

    def _create_methodology_section(self, project_plan: ProjectPlan) -> ProposalSection:
        """Create methodology section."""
        content = f"""
# Research Methodology

{project_plan.methodology}

## Quality Assurance

All research will be conducted in accordance with:

- Industry best practices and ethical standards
- ESOMAR guidelines for market research
- Data protection and privacy regulations
- Client-specific quality requirements

## Sample Design

Detailed sample specifications and recruitment criteria will be developed during the project design phase to ensure we reach the right respondents for robust, actionable insights.
        """.strip()

        return ProposalSection(title="Methodology", content=content, order=5)

    def _create_approach_section(self, project_plan: ProjectPlan) -> ProposalSection:
        """Create detailed approach section."""
        content = f"""
# Our Approach

{project_plan.approach}

## Project Phases

{chr(10).join(f"### {phase.get('name', f'Phase {i+1}')}{chr(10)}{phase.get('description', 'Details to be defined')}{chr(10)}" for i, phase in enumerate(project_plan.phases)) if project_plan.phases else 'Detailed project phases will be defined during kickoff.'}

## Risk Mitigation

We have identified potential risks and developed mitigation strategies:

{chr(10).join(f"- **Risk:** {risk}{chr(10)}  **Mitigation:** {mitigation}" for risk, mitigation in zip(project_plan.risks, project_plan.mitigation_strategies)) if project_plan.risks else 'Risk assessment will be conducted during project initiation.'}
        """.strip()

        return ProposalSection(title="Our Approach", content=content, order=6)

    def _create_timeline_section(self, project_plan: ProjectPlan) -> ProposalSection:
        """Create timeline section."""
        content = f"""
# Project Timeline

The project will be completed in **{project_plan.duration_weeks} weeks** from kickoff to final presentation.

## Key Milestones

{chr(10).join(f"- **{milestone.get('name')}:** {milestone.get('timing')}" for milestone in project_plan.milestones) if project_plan.milestones else 'Detailed milestones will be established during project kickoff.'}

## Timeline Assumptions

- Client feedback provided within 3 business days at key milestones
- Access to necessary stakeholders for input and validation
- Timely approval of research materials and questionnaires
        """.strip()

        return ProposalSection(title="Timeline", content=content, order=7)

    def _create_team_section(self, project_plan: ProjectPlan) -> ProposalSection:
        """Create team section."""
        content = f"""
# Project Team

Your project will be led by **{project_plan.project_lead_name or 'an experienced research director'}** and supported by a dedicated team of research professionals.

## Team Structure

{chr(10).join(f"- **{assignment.role}:** {assignment.resource_name} ({assignment.allocation:.0%} allocation)" for assignment in project_plan.resource_assignments[:5]) if project_plan.resource_assignments else 'Team structure will be finalized upon project award.'}

## Our Expertise

{self.company_name} brings deep expertise in market research with particular strength in:

- Strategic research design
- Advanced analytical techniques
- Stakeholder engagement
- Actionable insight generation
        """.strip()

        return ProposalSection(title="Project Team", content=content, order=8)

    def _create_deliverables_section(
        self, project_plan: ProjectPlan
    ) -> ProposalSection:
        """Create deliverables section."""
        content = f"""
# Deliverables

{chr(10).join(f"## {deliverable.get('name', 'Deliverable')}{chr(10)}{deliverable.get('description', 'Description to be provided')}" for deliverable in project_plan.deliverables) if project_plan.deliverables else 'Detailed deliverable specifications will be defined during project kickoff.'}

All deliverables will be delivered in professional formats suitable for executive presentation and strategic decision-making.
        """.strip()

        return ProposalSection(title="Deliverables", content=content, order=9)

    def _create_pricing_section(
        self, pricing_breakdown: Dict[str, Any]
    ) -> ProposalSection:
        """Create pricing section."""
        content = f"""
# Investment

## Pricing Summary

| Category | Amount |
|----------|--------|
| Professional Services | ${pricing_breakdown['staff_costs']:,.2f} |
| Data Collection | ${pricing_breakdown['vendor_costs']:,.2f} |
| Project Management | ${pricing_breakdown['pm_overhead']:,.2f} |
| Contingency | ${pricing_breakdown['contingency']:,.2f} |
| **Total Investment** | **${pricing_breakdown['total_price']:,.2f}** |

## Payment Terms

- 50% upon contract signing
- 50% upon completion of fieldwork

## What's Included

The investment includes all professional services, data collection, analysis, reporting, and presentations as outlined in this proposal.

## What's Excluded

- Client travel expenses (if required)
- Translation services beyond those specified
- Additional rounds of analysis beyond scope
        """.strip()

        return ProposalSection(title="Investment", content=content, order=10)

    def _create_why_us_section(self) -> ProposalSection:
        """Create why choose us section."""
        content = f"""
# Why Choose {self.company_name}

## Our Differentiators

1. **Expertise:** Deep industry knowledge and methodological excellence
2. **Partnership:** Collaborative approach ensuring your success
3. **Quality:** Rigorous standards and attention to detail
4. **Insights:** Focus on actionable recommendations, not just data
5. **Service:** Responsive, flexible, and committed to your timeline

## Our Commitment

We are committed to delivering research that drives real business impact. Your success is our success.
        """.strip()

        return ProposalSection(
            title=f"Why Choose {self.company_name}", content=content, order=11
        )

    def _create_terms_section(self) -> ProposalSection:
        """Create terms and conditions section."""
        content = """
# Terms & Conditions

## Proposal Validity

This proposal is valid for 30 days from the date of submission.

## Confidentiality

All information shared during this project will be treated as confidential and used solely for the purposes outlined in this proposal.

## Intellectual Property

All research materials, data, and deliverables become the property of the client upon final payment.

## Cancellation

If the project is cancelled after commencement, fees will be charged for work completed to date.

## Acceptance

To proceed, please sign and return this proposal along with a purchase order or confirmation email.

---

**Next Steps**

We're excited about the opportunity to partner with you on this research. Please contact us with any questions or to discuss next steps.
        """.strip()

        return ProposalSection(
            title="Terms & Conditions", content=content, order=12
        )

    def _format_team_members(
        self, resource_assignments: List
    ) -> List[Dict[str, Any]]:
        """Format team member information."""
        team_members = []

        for assignment in resource_assignments:
            if assignment.resource_type == "staff":
                team_members.append(
                    {
                        "name": assignment.resource_name,
                        "role": assignment.role,
                        "allocation": f"{assignment.allocation:.0%}",
                    }
                )

        return team_members
