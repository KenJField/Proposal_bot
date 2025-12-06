"""Celery task definitions for async execution."""

import asyncio
from typing import Any, Dict, Optional

from ..core.celery_app import celery_app
from ..core.agent import agent_registry, AgentContext
from ..database.connection import get_db


@celery_app.task(bind=True, max_retries=3)
def process_rfp(self, project_id: int) -> Dict[str, Any]:
    """Process a new RFP through the agent workflow."""
    async def _process_async():
        # Proper async database session management
        from ..database.connection import async_session_factory

        async with async_session_factory() as db_session:
            # Get orchestrator and process
            orchestrator = agent_registry.get_agent("orchestrator")

            context = AgentContext(
                project_id=project_id,
                db_session=db_session
            )

            return await orchestrator.execute(context)

    try:
        # Use asyncio.run for proper async execution
        return asyncio.run(_process_async())
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)


@celery_app.task(bind=True, max_retries=5)
def send_email(self, email_data: Dict[str, Any], project_id: Optional[int] = None) -> Dict[str, Any]:
    """Send an email asynchronously."""
    try:
        db_session = next(get_db())

        email_agent = agent_registry.get_agent("email")

        context = AgentContext(
            project_id=project_id or 0,
            db_session=db_session,
            data={"action": "send_email", "email": email_data}
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(email_agent.execute(context))
            return result
        finally:
            loop.close()

    except Exception as exc:
        # Email failures are critical, retry more aggressively
        raise self.retry(countdown=30 * (2 ** self.request.retries), exc=exc)


@celery_app.task(bind=True, max_retries=3)
def check_inbox(self) -> Dict[str, Any]:
    """Check email inbox for new messages."""
    try:
        db_session = next(get_db())

        email_agent = agent_registry.get_agent("email")

        context = AgentContext(
            project_id=0,  # Not project-specific
            db_session=db_session,
            data={"action": "check_inbox"}
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(email_agent.execute(context))
            return result
        finally:
            loop.close()

    except Exception as exc:
        raise self.retry(countdown=60, exc=exc)


@celery_app.task(bind=True, max_retries=3)
def validate_resource(self, validation_data: Dict[str, Any], project_id: int) -> Dict[str, Any]:
    """Validate a resource capability asynchronously."""
    try:
        db_session = next(get_db())

        planning_agent = agent_registry.get_agent("planning")

        context = AgentContext(
            project_id=project_id,
            db_session=db_session,
            data={"action": "validate_resource", "validation": validation_data}
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(planning_agent.execute(context))
            return result
        finally:
            loop.close()

    except Exception as exc:
        raise self.retry(countdown=120, exc=exc)


@celery_app.task(bind=True, max_retries=2)
def update_knowledge_base(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update knowledge base with new information."""
    try:
        db_session = next(get_db())

        knowledge_agent = agent_registry.get_agent("knowledge")

        context = AgentContext(
            project_id=0,  # Not project-specific
            db_session=db_session,
            data={"action": "process_validation_results", **update_data}
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(knowledge_agent.execute(context))
            return result
        finally:
            loop.close()

    except Exception as exc:
        raise self.retry(countdown=300, exc=exc)


@celery_app.task(bind=True, max_retries=2)
def generate_presentation(self, project_id: int, proposal_outline: Dict[str, Any]) -> Dict[str, Any]:
    """Generate PowerPoint presentation asynchronously."""
    try:
        db_session = next(get_db())

        powerpoint_agent = agent_registry.get_agent("powerpoint")

        context = AgentContext(
            project_id=project_id,
            db_session=db_session,
            data={
                "action": "generate_presentation",
                "proposal_outline": proposal_outline
            }
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(powerpoint_agent.execute(context))
            return result
        finally:
            loop.close()

    except Exception as exc:
        raise self.retry(countdown=600, exc=exc)  # 10 minutes for presentation generation


@celery_app.task(bind=True)
def process_work_queue(self) -> Dict[str, Any]:
    """Process pending work from the priority queue."""
    try:
        from ..core.redis_client import redis_client

        # Get highest priority work item
        work_item = redis_client.zpopmax("work_queue")

        if not work_item:
            return {"status": "no_work"}

        work_data = work_item[0]
        # Parse work data and execute appropriate task

        # This would route to the appropriate agent based on work type
        return {"status": "processed", "work_item": work_data.decode() if isinstance(work_data, bytes) else work_data}

    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Work queue processing failed: {exc}")
        return {"status": "error", "error": str(exc)}


@celery_app.task(bind=True)
def cleanup_expired_locks(self) -> Dict[str, Any]:
    """Clean up expired project locks."""
    try:
        from ..core.redis_client import redis_client
        import time

        # Find all lock keys
        lock_keys = redis_client.keys("lock:project:*")

        cleaned = 0
        for key in lock_keys:
            # Check if lock is expired (no TTL means it's not expired)
            ttl = redis_client.ttl(key)
            if ttl == -1:  # Key exists but no TTL
                # Check if the lock is older than max allowed
                lock_data = redis_client.get(key)
                if lock_data:
                    # In production, would check timestamp in lock data
                    # For now, assume locks without TTL are active
                    pass
            elif ttl == -2:  # Key doesn't exist
                continue
            else:
                # TTL exists, let Redis handle expiration
                pass

        return {"status": "cleaned", "locks_cleaned": cleaned}

    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Lock cleanup failed: {exc}")
        return {"status": "error", "error": str(exc)}


@celery_app.task(bind=True)
def update_resource_availability(self) -> Dict[str, Any]:
    """Update resource availability information daily."""
    try:
        db_session = next(get_db())

        # This would typically check calendars, update availability, etc.
        # For now, just log that it ran

        from ..core.logging import logger
        logger.info("Daily resource availability update completed")

        return {"status": "updated"}

    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Resource availability update failed: {exc}")
        return {"status": "error", "error": str(exc)}


@celery_app.task(bind=True)
def generate_daily_metrics(self) -> Dict[str, Any]:
    """Generate daily system metrics."""
    try:
        db_session = next(get_db())

        # Generate metrics about projects, agents, performance, etc.
        # This would create reports, update dashboards, etc.

        from ..core.logging import logger
        logger.info("Daily metrics generated")

        return {"status": "generated"}

    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Metrics generation failed: {exc}")
        return {"status": "error", "error": str(exc)}


# Chain tasks for complex workflows
@celery_app.task
def process_rfp_chain(project_id: int) -> None:
    """Chain of tasks to process an RFP end-to-end."""
    (
        process_rfp.s(project_id) |
        update_knowledge_base.s() |
        generate_presentation.s(project_id, {})  # Would need to pass proposal data
    ).apply_async()


# Helper functions for task management
def queue_rfp_processing(project_id: int, priority: str = "normal") -> None:
    """Add RFP processing to the work queue."""
    from ..core.redis_client import redis_client

    priority_scores = {"high": 100, "normal": 50, "low": 10}
    score = priority_scores.get(priority, 50)

    redis_client.zadd("work_queue", {f"rfp:{project_id}": score})


def schedule_email(email_data: Dict[str, Any], delay_seconds: int = 0) -> None:
    """Schedule an email to be sent."""
    if delay_seconds > 0:
        send_email.apply_async(args=[email_data], countdown=delay_seconds)
    else:
        send_email.delay(email_data)


def schedule_validation(validation_data: Dict[str, Any], project_id: int, delay_minutes: int = 0) -> None:
    """Schedule a validation task."""
    delay_seconds = delay_minutes * 60
    if delay_seconds > 0:
        validate_resource.apply_async(args=[validation_data, project_id], countdown=delay_seconds)
    else:
        validate_resource.delay(validation_data, project_id)
