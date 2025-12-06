"""Proposal Agent - Main deep agent for proposal generation."""

from typing import Any, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from proposal_bot.config import get_settings
from proposal_bot.schemas.brief import Brief
from proposal_bot.schemas.project import Project, ProjectPlan, ProjectStatus, ResourceAssignment
from proposal_bot.schemas.proposal import Proposal
from proposal_bot.tools.email_tools import create_gmail_tools
from proposal_bot.tools.file_tools import create_file_tools
from proposal_bot.tools.knowledge_tools import create_knowledge_tools
from proposal_bot.tools.planning_tools import create_planning_tools
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

        # Initialize tools
        self.tools = self._initialize_tools()

        # Initialize agent
        self.agent = self._create_agent()

    def _initialize_tools(self) -> list[Any]:
        """Initialize all tools for this agent."""
        tools = []

        # Planning tools
        tools.extend(create_planning_tools(self.workspace_dir))

        # File system tools
        tools.extend(create_file_tools(self.workspace_dir))

        # Resource tools (Google Sheets)
        tools.extend(create_resource_tools())

        # Email tools
        tools.extend(create_gmail_tools())

        # Knowledge tools
        tools.extend(create_knowledge_tools(self.workspace_dir))

        # Add sub-agent spawning tool
        tools.append(self._create_task_tool())

        return tools

    def _create_task_tool(self) -> Any:
        """Create the task tool for spawning sub-agents."""
        from langchain.tools import tool

        @tool
        def spawn_subagent(task_description: str, agent_type: str, context: str = "") -> str:
            """
            Spawn a specialized sub-agent for a specific task.

            Args:
                task_description: Detailed description of the task
                agent_type: Type of sub-agent (resource_validator/lead_validator/pricing_calculator)
                context: Additional context for the sub-agent

            Returns:
                Result from the sub-agent
            """
            if agent_type == "resource_validator":
                return self._resource_validator_subagent(task_description, context)
            elif agent_type == "lead_validator":
                return self._lead_validator_subagent(task_description, context)
            elif agent_type == "pricing_calculator":
                return self._pricing_calculator_subagent(task_description, context)
            else:
                return f"Unknown agent type: {agent_type}"

        return spawn_subagent

    def _resource_validator_subagent(self, task: str, context: str) -> str:
        """
        Sub-agent for validating resource availability and pricing.

        This sub-agent sends validation emails to resource managers and processes responses.
        """
        # In a full implementation, this would:
        # 1. Parse resource requirements from context
        # 2. Send validation emails using email tools
        # 3. Monitor for responses
        # 4. Parse and validate responses
        # 5. Update resource assignments
        return f"Resource Validator Sub-agent: {task} (simulated)"

    def _lead_validator_subagent(self, task: str, context: str) -> str:
        """
        Sub-agent for validating project design with proposed lead.

        This sub-agent communicates with the project lead to validate design decisions.
        """
        return f"Lead Validator Sub-agent: {task} (simulated)"

    def _pricing_calculator_subagent(self, task: str, context: str) -> str:
        """
        Sub-agent for calculating final pricing with business logic.

        This sub-agent applies pricing rules, markups, and discounts.
        """
        return f"Pricing Calculator Sub-agent: {task} (simulated)"

    def _create_agent(self) -> AgentExecutor:
        """Create the ReAct agent with tools."""
        prompt = PromptTemplate.from_template(
            """You are a Proposal Generation Agent for a market research firm.

Your role is to:
1. Analyze validated brief and create comprehensive project plan
2. Resource the plan by searching for qualified staff and approved vendors
3. Spawn sub-agents to validate resources via email (availability, capacity, pricing)
4. Identify the best project lead from qualified staff
5. Spawn sub-agent to validate key design decisions with the project lead
6. Apply business logic and pricing rules to finalize the proposal
7. Generate a formatted, professional proposal document

You have access to the following tools:
{tools}

Tool names: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT:
- Start by using write_todos to create a comprehensive project plan
- Use resource search tools to find qualified staff and vendors
- Spawn resource_validator sub-agents for each resource that needs validation
- Select a project lead based on expertise, availability, and past performance
- Spawn lead_validator sub-agent to confirm design approach
- Use file tools to draft and refine the proposal document
- Store successful patterns in knowledge base for future proposals

Be thorough, professional, and ensure all validations are complete before finalizing.

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
        )

        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=20,
            handle_parsing_errors=True,
        )

        return executor

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

        result = self.agent.invoke({"input": brief_summary})

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
