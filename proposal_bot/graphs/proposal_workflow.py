"""LangGraph workflow for proposal generation."""

from typing import Any, Dict, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from proposal_bot.agents.background_memory_agent import BackgroundMemoryAgent
from proposal_bot.agents.brief_preparation_agent import BriefPreparationAgent
from proposal_bot.agents.proposal_agent import ProposalAgent
from proposal_bot.schemas.brief import Brief, BriefStatus
from proposal_bot.schemas.project import ProjectStatus


class WorkflowState(TypedDict):
    """State for the proposal workflow."""

    # Brief information
    brief_id: str
    brief: Dict[str, Any]
    brief_status: str

    # Project information
    project_id: str
    project_status: str

    # Workflow control
    current_step: str
    messages: list[str]
    errors: list[str]

    # Agent outputs
    brief_preparation_output: Dict[str, Any]
    proposal_output: Dict[str, Any]
    memory_updates: Dict[str, Any]

    # Human-in-the-loop flags
    awaiting_clarification: bool
    awaiting_validation: bool
    awaiting_lead_approval: bool

    # Final outputs
    final_proposal: Dict[str, Any]


class ProposalWorkflow:
    """
    LangGraph workflow for orchestrating the proposal generation process.

    Workflow steps:
    1. brief_preparation: Brief Preparation Agent analyzes and validates brief
    2. check_clarification: Check if clarification is needed
    3. await_clarification: Human-in-the-loop for clarification responses
    4. proposal_generation: Proposal Agent creates project plan and proposal
    5. resource_validation: Validate resources (spawns sub-agents for email)
    6. await_validation: Human-in-the-loop for validation responses
    7. lead_validation: Project lead validates design
    8. await_lead_approval: Human-in-the-loop for lead responses
    9. finalize_proposal: Apply business logic and finalize
    10. update_memory: Background Memory Agent updates knowledge base
    11. complete: Workflow complete
    """

    def __init__(self, checkpoint_db: str = "checkpoints.db"):
        """
        Initialize the workflow.

        Args:
            checkpoint_db: Path to SQLite database for checkpoints
        """
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create the graph
        workflow = StateGraph(WorkflowState)

        # Add nodes (workflow steps)
        workflow.add_node("brief_preparation", self._brief_preparation_node)
        workflow.add_node("check_clarification", self._check_clarification_node)
        workflow.add_node("await_clarification", self._await_clarification_node)
        workflow.add_node("proposal_generation", self._proposal_generation_node)
        workflow.add_node("resource_validation", self._resource_validation_node)
        workflow.add_node("await_validation", self._await_validation_node)
        workflow.add_node("lead_validation", self._lead_validation_node)
        workflow.add_node("await_lead_approval", self._await_lead_approval_node)
        workflow.add_node("finalize_proposal", self._finalize_proposal_node)
        workflow.add_node("update_memory", self._update_memory_node)

        # Set entry point
        workflow.set_entry_point("brief_preparation")

        # Add edges (workflow transitions)
        workflow.add_edge("brief_preparation", "check_clarification")

        # Conditional edge: clarification needed or proceed
        workflow.add_conditional_edges(
            "check_clarification",
            self._route_after_clarification_check,
            {
                "clarification_needed": "await_clarification",
                "proceed": "proposal_generation",
            },
        )

        workflow.add_edge("await_clarification", "brief_preparation")
        workflow.add_edge("proposal_generation", "resource_validation")
        workflow.add_edge("resource_validation", "await_validation")
        workflow.add_edge("await_validation", "lead_validation")
        workflow.add_edge("lead_validation", "await_lead_approval")
        workflow.add_edge("await_lead_approval", "finalize_proposal")
        workflow.add_edge("finalize_proposal", "update_memory")
        workflow.add_edge("update_memory", END)

        # Compile the graph
        return workflow.compile(checkpointer=self.memory)

    def _brief_preparation_node(self, state: WorkflowState) -> WorkflowState:
        """Run the Brief Preparation Agent."""
        brief = Brief(**state["brief"])
        agent = BriefPreparationAgent(brief_id=state["brief_id"])

        result = agent.process_brief(brief, sales_rep_email="sales@example.com")

        state["brief_preparation_output"] = result
        state["current_step"] = "brief_preparation"
        state["messages"].append("Brief preparation completed")

        return state

    def _check_clarification_node(self, state: WorkflowState) -> WorkflowState:
        """Check if clarification is needed."""
        # In production, this would analyze the brief_preparation_output
        # to determine if clarification is needed
        state["awaiting_clarification"] = False  # Placeholder
        state["current_step"] = "check_clarification"

        return state

    def _route_after_clarification_check(self, state: WorkflowState) -> str:
        """Route based on clarification needs."""
        if state["awaiting_clarification"]:
            return "clarification_needed"
        return "proceed"

    def _await_clarification_node(self, state: WorkflowState) -> WorkflowState:
        """Human-in-the-loop: await clarification from sales rep."""
        state["current_step"] = "await_clarification"
        state["messages"].append("Awaiting clarification from sales representative")

        # This is a checkpoint - workflow will resume when clarification is received
        return state

    def _proposal_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Run the Proposal Agent to generate proposal."""
        brief = Brief(**state["brief"])
        agent = ProposalAgent(project_id=state["project_id"])

        result = agent.generate_proposal(brief)

        state["proposal_output"] = result
        state["project_status"] = ProjectStatus.RESOURCING.value
        state["current_step"] = "proposal_generation"
        state["messages"].append("Proposal generation completed")

        return state

    def _resource_validation_node(self, state: WorkflowState) -> WorkflowState:
        """Spawn sub-agents to validate resources via email."""
        # In production, this would:
        # 1. Extract resource assignments from proposal_output
        # 2. Spawn resource_validator sub-agents for each resource
        # 3. Send validation emails
        # 4. Track validation request IDs

        state["awaiting_validation"] = True
        state["current_step"] = "resource_validation"
        state["messages"].append("Resource validation emails sent")

        return state

    def _await_validation_node(self, state: WorkflowState) -> WorkflowState:
        """Human-in-the-loop: await validation responses."""
        state["current_step"] = "await_validation"
        state["messages"].append("Awaiting validation responses from resource managers")

        # This is a checkpoint - workflow will resume when responses are received
        return state

    def _lead_validation_node(self, state: WorkflowState) -> WorkflowState:
        """Spawn sub-agent to validate with project lead."""
        # In production, this would:
        # 1. Identify project lead from proposal
        # 2. Spawn lead_validator sub-agent
        # 3. Send validation email with design questions

        state["awaiting_lead_approval"] = True
        state["current_step"] = "lead_validation"
        state["messages"].append("Project lead validation email sent")

        return state

    def _await_lead_approval_node(self, state: WorkflowState) -> WorkflowState:
        """Human-in-the-loop: await project lead approval."""
        state["current_step"] = "await_lead_approval"
        state["messages"].append("Awaiting project lead approval")

        # This is a checkpoint
        return state

    def _finalize_proposal_node(self, state: WorkflowState) -> WorkflowState:
        """Apply business logic and finalize proposal."""
        # In production, this would:
        # 1. Apply pricing rules and markups
        # 2. Format proposal document
        # 3. Generate executive summary
        # 4. Create presentation slides

        state["project_status"] = ProjectStatus.READY.value
        state["current_step"] = "finalize_proposal"
        state["messages"].append("Proposal finalized and ready for review")

        state["final_proposal"] = {
            "project_id": state["project_id"],
            "brief_id": state["brief_id"],
            "status": "finalized",
            "document": "proposal_document.pdf",
        }

        return state

    def _update_memory_node(self, state: WorkflowState) -> WorkflowState:
        """Run Background Memory Agent to update knowledge base."""
        agent = BackgroundMemoryAgent()

        # Update knowledge based on this proposal workflow
        result = agent.monitor_project_emails(state["project_id"])

        state["memory_updates"] = result
        state["current_step"] = "complete"
        state["messages"].append("Knowledge base updated")

        return state

    def run_workflow(self, brief_data: Dict[str, Any], sales_rep_email: str) -> Dict[str, Any]:
        """
        Run the complete proposal workflow.

        Args:
            brief_data: Brief information
            sales_rep_email: Sales representative email

        Returns:
            Final workflow state
        """
        # Initialize state
        brief_id = brief_data.get("id", "brief_001")
        project_id = f"project_{brief_id}"

        initial_state: WorkflowState = {
            "brief_id": brief_id,
            "brief": brief_data,
            "brief_status": BriefStatus.RECEIVED.value,
            "project_id": project_id,
            "project_status": ProjectStatus.PLANNING.value,
            "current_step": "start",
            "messages": [],
            "errors": [],
            "brief_preparation_output": {},
            "proposal_output": {},
            "memory_updates": {},
            "awaiting_clarification": False,
            "awaiting_validation": False,
            "awaiting_lead_approval": False,
            "final_proposal": {},
        }

        # Run the workflow
        config = {"configurable": {"thread_id": project_id}}
        result = self.graph.invoke(initial_state, config=config)

        return result

    def resume_workflow(
        self, project_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resume a workflow from a checkpoint with new information.

        Args:
            project_id: Project ID to resume
            updates: State updates (e.g., clarification responses, validation responses)

        Returns:
            Updated workflow state
        """
        config = {"configurable": {"thread_id": project_id}}

        # Get current state
        current_state = self.graph.get_state(config)

        # Update state with new information
        updated_state = {**current_state.values, **updates}

        # Resume workflow
        result = self.graph.invoke(updated_state, config=config)

        return result
