"""Brief Preparation Agent - Main deep agent for brief collection and validation."""

from typing import Any, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from proposal_bot.config import get_settings
from proposal_bot.schemas.brief import Brief, BriefStatus
from proposal_bot.tools.email_tools import create_gmail_tools
from proposal_bot.tools.file_tools import create_file_tools
from proposal_bot.tools.planning_tools import create_planning_tools
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

        # Initialize tools
        self.tools = self._initialize_tools()

        # Initialize agent
        self.agent = self._create_agent()

    def _initialize_tools(self) -> list[Any]:
        """Initialize all tools for this agent."""
        tools = []

        # Planning tools (write_todos)
        tools.extend(create_planning_tools(self.workspace_dir))

        # File system tools
        tools.extend(create_file_tools(self.workspace_dir))

        # Email tools (Gmail integration)
        tools.extend(create_gmail_tools())

        # Knowledge base tools
        tools.extend(create_knowledge_tools(self.workspace_dir))

        # Add task tool for spawning sub-agents
        tools.append(self._create_task_tool())

        return tools

    def _create_task_tool(self) -> Any:
        """Create the task tool for spawning sub-agents."""
        from langchain.tools import tool

        @tool
        def spawn_subagent(task_description: str, agent_type: str) -> str:
            """
            Spawn a specialized sub-agent for a specific task.

            Args:
                task_description: Detailed description of the task for the sub-agent
                agent_type: Type of sub-agent (email_communicator/project_researcher/web_researcher/crm_integrator)

            Returns:
                Result from the sub-agent
            """
            # Create a specialized sub-agent based on type
            if agent_type == "email_communicator":
                return self._email_communicator_subagent(task_description)
            elif agent_type == "project_researcher":
                return self._project_researcher_subagent(task_description)
            elif agent_type == "web_researcher":
                return self._web_researcher_subagent(task_description)
            elif agent_type == "crm_integrator":
                return self._crm_integrator_subagent(task_description)
            else:
                return f"Unknown agent type: {agent_type}"

        return spawn_subagent

    def _email_communicator_subagent(self, task: str) -> str:
        """Sub-agent for email communication with sales reps."""
        # This sub-agent handles back-and-forth email communication
        # with sales reps to clarify brief details
        return f"Email Communicator Sub-agent executed: {task}"

    def _project_researcher_subagent(self, task: str) -> str:
        """Sub-agent for searching past projects."""
        # This sub-agent searches project repositories for similar past work
        return f"Project Researcher Sub-agent executed: {task}"

    def _web_researcher_subagent(self, task: str) -> str:
        """Sub-agent for web research about the client."""
        # This sub-agent performs web research to build client profiles
        return f"Web Researcher Sub-agent executed: {task}"

    def _crm_integrator_subagent(self, task: str) -> str:
        """Sub-agent for CRM integration."""
        # This sub-agent retrieves client data from CRM systems
        return f"CRM Integrator Sub-agent executed: {task}"

    def _create_agent(self) -> AgentExecutor:
        """Create the ReAct agent with tools."""
        # Define the agent prompt
        prompt = PromptTemplate.from_template(
            """You are a Brief Preparation Agent for a market research firm.

Your role is to:
1. Analyze incoming research briefs for completeness and quality
2. Identify missing information that's critical for proposal development
3. Use sub-agents to gather additional context (past projects, client info, web research)
4. Communicate with sales representatives to clarify requirements
5. Validate the final brief before triggering the proposal workflow

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
- Always start by using write_todos to plan your approach
- Break down complex tasks and track your progress
- Use spawn_subagent for specialized tasks (email, research, CRM)
- Store learnings in the knowledge base for future briefs
- Be thorough in identifying missing information

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
        )

        # Create the ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

        # Create executor with verbose output
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=15,
            handle_parsing_errors=True,
        )

        return executor

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

        # Execute the agent
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
