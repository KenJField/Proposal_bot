"""Background Memory Agent - Monitors emails and updates knowledge base."""

from typing import Any, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic

from proposal_bot.config import get_settings
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

        # Initialize tools
        self.tools = self._initialize_tools()

        # Initialize agent
        self.agent = self._create_agent()

    def _initialize_tools(self) -> list[Any]:
        """Initialize tools for this agent."""
        tools = []

        # Email tools for monitoring
        tools.extend(create_gmail_tools())

        # Knowledge tools for memory updates
        tools.extend(create_knowledge_tools(self.workspace_dir))

        return tools

    def _create_agent(self) -> AgentExecutor:
        """Create the agent for memory management."""
        prompt = PromptTemplate.from_template(
            """You are a Background Memory Agent for a proposal generation system.

Your role is to:
1. Monitor email communications related to proposals
2. Extract and update knowledge about:
   - Vendor pricing and capabilities
   - Staff skills, availability patterns, and performance
   - Successful proposal designs and patterns
   - Client preferences and feedback
3. Identify trends and patterns in the data
4. Maintain an up-to-date knowledge base for future proposals

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
- Extract factual information accurately
- Update knowledge incrementally as new information arrives
- Identify patterns across multiple projects
- Maintain data quality and consistency

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
            max_iterations=10,
            handle_parsing_errors=True,
        )

        return executor

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

        result = self.agent.invoke({"input": email_summary})

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

        result = self.agent.invoke({"input": monitoring_task})

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

        result = self.agent.invoke({"input": analysis_task})

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
