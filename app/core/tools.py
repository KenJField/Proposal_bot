"""Tool interface and base tool implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Result from a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


T = TypeVar('T')


class BaseTool(ABC, Generic[T]):
    """Abstract base class for all tools."""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameter schema."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for LLM consumption."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters(),
        }


class DatabaseTool(BaseTool[T]):
    """Base class for database-related tools."""

    def __init__(self, db_session):
        self.db_session = db_session


class WebTool(BaseTool[T]):
    """Base class for web-related tools."""

    pass


class FileTool(BaseTool[T]):
    """Base class for file system tools."""

    pass


class EmailTool(BaseTool[T]):
    """Base class for email-related tools."""

    pass


class NotionTool(BaseTool[T]):
    """Base class for Notion-related tools."""

    pass
