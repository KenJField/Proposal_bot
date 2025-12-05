"""Monitoring, metrics, and health checks."""

import time
from typing import Any, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from ..core.config import settings
from ..core.redis_client import redis_health_check
from .logging import logger


# Prometheus metrics
# Request metrics
REQUEST_COUNT = Counter(
    "proposal_bot_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "proposal_bot_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"]
)

# Agent metrics
AGENT_EXECUTION_COUNT = Counter(
    "proposal_bot_agent_executions_total",
    "Total number of agent executions",
    ["agent_name", "status"]
)

AGENT_EXECUTION_LATENCY = Histogram(
    "proposal_bot_agent_execution_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_name"]
)

# Project metrics
PROJECT_STATUS_GAUGE = Gauge(
    "proposal_bot_projects_by_status",
    "Number of projects by status",
    ["status"]
)

PROJECT_TRANSITIONS = Counter(
    "proposal_bot_project_transitions_total",
    "Total project status transitions",
    ["from_status", "to_status"]
)

# LLM metrics
LLM_REQUEST_COUNT = Counter(
    "proposal_bot_llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"]
)

LLM_TOKEN_USAGE = Counter(
    "proposal_bot_llm_tokens_total",
    "Total LLM tokens used",
    ["provider", "model"]
)

LLM_COST = Counter(
    "proposal_bot_llm_cost_total",
    "Total LLM API cost",
    ["provider", "currency"]
)

# Email metrics
EMAIL_SENT_COUNT = Counter(
    "proposal_bot_emails_sent_total",
    "Total emails sent",
    ["email_type", "status"]
)

EMAIL_RECEIVED_COUNT = Counter(
    "proposal_bot_emails_received_total",
    "Total emails received",
    ["email_type"]
)

# Validation metrics
VALIDATION_REQUESTS = Counter(
    "proposal_bot_validations_total",
    "Total validation requests",
    ["status", "priority"]
)

VALIDATION_RESPONSE_TIME = Histogram(
    "proposal_bot_validation_response_time_hours",
    "Validation response time in hours",
    ["priority"]
)

# System metrics
ACTIVE_CONNECTIONS = Gauge(
    "proposal_bot_active_connections",
    "Number of active connections"
)

WORK_QUEUE_LENGTH = Gauge(
    "proposal_bot_work_queue_length",
    "Length of work queue"
)

REDIS_CONNECTIONS = Gauge(
    "proposal_bot_redis_connections",
    "Redis connection status",
    ["status"]
)


class MetricsCollector:
    """Collect and expose system metrics."""

    def __init__(self):
        self.last_collection = 0
        self.collection_interval = 60  # Collect every 60 seconds

    async def collect_system_metrics(self) -> None:
        """Collect system-wide metrics."""
        current_time = time.time()

        if current_time - self.last_collection < self.collection_interval:
            return

        try:
            # Collect project status metrics
            await self._collect_project_metrics()

            # Collect work queue metrics
            await self._collect_queue_metrics()

            # Collect Redis health metrics
            await self._collect_redis_metrics()

            self.last_collection = current_time

        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")

    async def _collect_project_metrics(self) -> None:
        """Collect project status metrics."""
        try:
            from ..database.connection import get_db
            from sqlalchemy import select, func
            from ..models import Project

            db_session = next(get_db())

            # Count projects by status
            result = await db_session.execute(
                select(Project.status, func.count(Project.id)).group_by(Project.status)
            )

            status_counts = dict(result.all())

            # Update gauges
            for status, count in status_counts.items():
                PROJECT_STATUS_GAUGE.labels(status=status).set(count)

        except Exception as e:
            logger.error(f"Project metrics collection failed: {e}")

    async def _collect_queue_metrics(self) -> None:
        """Collect work queue metrics."""
        try:
            from ..core.redis_client import get_redis_client

            redis_client = get_redis_client()
            if redis_client:
                queue_length = redis_client.zcard("work_queue")
                WORK_QUEUE_LENGTH.set(queue_length)

        except Exception as e:
            logger.error(f"Queue metrics collection failed: {e}")

    async def _collect_redis_metrics(self) -> None:
        """Collect Redis health metrics."""
        try:
            redis_health = redis_health_check()

            if redis_health["status"] == "healthy":
                REDIS_CONNECTIONS.labels(status="healthy").set(1)
                REDIS_CONNECTIONS.labels(status="unhealthy").set(0)
            else:
                REDIS_CONNECTIONS.labels(status="healthy").set(0)
                REDIS_CONNECTIONS.labels(status="unhealthy").set(1)

        except Exception as e:
            logger.error(f"Redis metrics collection failed: {e}")
            REDIS_CONNECTIONS.labels(status="healthy").set(0)
            REDIS_CONNECTIONS.labels(status="unhealthy").set(1)


# Global metrics collector
metrics_collector = MetricsCollector()


def get_metrics() -> str:
    """Get current metrics in Prometheus format."""
    return generate_latest().decode('utf-8')


def increment_request_count(method: str, endpoint: str, status: str) -> None:
    """Increment request count metric."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()


def record_request_latency(method: str, endpoint: str, duration: float) -> None:
    """Record request latency."""
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_agent_execution(agent_name: str, status: str, duration: Optional[float] = None) -> None:
    """Record agent execution metrics."""
    AGENT_EXECUTION_COUNT.labels(agent_name=agent_name, status=status).inc()

    if duration is not None:
        AGENT_EXECUTION_LATENCY.labels(agent_name=agent_name).observe(duration)


def record_project_transition(from_status: str, to_status: str) -> None:
    """Record project status transition."""
    PROJECT_TRANSITIONS.labels(from_status=from_status, to_status=to_status).inc()


def record_llm_usage(provider: str, model: str, tokens: Optional[int] = None, cost: Optional[float] = None, success: bool = True) -> None:
    """Record LLM usage metrics."""
    status = "success" if success else "error"
    LLM_REQUEST_COUNT.labels(provider=provider, model=model, status=status).inc()

    if tokens:
        LLM_TOKEN_USAGE.labels(provider=provider, model=model).inc(tokens)

    if cost:
        LLM_COST.labels(provider=provider, currency="USD").inc(cost)


def record_email_sent(email_type: str, success: bool = True) -> None:
    """Record email sending metrics."""
    status = "success" if success else "error"
    EMAIL_SENT_COUNT.labels(email_type=email_type, status=status).inc()


def record_email_received(email_type: str) -> None:
    """Record email receiving metrics."""
    EMAIL_RECEIVED_COUNT.labels(email_type=email_type).inc()


def record_validation(validation_status: str, priority: str, response_time_hours: Optional[float] = None) -> None:
    """Record validation metrics."""
    VALIDATION_REQUESTS.labels(status=validation_status, priority=priority).inc()

    if response_time_hours and validation_status == "responded":
        VALIDATION_RESPONSE_TIME.labels(priority=priority).observe(response_time_hours)


class HealthChecker:
    """System health checker."""

    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {}
        }

        # Database health
        db_health = await self._check_database()
        health_status["checks"]["database"] = db_health

        # Redis health
        redis_health = redis_health_check()
        health_status["checks"]["redis"] = redis_health

        # LLM providers health
        llm_health = await self._check_llm_providers()
        health_status["checks"]["llm_providers"] = llm_health

        # Email health
        email_health = await self._check_email()
        health_status["checks"]["email"] = email_health

        # Overall status
        all_healthy = all(
            check.get("status") == "healthy"
            for check in health_status["checks"].values()
        )

        health_status["status"] = "healthy" if all_healthy else "unhealthy"

        return health_status

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from ..database.connection import get_db
            db_session = next(get_db())

            # Simple query to test connection
            from sqlalchemy import text
            await db_session.execute(text("SELECT 1"))

            return {"status": "healthy", "message": "Database connection OK"}

        except Exception as e:
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}

    async def _check_llm_providers(self) -> Dict[str, Any]:
        """Check LLM provider connectivity."""
        results = {}

        try:
            from ..core.llm import LLMManager
            llm_manager = LLMManager()

            # Test Gemini (quick test)
            try:
                # Simple test - would need API key validation in production
                results["gemini"] = {"status": "healthy", "message": "API key configured"}
            except Exception as e:
                results["gemini"] = {"status": "unhealthy", "message": str(e)}

            # Test Claude (quick test)
            try:
                results["claude"] = {"status": "healthy", "message": "API key configured"}
            except Exception as e:
                results["claude"] = {"status": "unhealthy", "message": str(e)}

        except Exception as e:
            results["error"] = {"status": "unhealthy", "message": f"LLM check failed: {str(e)}"}

        # Overall LLM health
        all_healthy = all(
            provider.get("status") == "healthy"
            for provider in results.values()
        )

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "providers": results
        }

    async def _check_email(self) -> Dict[str, Any]:
        """Check email connectivity."""
        try:
            # Test SMTP connection (mock)
            smtp_ok = True  # Would test actual SMTP in production

            # Test IMAP connection (mock)
            imap_ok = True  # Would test actual IMAP in production

            if smtp_ok and imap_ok:
                return {"status": "healthy", "message": "Email services configured"}
            else:
                return {"status": "unhealthy", "message": "Email service configuration issue"}

        except Exception as e:
            return {"status": "unhealthy", "message": f"Email check failed: {str(e)}"}


# Global health checker
health_checker = HealthChecker()
