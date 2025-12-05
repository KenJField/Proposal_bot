"""Structured logging configuration and utilities."""

import logging
import sys
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger
from ..core.config import settings


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add common fields
        log_record["timestamp"] = self.format_timestamp(record.created)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add environment info
        log_record["environment"] = settings.environment
        log_record["version"] = "1.0.0"

        # Add request context if available (would be set by middleware in production)
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id
        if hasattr(record, "project_id"):
            log_record["project_id"] = record.project_id


def setup_logging() -> None:
    """Configure structured logging for the application."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler for development
    if settings.environment == "development":
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    else:
        # JSON structured logging for production
        json_handler = logging.StreamHandler(sys.stdout)
        json_formatter = StructuredFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s"
        )
        json_handler.setFormatter(json_formatter)
        root_logger.addHandler(json_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # Agent-specific loggers
    agent_logger = logging.getLogger("app.agents")
    agent_logger.setLevel(logging.INFO)

    # Database loggers
    db_logger = logging.getLogger("app.database")
    db_logger.setLevel(logging.INFO)


# Global logger instance
logger = logging.getLogger(__name__)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context information."""

    def __init__(self, logger: logging.Logger, context: Optional[Dict[str, Any]] = None):
        self.context = context or {}
        super().__init__(logger, self.context)

    def process(self, msg: str, kwargs: Any) -> tuple:
        """Process log message with context."""
        # Add context to extra
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"].update(self.context)
        return msg, kwargs


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> LoggerAdapter:
    """Get a logger with optional context."""
    base_logger = logging.getLogger(name)
    return LoggerAdapter(base_logger, context)


# Agent execution logging
def log_agent_execution(
    agent_name: str,
    project_id: int,
    action: str,
    status: str,
    duration: Optional[float] = None,
    error: Optional[str] = None,
    **kwargs
) -> None:
    """Log agent execution for monitoring."""
    log_data = {
        "agent_name": agent_name,
        "project_id": project_id,
        "action": action,
        "status": status,
        "duration_seconds": duration,
        "error": error,
        **kwargs
    }

    if status == "error":
        logger.error(f"Agent execution failed: {agent_name}", extra=log_data)
    elif status == "completed":
        logger.info(f"Agent execution completed: {agent_name}", extra=log_data)
    else:
        logger.info(f"Agent execution: {agent_name} - {status}", extra=log_data)


# Workflow transition logging
def log_workflow_transition(
    project_id: int,
    from_status: str,
    to_status: str,
    agent_name: str,
    reasoning: str,
    **kwargs
) -> None:
    """Log workflow state transitions."""
    log_data = {
        "project_id": project_id,
        "from_status": from_status,
        "to_status": to_status,
        "agent_name": agent_name,
        "reasoning": reasoning,
        "transition_type": "workflow",
        **kwargs
    }

    logger.info(f"Workflow transition: {from_status} → {to_status}", extra=log_data)


# Performance monitoring
def log_performance(
    operation: str,
    duration: float,
    success: bool = True,
    **kwargs
) -> None:
    """Log performance metrics."""
    log_data = {
        "operation": operation,
        "duration_seconds": duration,
        "success": success,
        "performance_metric": True,
        **kwargs
    }

    if success:
        logger.info(f"Performance: {operation}", extra=log_data)
    else:
        logger.warning(f"Performance failure: {operation}", extra=log_data)


# Error tracking
def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
    **kwargs
) -> None:
    """Log errors with context."""
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_code": error_code,
        "traceback": True,  # Will be included by exc_info
        **(context or {}),
        **kwargs
    }

    logger.error(f"Error: {error_data['error_type']}", extra=error_data, exc_info=True)


# LLM usage tracking
def log_llm_usage(
    provider: str,
    model: str,
    tokens_used: Optional[int] = None,
    cost: Optional[float] = None,
    success: bool = True,
    **kwargs
) -> None:
    """Log LLM API usage."""
    usage_data = {
        "provider": provider,
        "model": model,
        "tokens_used": tokens_used,
        "cost_usd": cost,
        "success": success,
        "llm_usage": True,
        **kwargs
    }

    logger.info(f"LLM usage: {provider}/{model}", extra=usage_data)


# Email tracking
def log_email_event(
    event_type: str,
    email_type: str,
    recipient: str,
    success: bool = True,
    thread_id: Optional[str] = None,
    **kwargs
) -> None:
    """Log email events."""
    email_data = {
        "event_type": event_type,
        "email_type": email_type,
        "recipient": recipient,
        "success": success,
        "thread_id": thread_id,
        "email_event": True,
        **kwargs
    }

    if success:
        logger.info(f"Email {event_type}: {email_type}", extra=email_data)
    else:
        logger.warning(f"Email {event_type} failed: {email_type}", extra=email_data)


# Validation tracking
def log_validation_event(
    validation_id: int,
    resource_id: int,
    status: str,
    response_time_hours: Optional[float] = None,
    **kwargs
) -> None:
    """Log validation events."""
    validation_data = {
        "validation_id": validation_id,
        "resource_id": resource_id,
        "status": status,
        "response_time_hours": response_time_hours,
        "validation_event": True,
        **kwargs
    }

    logger.info(f"Validation {status}: ID {validation_id}", extra=validation_data)


# Initialize logging when module is imported
setup_logging()
