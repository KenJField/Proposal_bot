"""Project workflow and task models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import BaseModel


class Project(BaseModel):
    """Overall project state machine."""

    __tablename__ = "projects"

    # Project identification
    title = Column(String(500), nullable=False)
    client_name = Column(String(255), nullable=False, index=True)
    opportunity_id = Column(String(255), index=True)

    # Workflow state
    status = Column(String(50), nullable=False, default="received", index=True)
    # Statuses: received → analyzing → validating → planning → draft_ready → sent → won/lost

    # Lock management
    lock_token = Column(String(255), index=True)
    locked_at = Column(DateTime(timezone=True))
    locked_by = Column(String(100))  # agent name

    # Timing
    timeout_at = Column(DateTime(timezone=True))

    # Project data
    requirements = Column(JSONB, nullable=False, default=dict)
    plan = Column(JSONB, nullable=False, default=dict)
    proposal_outline = Column(JSONB, nullable=False, default=dict)

    # Results
    final_proposal_url = Column(String(500))
    outcome = Column(String(50))  # won, lost, no_response

    # Metadata
    priority = Column(String(20), default="medium")  # high, medium, low
    estimated_value = Column(JSONB, nullable=False, default=dict)
    project_lead = Column(String(255))

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, title='{self.title}', status='{self.status}')>"


class ProjectTask(BaseModel):
    """Granular tasks within projects."""

    __tablename__ = "project_tasks"

    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    task_type = Column(String(100), nullable=False, index=True)

    # Task state
    status = Column(String(50), nullable=False, default="pending", index=True)
    # Statuses: pending, in_progress, completed, failed, cancelled

    # Dependencies and blocking
    depends_on = Column(JSONB, nullable=False, default=list)  # List of task IDs
    blocked_by = Column(JSONB, nullable=False, default=list)  # List of blocking reasons

    # Execution
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    scheduled_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Results and errors
    result = Column(JSONB, nullable=False, default=dict)
    error_message = Column(Text)
    stack_trace = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<ProjectTask(id={self.id}, project_id={self.project_id}, type='{self.task_type}', status='{self.status}')>"


class StateTransitionLog(BaseModel):
    """Audit trail of all state changes."""

    __tablename__ = "state_transition_logs"

    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('project_tasks.id'), nullable=True, index=True)

    # Transition details
    from_status = Column(String(100), nullable=False)
    to_status = Column(String(100), nullable=False)
    transition_type = Column(String(50), nullable=False)  # project_status, task_status

    # Context
    agent_name = Column(String(100))
    reasoning = Column(Text)
    transition_metadata = Column(JSONB, nullable=False, default=dict)

    # User actions vs automatic
    is_user_action = Column(JSONB, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<StateTransitionLog(project_id={self.project_id}, {self.from_status} → {self.to_status})>"


# Add relationship to Project
Project.tasks = relationship("ProjectTask", order_by=ProjectTask.id, back_populates="project")
