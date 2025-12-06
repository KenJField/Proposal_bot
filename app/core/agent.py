"""Base agent framework and agent management."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .llm import LLMManager, Provider
from .tools import BaseTool, ToolResult

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BaseAgent')


class AgentContext:
    """Context passed to agents during execution."""

    def __init__(
        self,
        project_id: int,
        task_id: Optional[int] = None,
        db_session: Optional[AsyncSession] = None,
        **kwargs
    ):
        self.project_id = project_id
        self.task_id = task_id
        self.db_session = db_session
        self.data = kwargs


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    name: str
    description: str

    # Default LLM configuration
    default_provider: Provider = Provider.GEMINI
    default_model: str = "gemini-1.5-flash"
    default_temperature: float = 0.7

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm_manager = llm_manager or LLMManager()
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with this agent."""
        self.tools[tool.name] = tool

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for LLM consumption."""
        return [tool.to_dict() for tool in self.tools.values()]

    @abstractmethod
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the agent's main logic."""
        pass

    async def generate_text(
        self,
        prompt: str,
        provider: Optional[Provider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text using LLM."""
        provider = provider or self.default_provider
        model = model or self.default_model
        temperature = temperature or self.default_temperature

        response = await self.llm_manager.generate(
            prompt=prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            **kwargs
        )

        return response.content

    async def call_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Call a registered tool."""
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found"
            )

        try:
            result = await self.tools[tool_name].execute(**kwargs)
            return result
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )

    def log_execution_start(self, context: AgentContext) -> None:
        """Log agent execution start."""
        self.logger.info(
            f"Starting execution of {self.name} for project {context.project_id}"
        )

    def log_execution_end(self, context: AgentContext, result: Dict[str, Any]) -> None:
        """Log agent execution end."""
        self.logger.info(
            f"Completed execution of {self.name} for project {context.project_id}"
        )


class OrchestratorAgent(BaseAgent):
    """Special agent that coordinates other agents."""

    name = "orchestrator"
    description = "Central coordinator that manages workflow state and delegates tasks"
    default_provider = Provider.CLAUDE
    default_model = "claude-3-sonnet-20240229"

    # Deterministic state transitions (no LLM calls needed)
    STATE_TRANSITIONS = {
        "received": {"next": "analyzing", "agent": "brief_review", "action": "analyze_rfp"},
        "analyzing": {"next": "requirements_ready", "agent": "brief_review", "action": "complete_analysis"},
        "requirements_ready": {"next": "validating", "agent": "planning", "action": "start_planning"},
        "validating": {"next": "planning", "agent": "planning", "action": "complete_validations"},
        "planning": {"next": "draft_ready", "agent": "planning", "action": "create_plan"},
        "draft_ready": {"next": "review_ready", "agent": "gtm", "action": "generate_proposal"},
        "review_ready": {"next": "approved", "agent": "gtm", "action": "await_approval"},
        "approved": {"next": "generating", "agent": "powerpoint", "action": "generate_presentation"},
        "generating": {"next": "final_ready", "agent": "powerpoint", "action": "finalize_presentation"},
        "final_ready": {"next": "sent", "agent": "email", "action": "deliver_proposal"},
    }

    def __init__(self, agent_registry: 'AgentRegistry', redis_client=None, **kwargs):
        super().__init__(**kwargs)
        self.agent_registry = agent_registry
        self.redis = redis_client

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Coordinate workflow execution."""
        self.log_execution_start(context)

        try:
            # Get current project state
            project_state = await self._get_project_state(context.project_id, context.db_session)

            # Check for timeouts
            if await self._check_timeouts(project_state):
                await self._handle_timeout(context.project_id, project_state, context.db_session)
                return {"status": "timeout_handled"}

            # Determine next action
            next_action = await self._decide_next_action(project_state)

            # Execute next action
            result = await self._execute_action(next_action, context)

            # Update project state
            await self._update_project_state(context.project_id, result, context.db_session)

            self.log_execution_end(context, result)
            return result

        except Exception as e:
            self.logger.error(f"Orchestrator execution failed: {str(e)}", exc_info=True)
            await self._handle_error(context.project_id, str(e))
            return {"status": "error", "error": str(e)}

    async def _get_project_state(self, project_id: int, db_session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Get current project state from database."""
        if not db_session:
            raise ValueError("Database session required for orchestrator")

        from ..models import Project, ProjectTask

        # Get project
        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get active tasks
        result = await db_session.execute(
            select(ProjectTask).where(
                ProjectTask.project_id == project_id,
                ProjectTask.status.in_(["pending", "in_progress"])
            )
        )
        active_tasks = result.scalars().all()

        return {
            "project": project,
            "active_tasks": active_tasks,
            "status": project.status,
            "requirements": project.requirements,
            "plan": project.plan,
            "timeout_at": project.timeout_at,
        }

    async def _check_timeouts(self, project_state: Dict[str, Any]) -> bool:
        """Check if project has timed out."""
        timeout_at = project_state.get("timeout_at")
        if not timeout_at:
            return False

        from datetime import datetime
        return datetime.utcnow() > timeout_at

    async def _handle_timeout(self, project_id: int, project_state: Dict[str, Any], db_session: AsyncSession) -> None:
        """Handle project timeout."""
        # Transition to timeout state
        await self._transition_state(project_id, "timeout", "Project timed out", db_session)

        # Send escalation notification
        # TODO: Implement escalation notification

    async def _decide_next_action(self, project_state: Dict[str, Any]) -> Dict[str, Any]:
        """Decide what action to take next based on current state."""
        status = project_state["status"]

        # Use LLM to make complex decisions
        prompt = self._build_decision_prompt(project_state)

        try:
            decision_text = await self.generate_text(
                prompt,
                provider=Provider.CLAUDE,
                temperature=0.1  # Low temperature for consistent decisions
            )

            action = self._parse_decision(decision_text)
            return action

        except Exception as e:
            self.logger.error(f"Decision making failed: {str(e)}")
            return self._fallback_decision(status)

    def _build_decision_prompt(self, project_state: Dict[str, Any]) -> str:
        """Build prompt for decision making."""
        status = project_state["status"]
        requirements = project_state.get("requirements", {})
        active_tasks = project_state.get("active_tasks", [])

        prompt = f"""You are the Orchestrator Agent for a market research proposal system.

Current Project Status: {status}
Requirements: {requirements}
Active Tasks: {len(active_tasks)} tasks running

Based on the workflow state machine and current conditions, decide the next action.

Available Actions:
- analyze_rfp: Start RFP analysis (from received)
- check_analysis_complete: Check if analysis is done (from analyzing)
- send_clarification: Send questions to client (from analyzing)
- start_validation: Begin resource validation (from requirements_ready)
- check_validations: Check validation status (from validating)
- create_plan: Generate project plan (from validating)
- send_design_questions: Ask project lead for decisions (from planning)
- prepare_proposal: Create proposal outline (from draft_ready)
- wait_for_review: Wait for human review (from review_ready)
- generate_powerpoint: Create final presentation (from approved)
- send_proposal: Deliver to client (from final_ready)
- wait: No action needed, check again later
- escalate: Human intervention required

Consider:
- Are there pending validations?
- Has analysis completed?
- Are there blocking issues?
- Is human approval needed?
- Should we proceed with partial information?

Respond with JSON: {{"action": "action_name", "agent": "agent_name", "reasoning": "brief explanation"}}
"""

        return prompt

    def _parse_decision(self, decision_text: str) -> Dict[str, Any]:
        """Parse LLM decision response."""
        import json

        try:
            # Extract JSON from response
            start = decision_text.find('{')
            end = decision_text.rfind('}') + 1
            json_str = decision_text[start:end]

            decision = json.loads(json_str)

            # Validate decision
            required_fields = ["action", "reasoning"]
            if not all(field in decision for field in required_fields):
                raise ValueError("Missing required fields in decision")

            return decision

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse decision: {decision_text}")
            return {"action": "escalate", "reasoning": f"Decision parsing failed: {str(e)}"}

    def _fallback_decision(self, status: str) -> Dict[str, Any]:
        """Fallback decision when LLM fails."""
        fallbacks = {
            "received": {"action": "analyze_rfp", "agent": "brief_review"},
            "analyzing": {"action": "check_analysis_complete", "agent": "brief_review"},
            "requirements_ready": {"action": "start_validation", "agent": "planning"},
            "validating": {"action": "check_validations", "agent": "planning"},
            "planning": {"action": "create_plan", "agent": "planning"},
            "draft_ready": {"action": "prepare_proposal", "agent": "gtm"},
            "approved": {"action": "generate_powerpoint", "agent": "powerpoint"},
            "final_ready": {"action": "send_proposal", "agent": "email"},
        }

        return fallbacks.get(status, {"action": "escalate", "reasoning": "No fallback available"})

    async def _execute_action(self, action: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Execute the decided action."""
        action_type = action.get("action")

        if action_type == "wait":
            return {"status": "waiting", "reason": action.get("reasoning", "Waiting")}

        if action_type == "escalate":
            return await self._escalate_project(context.project_id, action.get("reasoning", "Escalation required"), context.db_session)

        agent_name = action.get("agent")
        if not agent_name:
            return {"status": "error", "error": "No agent specified for action"}

        try:
            agent = self.agent_registry.get_agent(agent_name)
            result = await agent.execute(context)
            return {"status": "completed", "action": action_type, "result": result}

        except Exception as e:
            self.logger.error(f"Action execution failed: {action_type}", exc_info=True)
            return {"status": "error", "error": f"Action {action_type} failed: {str(e)}"}

    async def _update_project_state(self, project_id: int, result: Dict[str, Any], db_session: AsyncSession) -> None:
        """Update project state based on action result."""
        if result.get("status") != "completed":
            return

        action = result.get("action")
        new_status = self._determine_new_status(action, result)

        if new_status:
            await self._transition_state(project_id, new_status, f"Action completed: {action}", db_session)

    def _determine_new_status(self, action: str, result: Dict[str, Any]) -> Optional[str]:
        """Determine new status based on completed action."""
        status_map = {
            "analyze_rfp": "analyzing",
            "check_analysis_complete": "requirements_ready",
            "send_clarification": "needs_clarification",
            "start_validation": "validating",
            "check_validations": "planning",
            "create_plan": "draft_ready",
            "send_design_questions": "design_questions",
            "prepare_proposal": "review_ready",
            "generate_powerpoint": "final_ready",
            "send_proposal": "sent",
        }

        return status_map.get(action)

    async def _transition_state(self, project_id: int, new_status: str, reasoning: str, db_session: AsyncSession) -> None:
        """Transition project to new status."""
        from ..models import Project, StateTransitionLog

        # Update project status
        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            old_status = project.status
            project.status = new_status

            # Log transition
            log_entry = StateTransitionLog(
                project_id=project_id,
                from_status=old_status,
                to_status=new_status,
                transition_type="project_status",
                agent_name=self.name,
                reasoning=reasoning,
            )

            db_session.add(log_entry)
            await db_session.commit()

    async def _escalate_project(self, project_id: int, reason: str, db_session: AsyncSession) -> Dict[str, Any]:
        """Escalate project to human intervention."""
        await self._transition_state(project_id, "escalated", reason, db_session)

        # TODO: Send escalation notification

        return {"status": "escalated", "reason": reason}

    async def _handle_error(self, project_id: int, error: str) -> None:
        """Handle execution errors."""
        # Log error and potentially escalate
        self.logger.error(f"Orchestrator error for project {project_id}: {error}")

        # TODO: Implement error handling strategy


class AgentRegistry:
    """Registry for managing agent instances."""

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> BaseAgent:
        """Get an agent by name."""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not registered")
        return self.agents[name]

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())


# Global agent registry
agent_registry = AgentRegistry()
