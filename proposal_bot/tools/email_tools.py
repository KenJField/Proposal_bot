"""Email tools using LangChain Gmail integration with audit logging."""

from typing import Any

from langchain_google_community.gmail.toolkit import GmailToolkit

from proposal_bot.audit import audit_logger
from proposal_bot.auth import gmail_token_manager


def create_gmail_tools(agent_id: str = "default_agent") -> list[Any]:
    """
    Create Gmail tools for email communication using LangChain's Gmail toolkit.

    Enhanced with LangSmith authentication and comprehensive audit logging.

    The toolkit provides these tools out of the box:
    - GmailCreateDraft: Create email drafts (requires approval)
    - GmailSendMessage: Send emails (requires approval)
    - GmailSearch: Search emails by query (requires approval)
    - GmailGetMessage: Get specific email messages
    - GmailGetThread: Get email thread conversations

    Args:
        agent_id: Unique identifier for the agent using these tools

    Returns:
        List of Gmail tools for agents to use.
    """
    # Validate Gmail access for the agent
    if not gmail_token_manager.validate_gmail_access(agent_id, "initialize"):
        audit_logger.log_security_event(
            "gmail_access_denied",
            agent_id,
            "warning",
            {"reason": "access_validation_failed"}
        )
        raise ValueError(f"Gmail access denied for agent {agent_id}")

    # Check if we're using placeholder credentials for testing
    credentials = gmail_token_manager.get_gmail_credentials(agent_id)
    # Only check the essential credential fields we set as placeholders
    essential_fields = ['client_id', 'client_secret', 'access_token', 'refresh_token']
    is_placeholder = credentials and all(
        str(credentials.get(field, '')) == "placeholder"
        for field in essential_fields
    )

    if is_placeholder:
        # Return mock tools for testing with placeholder credentials
        audit_logger.log_agent_action(
            agent_type="email_tools",
            action="gmail_tools_mock_initialized",
            agent_id=agent_id,
            details={"mode": "placeholder_testing", "tool_count": 5},
            success=True
        )
        return create_mock_gmail_tools(agent_id)

    # Initialize the Gmail toolkit with secure authentication
    try:
        toolkit = GmailToolkit()
        gmail_tools = toolkit.get_tools()

        # Wrap tools with audit logging
        audited_tools = []
        for tool in gmail_tools:
            audited_tool = GmailAuditWrapper(tool, agent_id)
            audited_tools.append(audited_tool)

        audit_logger.log_agent_action(
            agent_type="email_tools",
            action="gmail_tools_initialized",
            agent_id=agent_id,
            details={"tool_count": len(audited_tools)},
            success=True
        )

        return audited_tools

    except Exception as e:
        audit_logger.log_agent_action(
            agent_type="email_tools",
            action="gmail_tools_initialization_failed",
            agent_id=agent_id,
            error_message=str(e),
            success=False
        )
        raise


def create_mock_gmail_tools(agent_id: str) -> list[Any]:
    """
    Create mock Gmail tools for testing with placeholder credentials.

    Args:
        agent_id: Agent identifier for audit logging

    Returns:
        List of mock Gmail tools
    """
    return [
        MockGmailTool("GmailCreateDraft", agent_id),
        MockGmailTool("GmailSendMessage", agent_id),
        MockGmailTool("GmailSearch", agent_id),
        MockGmailTool("GmailGetMessage", agent_id),
        MockGmailTool("GmailGetThread", agent_id),
    ]


class MockGmailTool:
    """
    Mock Gmail tool for testing with placeholder credentials.

    This tool simulates Gmail operations without actually connecting to Gmail.
    """

    def __init__(self, name: str, agent_id: str):
        self.name = name
        self.agent_id = agent_id
        self.description = f"Mock {name} tool for testing"
        self.args_schema = None
        # Required attributes for LangChain tool compatibility
        self.is_single_input = True
        self.handle_tool_error = False
        self.return_direct = False
        # Additional attributes needed by structured chat agent
        self.args = ""  # Empty string for mock args

    def run(self, **kwargs) -> str:
        """Run the mock tool."""
        return f"[MOCK] {self.name} executed successfully with args: {kwargs}"

    async def arun(self, **kwargs) -> str:
        """Async version of run."""
        return await self.run(**kwargs)


class GmailAuditWrapper:
    """
    Wrapper for Gmail tools that adds comprehensive audit logging.

    This ensures all Gmail operations are logged for compliance and debugging.
    """

    def __init__(self, tool: Any, agent_id: str):
        """
        Initialize the audit wrapper.

        Args:
            tool: Gmail tool to wrap
            agent_id: Agent identifier for audit logging
        """
        self.tool = tool
        self.agent_id = agent_id
        self.audit_logger = audit_logger

        # Copy tool attributes
        self.name = tool.name
        self.description = tool.description
        self.args_schema = getattr(tool, 'args_schema', None)

    def run(self, **kwargs) -> Any:
        """
        Run the tool with audit logging.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        operation = self._get_operation_type()

        # Log operation start
        audit_id = self.audit_logger.log_email_operation(
            operation=operation,
            agent_id=self.agent_id,
            email_details=self._extract_email_metadata(kwargs),
            success=True  # Will be updated if operation fails
        )

        try:
            # Execute the tool
            result = self.tool.run(kwargs)

            # Log successful operation
            self.audit_logger.log_email_operation(
                operation=f"{operation}_completed",
                agent_id=self.agent_id,
                email_details=self._extract_result_metadata(result),
                success=True
            )

            return result

        except Exception as e:
            # Log failed operation
            self.audit_logger.log_email_operation(
                operation=f"{operation}_failed",
                agent_id=self.agent_id,
                email_details=self._extract_email_metadata(kwargs),
                success=False,
                error_message=str(e)
            )
            raise

    def _get_operation_type(self) -> str:
        """Get the operation type from tool name."""
        tool_name = self.name.lower()
        if "send" in tool_name:
            return "send"
        elif "create_draft" in tool_name or "draft" in tool_name:
            return "create_draft"
        elif "search" in tool_name:
            return "search"
        elif "get_message" in tool_name:
            return "get_message"
        elif "get_thread" in tool_name:
            return "get_thread"
        else:
            return "unknown"

    def _extract_email_metadata(self, kwargs: dict) -> dict:
        """
        Extract email metadata from tool arguments.

        Args:
            kwargs: Tool arguments

        Returns:
            Sanitized metadata for audit logging
        """
        metadata = {}

        # Safe fields to extract
        safe_fields = ["to", "subject", "query", "message_id", "thread_id"]

        for field in safe_fields:
            if field in kwargs:
                value = kwargs[field]
                if isinstance(value, str) and len(value) > 100:
                    metadata[field] = value[:100] + "..."
                else:
                    metadata[field] = value

        return metadata

    def _extract_result_metadata(self, result: Any) -> dict:
        """
        Extract metadata from tool result.

        Args:
            result: Tool execution result

        Returns:
            Metadata for audit logging
        """
        if isinstance(result, dict):
            return {
                "has_result": True,
                "result_keys": list(result.keys()) if result else [],
            }
        elif isinstance(result, str):
            return {
                "has_result": True,
                "result_type": "string",
                "result_length": len(result),
            }
        else:
            return {
                "has_result": True,
                "result_type": str(type(result).__name__),
            }

    async def arun(self, **kwargs) -> Any:
        """
        Async version of run method.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        # For now, delegate to sync run - could be enhanced for true async
        return self.run(**kwargs)
