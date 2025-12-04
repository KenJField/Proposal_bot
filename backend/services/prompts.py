"""
Prompt templates for LLM interactions.
"""

from typing import List, Dict, Any
from models.schemas import ExtractedRequirements


# System prompts
REQUIREMENT_EXTRACTION_SYSTEM = """You are an expert at analyzing Request for Proposals (RFPs) in the market research industry. Your task is to extract structured requirements from RFP documents.

Extract the following information:
1. Project title/name
2. Research objectives
3. Requested methodologies (quantitative surveys, focus groups, interviews, etc.)
4. Target audience/respondent criteria
5. Sample size requirements
6. Geographic scope
7. Timeline (start date, end date, key milestones)
8. Budget (if mentioned)
9. Required deliverables
10. Evaluation criteria

Be thorough but concise. If information is missing or ambiguous, note it in the missing_information and ambiguities fields. Provide a confidence score (0-100) for your extraction.

Always respond with valid JSON only."""


PROPOSAL_GENERATION_SYSTEM = """You are an expert proposal writer for a market research firm. You write compelling, professional proposals that win business.

Your proposals should:
1. Demonstrate deep understanding of client needs
2. Present clear, detailed methodology
3. Showcase relevant expertise
4. Provide realistic timelines and pricing
5. Differentiate from competitors
6. Be professional yet personable in tone

Always ground proposals in provided capabilities and team members. Don't invent methodologies or expertise not mentioned in the context.

Always respond with valid JSON only."""


PROPOSAL_REVISION_SYSTEM = """You are an expert proposal editor for a market research firm. Your task is to revise proposals based on feedback while maintaining quality and professionalism.

When revising:
1. Address all feedback points specifically
2. Maintain consistency across sections
3. Preserve good content that wasn't critiqued
4. Ensure pricing changes are realistic and justified
5. Keep the professional, winning tone

Always respond with valid JSON only."""


# Extraction prompt
def get_extraction_prompt(rfp_content: str) -> str:
    """Generate prompt for requirement extraction."""
    return f"""Please extract structured requirements from this RFP:

<rfp_content>
{rfp_content}
</rfp_content>

Respond in JSON format following this exact schema:
{{
  "project_title": "string or null",
  "objectives": ["array of objective strings"],
  "methodologies_requested": ["array of methodology strings like 'quantitative survey', 'focus groups', 'interviews'"],
  "target_audience": "string describing who should be surveyed/interviewed or null",
  "sample_size": "string describing sample requirements or null",
  "geography": ["array of geographic locations"],
  "timeline": {{
    "start_date": "YYYY-MM-DD or null",
    "end_date": "YYYY-MM-DD or null",
    "key_milestones": [
      {{"date": "YYYY-MM-DD", "description": "string"}}
    ]
  }},
  "budget": {{
    "amount": number or null,
    "currency": "string like USD",
    "is_fixed": boolean or null
  }},
  "deliverables": ["array of required deliverable strings"],
  "evaluation_criteria": ["array of criteria strings"],
  "extraction_confidence": number between 0 and 100,
  "missing_information": ["array of strings describing what information is missing"],
  "ambiguities": ["array of strings describing ambiguous requirements"]
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or additional text."""


# Proposal generation prompt
def get_proposal_prompt(
    requirements: ExtractedRequirements,
    matched_capabilities: List[Dict[str, Any]],
    available_resources: List[Dict[str, Any]],
    firm_info: Dict[str, Any],
) -> str:
    """Generate prompt for proposal creation."""

    capabilities_text = "\n".join(
        [
            f"- {c['name']} ({c['category']}): {c['detailed_description'] or c['description']}"
            for c in matched_capabilities
        ]
    )

    team_text = "\n".join(
        [
            f"- {r['name']} ({r['title']}): {r['bio']}\n  Skills: {', '.join(r['skills'])}\n  Rate: ${r['hourly_rate']}/hr"
            for r in available_resources[:5]  # Top 5 resources
        ]
    )

    return f"""Generate a complete research proposal for this RFP:

<client_requirements>
Title: {requirements.project_title or 'Not specified'}
Objectives: {', '.join(requirements.objectives)}
Methodologies Requested: {', '.join(requirements.methodologies_requested)}
Target Audience: {requirements.target_audience or 'Not specified'}
Sample Size: {requirements.sample_size or 'Not specified'}
Geography: {', '.join(requirements.geography)}
Timeline: {requirements.timeline.get('start_date', 'TBD') if requirements.timeline else 'TBD'} to {requirements.timeline.get('end_date', 'TBD') if requirements.timeline else 'TBD'}
Budget: {requirements.budget.get('amount', 'Not specified') if requirements.budget else 'Not specified'} {requirements.budget.get('currency', '') if requirements.budget else ''}
Deliverables: {', '.join(requirements.deliverables)}
Evaluation Criteria: {', '.join(requirements.evaluation_criteria)}
</client_requirements>

<our_capabilities>
{capabilities_text}
</our_capabilities>

<available_team>
{team_text}
</available_team>

<firm_information>
Name: {firm_info.get('name', 'Research Solutions Group')}
Tagline: {firm_info.get('tagline', 'Insights that drive decisions')}
Differentiators: {', '.join(firm_info.get('differentiators', ['Experienced team', 'Proven methodologies', 'Client-focused approach']))}
</firm_information>

Create a comprehensive proposal with these sections:

1. EXECUTIVE SUMMARY (2-3 paragraphs)
   - Hook with understanding of their challenge
   - Our solution in brief
   - Key benefits

2. UNDERSTANDING OF NEEDS (3-4 paragraphs)
   - Demonstrate comprehension of objectives
   - Context and challenges
   - Why this research matters

3. PROPOSED METHODOLOGY
   - Overview (1-2 paragraphs explaining overall approach)
   - Detailed approach (3-5 paragraphs describing methodology)
   - Phases (3-5 phases, each with name, description, duration in weeks, and deliverables)

4. TIMELINE
   - Total duration in weeks
   - Key milestones with dates (use realistic dates based on requirements)

5. PROJECT TEAM (3-5 people from available team)
   - Name, role in project, brief bio
   - Hours allocated to project

6. PRICING
   - Line items with descriptions, quantities, unit costs, and totals
   - Include project management, data collection, analysis, reporting
   - Subtotal, tax (0 for now), final total
   - Ensure total is realistic based on scope and aligns roughly with client budget if specified

7. WHY CHOOSE US (2-3 paragraphs)
   - Relevant experience
   - Differentiators
   - Client-centric approach

Return response in JSON format following this exact schema:
{{
  "executive_summary": "string",
  "understanding_of_needs": "string",
  "proposed_methodology": {{
    "overview": "string",
    "approach": "string",
    "phases": [
      {{
        "name": "string",
        "description": "string",
        "duration_weeks": number,
        "deliverables": ["array of strings"]
      }}
    ]
  }},
  "timeline": {{
    "total_duration_weeks": number,
    "milestones": [
      {{"date": "YYYY-MM-DD", "milestone": "string"}}
    ]
  }},
  "team": [
    {{
      "name": "string",
      "role": "string",
      "bio": "string",
      "hours_allocated": number
    }}
  ],
  "pricing": {{
    "line_items": [
      {{
        "description": "string",
        "quantity": number,
        "unit_cost": number,
        "total": number
      }}
    ],
    "subtotal": number,
    "tax": number,
    "total": number,
    "currency": "USD"
  }},
  "why_us": "string",
  "case_studies": []
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or additional text."""


# Revision prompt
def get_revision_prompt(
    current_proposal: Dict[str, Any], feedback: str
) -> str:
    """Generate prompt for proposal revision."""

    import json

    current_json = json.dumps(current_proposal, indent=2)

    return f"""You are revising a market research proposal based on client feedback.

<current_proposal>
{current_json}
</current_proposal>

<feedback>
{feedback}
</feedback>

Apply the feedback to improve the proposal. Make targeted changes while preserving the overall quality and structure.

If feedback requests price changes:
- Adjust line items accordingly while maintaining realistic costs
- Ensure subtotal and total are recalculated correctly

If feedback requests content changes:
- Update the relevant sections specifically
- Maintain consistency across all sections
- Keep the professional, compelling tone

Return the complete revised proposal in JSON format using the same schema as the original proposal.

IMPORTANT: Return ONLY valid JSON, no markdown formatting or additional text."""
