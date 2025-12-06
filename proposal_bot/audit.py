"""
Comprehensive Audit Logging for Proposal Bot

This module implements detailed audit logging for all agent operations,
particularly email interactions, following LangSmith's observability patterns.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from langsmith import Client

from proposal_bot.config import get_settings


class AuditLogger:
    """
    Comprehensive audit logger for Proposal Bot operations.

    This provides structured logging for all agent activities, with special
    attention to email operations and human-in-the-loop interactions.
    """

    def __init__(self):
        """Initialize the audit logger."""
        self.settings = get_settings()
        self.langsmith_client = Client()

        # Enable audit logging based on environment
        self.audit_enabled = self.settings.audit_logging_enabled

    def log_agent_action(
        self,
        agent_type: str,
        action: str,
        agent_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Log an agent action for audit purposes.

        Args:
            agent_type: Type of agent performing the action
            action: Action being performed
            agent_id: Unique identifier for the agent instance
            user_id: User associated with the action (if applicable)
            details: Additional action details
            success: Whether the action was successful
            error_message: Error message if action failed

        Returns:
            Audit log ID for tracking
        """
        audit_id = str(uuid.uuid4())

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": agent_type,
            "action": action,
            "agent_id": agent_id,
            "user_id": user_id,
            "success": success,
            "error_message": error_message,
            "details": details or {},
            "environment": {
                "deployment": self.settings.deployment_environment,
                "version": self.settings.version,
            }
        }

        if self.audit_enabled:
            try:
                self.langsmith_client.log_event(
                    event_type="agent_action",
                    event_data=audit_entry
                )
            except Exception as e:
                # Fallback logging if LangSmith is unavailable
                print(f"Audit logging failed: {e}")
                self._write_local_audit_log(audit_entry)

        return audit_id

    def log_email_operation(
        self,
        operation: str,
        agent_id: str,
        email_details: Dict[str, Any],
        user_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Log email operations with enhanced security tracking.

        Args:
            operation: Email operation type (send, receive, search, etc.)
            agent_id: Agent performing the operation
            email_details: Sanitized email details (no sensitive content)
            user_id: User associated with the operation
            success: Whether the operation was successful
            error_message: Error message if operation failed

        Returns:
            Audit log ID
        """
        # Sanitize email details for audit logging
        sanitized_details = self._sanitize_email_details(email_details)

        audit_id = self.log_agent_action(
            agent_type="email_agent",
            action=f"email_{operation}",
            agent_id=agent_id,
            user_id=user_id,
            details={
                "operation": operation,
                "email_metadata": sanitized_details,
                "requires_approval": operation in ["send", "create_draft"],
            },
            success=success,
            error_message=error_message
        )

        return audit_id

    def log_human_interaction(
        self,
        interaction_type: str,
        agent_id: str,
        workflow_id: str,
        user_id: str,
        decision: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log human-in-the-loop interactions.

        Args:
            interaction_type: Type of human interaction
            agent_id: Agent involved
            workflow_id: Workflow instance ID
            user_id: User making the decision
            decision: User's decision or response
            details: Additional interaction details

        Returns:
            Audit log ID
        """
        return self.log_agent_action(
            agent_type="human_interaction",
            action=interaction_type,
            agent_id=agent_id,
            user_id=user_id,
            details={
                "workflow_id": workflow_id,
                "decision": decision,
                "interaction_details": details or {},
            },
            success=True
        )

    def log_workflow_transition(
        self,
        workflow_id: str,
        from_state: str,
        to_state: str,
        agent_id: str,
        trigger: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log workflow state transitions.

        Args:
            workflow_id: Workflow instance ID
            from_state: Previous workflow state
            to_state: New workflow state
            agent_id: Agent managing the workflow
            trigger: What triggered the transition
            details: Additional transition details

        Returns:
            Audit log ID
        """
        return self.log_agent_action(
            agent_type="workflow_manager",
            action="state_transition",
            agent_id=agent_id,
            details={
                "workflow_id": workflow_id,
                "from_state": from_state,
                "to_state": to_state,
                "trigger": trigger,
                "transition_details": details or {},
            },
            success=True
        )

    def log_security_event(
        self,
        event_type: str,
        user_id: str,
        severity: str = "info",
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log security-related events.

        Args:
            event_type: Type of security event
            user_id: User associated with the event
            severity: Event severity (info, warning, error, critical)
            details: Additional event details

        Returns:
            Audit log ID
        """
        return self.log_agent_action(
            agent_type="security",
            action=event_type,
            agent_id="security_monitor",
            user_id=user_id,
            details={
                "severity": severity,
                "security_details": details or {},
            },
            success=True
        )

    def _sanitize_email_details(self, email_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize email details for audit logging.

        Removes sensitive content while preserving metadata for compliance.

        Args:
            email_details: Raw email details

        Returns:
            Sanitized email details
        """
        sanitized = {}

        # Safe metadata fields
        safe_fields = [
            "from", "to", "cc", "bcc", "subject", "date",
            "message_id", "thread_id", "label_ids", "size"
        ]

        for field in safe_fields:
            if field in email_details:
                # Truncate long fields for audit logs
                value = email_details[field]
                if isinstance(value, str) and len(value) > 200:
                    sanitized[field] = value[:200] + "..."
                else:
                    sanitized[field] = value

        # Add content indicators without actual content
        if "body" in email_details:
            sanitized["has_body"] = bool(email_details["body"])
            sanitized["body_length"] = len(email_details.get("body", ""))

        if "attachments" in email_details:
            sanitized["attachment_count"] = len(email_details["attachments"])

        return sanitized

    def _write_local_audit_log(self, audit_entry: Dict[str, Any]):
        """
        Fallback method to write audit logs locally when LangSmith is unavailable.

        Args:
            audit_entry: Audit entry to write
        """
        try:
            audit_file = f"audit_{datetime.utcnow().date()}.log"
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry) + "\n")
        except Exception as e:
            print(f"Local audit logging failed: {e}")

    def query_audit_logs(
        self,
        agent_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Query audit logs with filtering.

        Args:
            agent_type: Filter by agent type
            user_id: Filter by user ID
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results

        Returns:
            List of matching audit entries
        """
        # In production, this would query LangSmith's audit logs
        # For now, return empty list as fallback
        return []


# Global audit logger instance
audit_logger = AuditLogger()


class AuditMiddleware:
    """
    Middleware for automatic audit logging of agent actions.

    This middleware can be added to deep agents to automatically log
    all tool usage and agent decisions.
    """

    def __init__(self, agent_type: str, agent_id: str):
        """
        Initialize audit middleware.

        Args:
            agent_type: Type of agent
            agent_id: Unique agent identifier
        """
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.audit_logger = AuditLogger()

    def log_tool_usage(self, tool_name: str, inputs: Dict[str, Any], outputs: Any, success: bool = True):
        """
        Log tool usage.

        Args:
            tool_name: Name of the tool used
            inputs: Tool inputs
            outputs: Tool outputs
            success: Whether tool execution was successful
        """
        self.audit_logger.log_agent_action(
            agent_type=self.agent_type,
            action=f"tool_{tool_name}",
            agent_id=self.agent_id,
            details={
                "inputs": self._sanitize_inputs(inputs),
                "has_outputs": outputs is not None,
                "success": success
            },
            success=success
        )

    def _sanitize_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize tool inputs for audit logging.

        Args:
            inputs: Raw tool inputs

        Returns:
            Sanitized inputs
        """
        sanitized = {}

        for key, value in inputs.items():
            if "password" in key.lower() or "token" in key.lower():
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "..."
            else:
                sanitized[key] = value

        return sanitized
