"""Brief Preparation Agent - Main deep agent for brief collection and validation."""

from typing import Any, Optional

from proposal_bot import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from proposal_bot.config import get_settings
from proposal_bot.memory import create_composite_memory_backend
from proposal_bot.schemas.brief import Brief, BriefStatus
from proposal_bot.tools.email_tools import create_gmail_tools
from proposal_bot.tools.knowledge_tools import create_knowledge_tools


class BriefPreparationAgent:
    """
    Deep Agent for preparing and validating research briefs.

    This agent:
    1. Receives initial brief details (email, RFP document, etc.)
    2. Analyzes brief quality and completeness
    3. Spawns sub-agents for:
       - Email communication with sales reps
       - Searching project repositories for similar past projects
       - Web research to improve client profiles
       - CRM system integration
    4. Identifies missing information and requests clarification
    5. Validates brief with sales rep before triggering proposal workflow

    Built using LangChain's Deep Agents, which automatically provides:
    - Planning tools (write_todos)
    - File system access (ls, read_file, write_file, edit_file)
    - Subagent spawning (task tool)
    """

    def __init__(self, brief_id: str, workspace_dir: Optional[str] = None):
        """
        Initialize Brief Preparation Agent.

        Args:
            brief_id: Unique identifier for the brief
            workspace_dir: Directory for agent workspace (defaults to .agent_workspace/{brief_id})
        """
        self.brief_id = brief_id
        self.workspace_dir = workspace_dir or f".agent_workspace/brief_{brief_id}"
        self.settings = get_settings()

        # Initialize LLM
        self.llm = ChatAnthropic(
            model=self.settings.default_model,
            temperature=self.settings.temperature,
            api_key=self.settings.anthropic_api_key,
        )

        # Initialize custom tools (planning and file tools are built-in to deep agents)
        self.custom_tools = self._initialize_custom_tools()

        # Initialize memory backend for long-term persistence
        self.memory_backend = create_composite_memory_backend(
            memory_dir=f"{self.workspace_dir}/memory"
        )

        # Initialize checkpointer for human-in-the-loop workflows
        self.checkpointer = MemorySaver()

        # Initialize deep agent
        self.agent = self._create_deep_agent()

    def _initialize_custom_tools(self) -> list[Any]:
        """Initialize custom tools for this agent (not including built-in deep agent tools)."""
        tools = []

        # Email tools (Gmail integration) - skip for placeholder testing
        from proposal_bot.auth import gmail_token_manager
        credentials = gmail_token_manager.get_gmail_credentials(f"brief_prep_{self.brief_id}")
        is_placeholder = credentials and all(
            str(credentials.get(field, '')) == "placeholder"
            for field in ['client_id', 'client_secret', 'access_token', 'refresh_token']
        )

        if not is_placeholder:
            # Only add real Gmail tools if we have real credentials
            tools.extend(create_gmail_tools(agent_id=f"brief_prep_{self.brief_id}"))

        # Knowledge base tools
        tools.extend(create_knowledge_tools(self.workspace_dir))

        return tools

    def _create_deep_agent(self) -> Any:
        """Create the deep agent using create_deep_agent."""

        # Define the system prompt for the agent
        system_prompt = """You are a Brief Preparation Agent for a market research firm.

Your role is to:
1. Analyze incoming research briefs for completeness and quality
2. Identify missing information that's critical for proposal development
3. Use sub-agents to gather additional context (past projects, client info, web research)
4. Communicate with sales representatives to clarify requirements
5. Validate the final brief before triggering the proposal workflow

BUILT-IN CAPABILITIES:
You have built-in access to:
- Planning tools: Use write_todos to break down tasks and track progress
- File system: Use ls, read_file, write_file, edit_file to manage context
- Subagents: Use the task tool to spawn specialized subagents for complex tasks

CUSTOM TOOLS:
You also have access to:
- Email tools: Send and receive emails via Gmail
- Knowledge base tools: Store and retrieve learnings for future briefs

WORKFLOW:
1. Start by using write_todos to plan your approach
2. Use read_file/write_file to store brief details and analysis
3. Spawn subagents using the task tool for specialized work:
   - Email communicator: Clarify requirements with sales reps
   - Project researcher: Find similar past projects
   - Web researcher: Research client background
   - CRM integrator: Retrieve client data
4. Store learnings in the knowledge base
5. Be thorough in identifying missing information

Always break down complex tasks and track your progress systematically."""

        # Create the deep agent with LangSmith best practices
        agent = create_deep_agent(
            model=self.llm,
            tools=self.custom_tools,
            system_prompt=system_prompt,
            backend=self.memory_backend,  # Long-term memory backend
            checkpointer=self.checkpointer,  # Human-in-the-loop support
            interrupt_on=["GmailSendMessage", "GmailCreateDraft"],  # Require approval for email operations
        )

        return agent

    def process_brief(self, brief: Brief, sales_rep_email: str) -> dict[str, Any]:
        """
        Process a research brief through the full preparation workflow.

        Args:
            brief: The initial brief to process
            sales_rep_email: Email of the sales representative

        Returns:
            Dictionary containing the validated brief and workflow status
        """
        # Prepare the input for the agent
        brief_summary = f"""
New research brief received:

Client: {brief.client_name}
Contact: {brief.client_contact} ({brief.client_email})
Title: {brief.title}
Description: {brief.description}

Objectives:
{chr(10).join(f"- {obj}" for obj in brief.objectives)}

Budget Range: {brief.budget_range if brief.budget_range else 'Not specified'}
Timeline: {brief.timeline or 'Not specified'}

Sales Rep: {sales_rep_email}

Your task is to:
1. Analyze this brief for completeness and quality
2. Identify any missing critical information
3. Use sub-agents to gather additional context (past projects, client research, CRM data)
4. If information is missing, prepare clarification questions for the sales rep
5. Once all information is collected, validate the brief and confirm go-ahead

Be thorough and methodical. Use your planning tools to track progress.
        """.strip()

        # Execute the agent with simple string input
        try:
            result = self.agent.run(brief_summary)
        except Exception as e:
            # Fallback to invoke format if run fails
            result = self.agent.invoke({"input": brief_summary})

        return {
            "brief_id": self.brief_id,
            "status": "completed",
            "agent_output": result,
            "brief": brief,
        }

    def analyze_brief_quality(self, brief: Brief) -> dict[str, Any]:
        """
        Analyze the quality and completeness of a brief.

        Args:
            brief: Brief to analyze

        Returns:
            Analysis results including quality score and missing information
        """
        analysis_prompt = f"""
Analyze the following research brief for quality and completeness:

{brief.model_dump_json(indent=2)}

Provide:
1. A quality score (0-100)
2. List of missing critical information
3. List of missing optional but helpful information
4. Assessment of brief clarity
5. Recommended clarification questions

Format your response as a structured analysis.
        """.strip()

        response = self.llm.invoke([HumanMessage(content=analysis_prompt)])

        return {
            "analysis": response.content,
            "brief_id": self.brief_id,
        }
