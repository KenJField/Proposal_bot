"""Background Memory Agent - Monitors emails and updates knowledge base."""

from typing import Any, Optional

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver

from proposal_bot.config import get_settings
from proposal_bot.memory import create_composite_memory_backend
from proposal_bot.tools.email_tools import create_gmail_tools
from proposal_bot.tools.knowledge_tools import create_knowledge_tools


class BackgroundMemoryAgent:
    """
    Background agent that monitors email communications and updates system memory.

    This agent:
    1. Monitors incoming email responses to validation requests
    2. Parses responses for key information (pricing, availability, capabilities)
    3. Updates knowledge base with:
       - Vendor pricing updates
       - Staff capabilities and skills
       - Successful proposal patterns
       - Design preferences from project leads
    4. Identifies trends and patterns in responses
    5. Suggests improvements to proposal generation logic

    Built using LangChain's Deep Agents, which automatically provides:
    - Planning tools (write_todos)
    - File system access (ls, read_file, write_file, edit_file)
    - Subagent spawning (task tool)
    """

    def __init__(self, workspace_dir: str = ".agent_workspace/memory"):
        """
        Initialize Background Memory Agent.

        Args:
            workspace_dir: Directory for agent workspace
        """
        self.workspace_dir = workspace_dir
        self.settings = get_settings()

        # Initialize LLM - use faster model for background processing
        self.llm = ChatAnthropic(
            model=self.settings.fast_model,
            temperature=0.3,  # Lower temperature for factual extraction
            api_key=self.settings.anthropic_api_key,
        )

        # Initialize custom tools
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
        """Initialize custom tools for this agent."""
        tools = []

        # Email tools for monitoring
        tools.extend(create_gmail_tools(agent_id="background_memory"))

        # Knowledge tools for memory updates
        tools.extend(create_knowledge_tools(self.workspace_dir))

        return tools

    def _create_deep_agent(self) -> Any:
        """Create the deep agent using create_deep_agent."""

        # Define the system prompt for the agent
        system_prompt = """You are a Background Memory Agent for a proposal generation system.

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

Always focus on extracting accurate, actionable knowledge."""

        # Create the deep agent with LangSmith best practices
        agent = create_deep_agent(
            model=self.llm,
            tools=self.custom_tools,
            system_prompt=system_prompt,
            backend=self.memory_backend,  # Long-term memory backend
            checkpointer=self.checkpointer,  # Human-in-the-loop support
            interrupt_on=["GmailSendMessage", "GmailSearch"],  # Require approval for email operations
        )

        return agent

    def process_email_response(self, email_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process an email response and extract knowledge.

        Args:
            email_data: Email data including sender, subject, body

        Returns:
            Dictionary with extracted knowledge and updates made
        """
        email_summary = f"""
Process the following email response and update the knowledge base:

From: {email_data.get('from')}
Subject: {email_data.get('subject')}
Body:
{email_data.get('body')}

Extract and store:
1. Any pricing information or rate confirmations
2. Availability or capacity information
3. Skills, capabilities, or expertise mentioned
4. Design feedback or preferences
5. Successful proposal patterns or approaches

Update the appropriate knowledge categories.
        """.strip()

        # Execute the agent with messages format expected by deep agents
        result = self.agent.invoke({
            "messages": [{"role": "user", "content": email_summary}]
        })

        return {
            "status": "processed",
            "email_id": email_data.get("id"),
            "updates": result,
        }

    def monitor_project_emails(self, project_id: str) -> dict[str, Any]:
        """
        Monitor all emails for a specific project and update knowledge.

        Args:
            project_id: Project ID to monitor

        Returns:
            Summary of knowledge updates
        """
        monitoring_task = f"""
Search for and process all emails related to project {project_id}.

For each email:
1. Extract relevant knowledge (pricing, capabilities, feedback)
2. Update the knowledge base
3. Log any patterns or insights

Provide a summary of all updates made.
        """.strip()

        # Execute the agent
        result = self.agent.invoke({
            "messages": [{"role": "user", "content": monitoring_task}]
        })

        return {
            "project_id": project_id,
            "status": "monitored",
            "summary": result,
        }

    def analyze_validation_patterns(self) -> dict[str, Any]:
        """
        Analyze patterns in validation responses across all projects.

        Returns:
            Analysis of patterns and recommendations
        """
        analysis_task = """
Analyze all validation responses in the knowledge base to identify:

1. Common availability patterns (when resources are typically available)
2. Pricing trends (rate increases, seasonal variations)
3. Resource preferences (which resources are most often selected)
4. Design patterns (commonly successful methodologies, team structures)
5. Client feedback patterns

Provide actionable insights for improving future proposals.
        """.strip()

        # Execute the agent
        result = self.agent.invoke({
            "messages": [{"role": "user", "content": analysis_task}]
        })

        return {
            "status": "analyzed",
            "insights": result,
        }

    def update_vendor_pricing(self, vendor_id: str, new_pricing: dict[str, Any]) -> str:
        """
        Update vendor pricing information in knowledge base.

        Args:
            vendor_id: Vendor identifier
            new_pricing: New pricing information

        Returns:
            Confirmation message
        """
        from proposal_bot.tools.knowledge_tools import create_knowledge_tools

        knowledge_tools = create_knowledge_tools(self.workspace_dir)
        store_tool = next(t for t in knowledge_tools if t.name == "store_knowledge")

        return store_tool.run(
            {
                "category": "vendor_pricing",
                "key": vendor_id,
                "value": new_pricing,
                "metadata": {"source": "validation_response", "auto_updated": True},
            }
        )

    def update_staff_capabilities(self, staff_id: str, new_capabilities: dict[str, Any]) -> str:
        """
        Update staff capabilities in knowledge base.

        Args:
            staff_id: Staff identifier
            new_capabilities: Updated capability information

        Returns:
            Confirmation message
        """
        from proposal_bot.tools.knowledge_tools import create_knowledge_tools

        knowledge_tools = create_knowledge_tools(self.workspace_dir)
        store_tool = next(t for t in knowledge_tools if t.name == "store_knowledge")

        return store_tool.run(
            {
                "category": "staff_capabilities",
                "key": staff_id,
                "value": new_capabilities,
                "metadata": {"source": "validation_response", "auto_updated": True},
            }
        )
