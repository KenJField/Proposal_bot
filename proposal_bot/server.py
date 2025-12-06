"""
LangSmith Agent Server for Proposal Bot

This module implements LangSmith Agent Server endpoints for deploying
deep agents on LangChain's hosted infrastructure.
"""

from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes

from proposal_bot.agents.background_memory_agent import BackgroundMemoryAgent
from proposal_bot.agents.brief_preparation_agent import BriefPreparationAgent
from proposal_bot.agents.proposal_agent import ProposalAgent
from proposal_bot.graphs.proposal_workflow import ProposalWorkflow
from proposal_bot.schemas.brief import Brief
from proposal_bot.schemas.proposal import ProposalRequest


# Create FastAPI app
app = FastAPI(
    title="Proposal Bot Agent Server",
    description="LangSmith Agent Server for automated market research proposal generation",
    version="1.0.0",
)

# Add CORS middleware for LangSmith Studio integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Brief Preparation Agent endpoint
brief_agent = BriefPreparationAgent(brief_id="server_instance")
add_routes(
    app,
    brief_agent.agent,
    path="/brief-preparation",
    config_keys=["configurable"],
)

# Proposal Agent endpoint
proposal_agent = ProposalAgent(project_id="server_instance")
add_routes(
    app,
    proposal_agent.agent,
    path="/proposal-generation",
    config_keys=["configurable"],
)

# Background Memory Agent endpoint
memory_agent = BackgroundMemoryAgent()
add_routes(
    app,
    memory_agent.agent,
    path="/background-memory",
    config_keys=["configurable"],
)


@app.post("/workflows/proposal")
async def run_proposal_workflow(request: ProposalRequest) -> Dict[str, Any]:
    """
    Run the complete proposal workflow.

    This endpoint orchestrates the full proposal generation process
    using LangGraph workflow orchestration.
    """
    try:
        # Convert request to brief
        brief_data = request.model_dump()

        # Initialize workflow
        workflow = ProposalWorkflow()

        # Run workflow
        result = workflow.run_workflow(brief_data, request.sales_rep_email)

        return {
            "status": "success",
            "workflow_result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@app.post("/workflows/resume/{project_id}")
async def resume_workflow(project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resume a paused workflow with new information.

    This endpoint handles human-in-the-loop interactions where the workflow
    has been interrupted for clarification or validation responses.
    """
    try:
        workflow = ProposalWorkflow()
        result = workflow.resume_workflow(project_id, updates)

        return {
            "status": "success",
            "workflow_result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow resume failed: {str(e)}")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for load balancer and monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "proposal_bot.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
