"""Proposal Agent - Main deep agent for proposal generation."""

from typing import Any, Optional

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from proposal_bot.config import get_settings
from proposal_bot.schemas.brief import Brief
from proposal_bot.schemas.project import Project, ProjectPlan, ProjectStatus, ResourceAssignment
from proposal_bot.schemas.proposal import Proposal
from proposal_bot.tools.email_tools import create_gmail_tools
from proposal_bot.tools.knowledge_tools import create_knowledge_tools
from proposal_bot.tools.resource_tools import create_resource_tools


class ProposalAgent:
    """
    Deep Agent for generating market research proposals.

    This agent:
    1. Receives validated brief from Brief Preparation Agent
    2. Creates initial project plan
    3. Resources the plan by:
       - Searching company capabilities, staff, and vendors
       - Matching requirements to available resources
    4. Spawns sub-agents to validate resources via email:
       - Staff availability and rates
       - Vendor capacity and pricing
       - Manager approvals
    5. Identifies qualified project lead
    6. Spawns sub-agent to validate design decisions with project lead
    7. Applies business logic and pricing rules
    8. Generates formatted proposal document

    Built using LangChain's Deep Agents, which automatically provides:
    - Planning tools (write_todos)
    - File system access (ls, read_file, write_file, edit_file)
    - Subagent spawning (task tool)
    """

    def __init__(self, project_id: str, workspace_dir: Optional[str] = None):
        """
        Initialize Proposal Agent.

        Args:
            project_id: Unique identifier for the project
            workspace_dir: Directory for agent workspace
        """
        self.project_id = project_id
        self.workspace_dir = workspace_dir or f".agent_workspace/project_{project_id}"
        self.settings = get_settings()

        # Initialize LLM
        self.llm = ChatAnthropic(
            model=self.settings.default_model,
            temperature=self.settings.temperature,
            api_key=self.settings.anthropic_api_key,
        )

        # Initialize custom tools (planning and file tools are built-in to deep agents)
        self.custom_tools = self._initialize_custom_tools()

        # Initialize deep agent
        self.agent = self._create_deep_agent()

    def _initialize_custom_tools(self) -> list[Any]:
        """Initialize custom tools for this agent (not including built-in deep agent tools)."""
        tools = []

        # Resource tools (Google Sheets)
        tools.extend(create_resource_tools())

        # Email tools
        tools.extend(create_gmail_tools())

        # Knowledge tools
        tools.extend(create_knowledge_tools(self.workspace_dir))

        return tools

    def _create_deep_agent(self) -> Any:
        """Create the deep agent using create_deep_agent."""

        # Define the system prompt for the agent
        system_prompt = """You are a Proposal Generation Agent for a market research firm.

Your role is to:
1. Analyze validated brief and create comprehensive project plan
2. Resource the plan by searching for qualified staff and approved vendors
3. Spawn sub-agents to validate resources via email (availability, capacity, pricing)
4. Identify the best project lead from qualified staff
5. Spawn sub-agent to validate key design decisions with the project lead
6. Apply business logic and pricing rules to finalize the proposal
7. Generate a formatted, professional proposal document

BUILT-IN CAPABILITIES:
You have built-in access to:
- Planning tools: Use write_todos to break down tasks and track progress
- File system: Use ls, read_file, write_file, edit_file to manage context
- Subagents: Use the task tool to spawn specialized subagents for complex tasks

CUSTOM TOOLS:
You also have access to:
- Resource tools: Search for staff and vendors in Google Sheets
- Email tools: Send and receive emails via Gmail for validations
- Knowledge base tools: Store and retrieve successful proposal patterns

WORKFLOW:
1. Start by using write_todos to create a comprehensive project plan
2. Use resource search tools to find qualified staff and vendors
3. Spawn resource_validator sub-agents for each resource that needs validation
4. Select a project lead based on expertise, availability, and past performance
5. Spawn lead_validator sub-agent to confirm design approach
6. Use file tools to draft and refine the proposal document
7. Store successful patterns in knowledge base for future proposals

Be thorough, professional, and ensure all validations are complete before finalizing."""

        # Create the deep agent
        agent = create_deep_agent(
            model=self.llm,
            tools=self.custom_tools,
            system_prompt=system_prompt,
        )

        return agent

    def generate_proposal(self, brief: Brief) -> dict[str, Any]:
        """
        Generate a complete proposal from a validated brief.

        Args:
            brief: Validated research brief

        Returns:
            Dictionary containing the proposal and project details
        """
        brief_summary = f"""
Generate a comprehensive market research proposal for the following validated brief:

CLIENT INFORMATION:
- Name: {brief.client_name}
- Contact: {brief.client_contact} ({brief.client_email})

PROJECT DETAILS:
- Title: {brief.title}
- Description: {brief.description}
- Objectives: {', '.join(brief.objectives)}
- Budget Range: ${brief.budget_range[0]:,.0f} - ${brief.budget_range[1]:,.0f if brief.budget_range else 'TBD'}
- Timeline: {brief.timeline}
- Target Audience: {brief.target_audience}
- Preferred Methodologies: {', '.join(brief.methodology_preferences)}
- Deliverables: {', '.join(brief.deliverables)}

REQUIREMENTS:
{brief.requirements}

Your tasks:
1. Create detailed project plan with methodology, phases, and timeline
2. Search for and assign qualified staff and vendors
3. Validate all resource assignments via email
4. Select project lead and validate design approach
5. Calculate final pricing with appropriate markup
6. Generate professional proposal document

Use your planning tools to organize this work systematically.
        """.strip()

        # Execute the agent with messages format expected by deep agents
        result = self.agent.invoke({
            "messages": [{"role": "user", "content": brief_summary}]
        })

        return {
            "project_id": self.project_id,
            "brief_id": brief.id,
            "status": "completed",
            "agent_output": result,
        }

    def create_project_plan(self, brief: Brief) -> ProjectPlan:
        """
        Create initial project plan from brief.

        Args:
            brief: Research brief

        Returns:
            Initial project plan
        """
        planning_prompt = f"""
Create a detailed project plan for this research project:

Brief: {brief.model_dump_json(indent=2)}

Include:
1. Project title and executive summary
2. Research objectives
3. Detailed methodology
4. Project phases with timelines
5. Resource requirements (roles, not specific people yet)
6. Deliverables with specifications
7. Timeline and milestones
8. Initial budget estimate
9. Risks and mitigation strategies

Format as a structured project plan.
        """.strip()

        response = self.llm.invoke([HumanMessage(content=planning_prompt)])

        # In production, this would parse the response into a ProjectPlan object
        # For now, return a placeholder
        return ProjectPlan(
            title=brief.title,
            summary="Project plan created",
            objectives=brief.objectives,
            approach="To be defined",
            methodology="To be defined",
            duration_weeks=8,
            estimated_cost=0.0,
        )
