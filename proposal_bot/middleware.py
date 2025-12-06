"""
LangChain Deep Agents Middleware Configuration

This module implements proper middleware composition following LangChain's
recommended patterns for deep agents, ensuring consistent behavior across
all agents in the system.
"""

from typing import Any, Dict, List, Optional

from deepagents import (
    FilesystemMiddleware,
    SubAgentMiddleware,
    TodoListMiddleware,
    create_deep_agent,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from proposal_bot.memory import create_composite_memory_backend


class ProposalBotAgentConfig:
    """
    Configuration class for Proposal Bot agents following LangChain best practices.

    This ensures consistent middleware composition and agent setup across
    all agents in the system.
    """

    def __init__(
        self,
        model: BaseLanguageModel,
        tools: List[BaseTool],
        system_prompt: str,
        workspace_dir: str,
        interrupt_on: Optional[List[str]] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ):
        """
        Initialize agent configuration.

        Args:
            model: The language model to use
            tools: Custom tools for the agent
            system_prompt: System prompt for the agent
            workspace_dir: Directory for agent workspace and memory
            interrupt_on: List of tool names that require human approval
            checkpointer: Checkpointer for human-in-the-loop workflows
        """
        self.model = model
        self.tools = tools
        self.system_prompt = system_prompt
        self.workspace_dir = workspace_dir
        self.interrupt_on = interrupt_on or []
        self.checkpointer = checkpointer

        # Initialize memory backend
        self.memory_backend = create_composite_memory_backend(
            memory_dir=f"{workspace_dir}/memory"
        )

    def create_agent(self) -> Any:
        """
        Create a deep agent with proper middleware composition.

        Returns:
            Configured deep agent
        """
        return create_deep_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.system_prompt,
            backend=self.memory_backend,
            checkpointer=self.checkpointer,
            interrupt_on=self.interrupt_on,
        )


class MiddlewareStack:
    """
    Middleware stack for consistent agent behavior.

    This class manages the composition of middleware following LangChain's
    patterns, ensuring all agents have the same foundational capabilities.
    """

    def __init__(self):
        """Initialize the middleware stack."""
        self._middleware = []

        # Add core middleware in the correct order
        self._add_core_middleware()

    def _add_core_middleware(self):
        """Add core middleware required for all Proposal Bot agents."""
        # Filesystem middleware for context management
        self._middleware.append(FilesystemMiddleware())

        # TodoList middleware for planning and task tracking
        self._middleware.append(TodoListMiddleware())

        # SubAgent middleware for delegation
        self._middleware.append(SubAgentMiddleware())

    def add_middleware(self, middleware: Any):
        """
        Add custom middleware to the stack.

        Args:
            middleware: Middleware instance to add
        """
        self._middleware.append(middleware)

    def get_middleware_stack(self) -> List[Any]:
        """
        Get the complete middleware stack.

        Returns:
            List of configured middleware
        """
        return self._middleware.copy()

    def create_agent_with_middleware(
        self,
        model: BaseLanguageModel,
        tools: List[BaseTool],
        system_prompt: str,
        **kwargs
    ) -> Any:
        """
        Create an agent with the full middleware stack.

        Args:
            model: Language model
            tools: Custom tools
            system_prompt: System prompt
            **kwargs: Additional arguments for create_deep_agent

        Returns:
            Configured deep agent with middleware
        """
        # Get middleware stack
        middleware_stack = self.get_middleware_stack()

        # Create agent with middleware
        return create_deep_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            middleware=middleware_stack,
            **kwargs
        )


def create_proposal_agent_config(
    agent_type: str,
    workspace_dir: str,
    tools: List[BaseTool],
    interrupt_on: Optional[List[str]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> ProposalBotAgentConfig:
    """
    Create a standardized agent configuration for Proposal Bot agents.

    Args:
        agent_type: Type of agent ("brief_preparation", "proposal", "background_memory")
        workspace_dir: Workspace directory for the agent
        tools: Custom tools for the agent
        interrupt_on: Tools requiring human approval
        checkpointer: Checkpointer for HITL workflows

    Returns:
        Configured agent configuration
    """
    # Model configuration
    model = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.3,  # Lower temperature for consistent agent behavior
        max_tokens=4096,
    )

    # System prompts based on agent type
    system_prompts = {
        "brief_preparation": """You are a Brief Preparation Agent for a market research firm.

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
3. Spawn subagents using the task tool for specialized work
4. Store learnings in the knowledge base
5. Be thorough in identifying missing information

Always break down complex tasks and track your progress systematically.""",

        "proposal": """You are a Proposal Generation Agent for a market research firm.

Your role is to:
1. Analyze validated brief and create comprehensive project plan
2. Resource the plan by searching for qualified staff and approved vendors
3. Spawn sub-agents to validate resources via email (availability, capacity, pricing)
4. Identify the best project lead from qualified staff
5. Spawn sub-agent to validate design decisions with the project lead
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

Be thorough, professional, and ensure all validations are complete before finalizing.""",

        "background_memory": """You are a Background Memory Agent for a proposal generation system.

Your role is to:
1. Monitor email communications related to proposals
2. Extract and update knowledge about:
   - Vendor pricing and capabilities
   - Staff skills, availability patterns, and performance
   - Successful proposal designs and patterns
   - Client preferences and feedback
3. Identify trends and patterns in the data
4. Maintain an up-to-date knowledge base for future proposals

BUILT-IN CAPABILITIES:
You have built-in access to:
- Planning tools: Use write_todos to break down monitoring tasks
- File system: Use ls, read_file, write_file to manage extracted data
- Subagents: Use the task tool if needed for specialized analysis

CUSTOM TOOLS:
You also have access to:
- Email tools: Search and read emails from Gmail
- Knowledge base tools: Store and retrieve learnings

WORKFLOW:
1. Extract factual information accurately from emails
2. Update knowledge incrementally as new information arrives
3. Identify patterns across multiple projects
4. Maintain data quality and consistency
5. Use the file system to track extraction progress

Always focus on extracting accurate, actionable knowledge.""",
    }

    system_prompt = system_prompts.get(agent_type, "")
    if not system_prompt:
        raise ValueError(f"Unknown agent type: {agent_type}")

    # Default interrupt_on for Gmail operations if not specified
    if interrupt_on is None:
        interrupt_on = ["GmailSendMessage", "GmailCreateDraft", "GmailSearch"]

    return ProposalBotAgentConfig(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        workspace_dir=workspace_dir,
        interrupt_on=interrupt_on,
        checkpointer=checkpointer,
    )
