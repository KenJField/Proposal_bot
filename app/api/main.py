"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import time

from ..core.config import settings
from ..database.connection import get_db, create_tables
from ..models import Project
from ..core.agent import agent_registry, OrchestratorAgent
from ..agents import EmailAgent, BriefReviewAgent, PlanningAgent, GTMProposalAgent, KnowledgeAgent, NotionAgent, PowerPointAgent
from ..core.monitoring import get_metrics, health_checker, increment_request_count, record_request_latency
from ..core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    await create_tables()

    # Register agents
    email_agent = EmailAgent()
    agent_registry.register(email_agent)

    brief_review_agent = BriefReviewAgent()
    agent_registry.register(brief_review_agent)

    planning_agent = PlanningAgent()
    agent_registry.register(planning_agent)

    gtm_agent = GTMProposalAgent()
    agent_registry.register(gtm_agent)

    knowledge_agent = KnowledgeAgent()
    agent_registry.register(knowledge_agent)

    notion_agent = NotionAgent()
    agent_registry.register(notion_agent)

    powerpoint_agent = PowerPointAgent()
    agent_registry.register(powerpoint_agent)

    orchestrator = OrchestratorAgent(agent_registry)
    agent_registry.register(orchestrator)

    yield

    # Shutdown
    pass


app = FastAPI(
    title="Multi-Agent Market Research Proposal Generator",
    description="Intelligent system that automates market research proposal generation",
    version="1.0.0",
    lifespan=lifespan,
)

# Request monitoring middleware
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """Monitor all HTTP requests."""
    start_time = time.time()

    # Extract route information
    path = request.url.path
    method = request.method

    # Simplify path for metrics (remove IDs)
    if "/project/" in path:
        path = "/project/{project_id}"
    elif "/rfp/submit" in path:
        path = "/rfp/submit"
    elif path.startswith("/api/"):
        path = path  # Keep API paths as-is

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Record metrics
        increment_request_count(method, path, str(response.status_code))
        record_request_latency(method, path, duration)

        # Log slow requests
        if duration > 5.0:  # Log requests taking more than 5 seconds
            logger.warning(
                f"Slow request: {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "duration": duration,
                    "status_code": response.status_code
                }
            )

        return response

    except Exception as e:
        duration = time.time() - start_time

        # Record failed request
        increment_request_count(method, path, "500")
        record_request_latency(method, path, duration)

        logger.error(
            f"Request failed: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "duration": duration,
                "error": str(e)
            },
            exc_info=True
        )
        raise


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Proposal Bot API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system status."""
    health_status = await health_checker.check_health()
    return health_status


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@app.get("/status")
async def system_status():
    """System status overview."""
    try:
        from ..core.redis_client import get_redis_client

        redis_client = get_redis_client()
        work_queue_length = redis_client.zcard("work_queue") if redis_client else 0

        # Get project counts
        db_session = next(get_db())
        from sqlalchemy import select, func
        from ..models import Project

        result = await db_session.execute(
            select(Project.status, func.count(Project.id)).group_by(Project.status)
        )
        project_counts = dict(result.all())

        return {
            "status": "operational",
            "timestamp": time.time(),
            "version": "1.0.0",
            "environment": settings.environment,
            "work_queue_length": work_queue_length,
            "projects_by_status": project_counts,
            "agents_registered": len(agent_registry.list_agents())
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


@app.post("/rfp/submit")
async def submit_rfp(
    file: UploadFile = File(...),
    client_name: str = None,
    opportunity_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Submit a new RFP for processing."""
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")

        # Create project record
        project = Project(
            title=f"RFP from {client_name or 'Unknown Client'}",
            client_name=client_name or "Unknown Client",
            opportunity_id=opportunity_id,
            requirements={
                "rfp_content": content_str,
                "filename": file.filename,
                "content_type": file.content_type,
            }
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)

        # Trigger orchestrator to start processing (FIX: Actually trigger workflow)
        from ..core.tasks import process_rfp
        process_rfp.apply_async(args=[project.id], countdown=5)  # Start in 5 seconds

        return {
            "project_id": project.id,
            "status": "submitted",
            "message": "RFP submitted successfully - processing started"
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit RFP: {str(e)}")


@app.get("/project/{project_id}")
async def get_project_status(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get project status and details."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": project.id,
        "title": project.title,
        "client_name": project.client_name,
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "estimated_value": project.estimated_value,
    }


@app.get("/projects")
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all projects."""
    # TODO: Add proper pagination and filtering
    result = await db.execute(
        f"SELECT * FROM projects ORDER BY created_at DESC LIMIT {limit} OFFSET {skip}"
    )
    projects = result.fetchall()

    return [
        {
            "id": p.id,
            "title": p.title,
            "client_name": p.client_name,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in projects
    ]
