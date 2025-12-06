"""Planning tools for Deep Agents (write_todos)."""

import json
from pathlib import Path
from typing import Any

from langchain.tools import tool


def create_planning_tools(workspace_dir: str = ".agent_workspace") -> list[Any]:
    """
    Create planning tools for agents (write_todos pattern).

    Args:
        workspace_dir: Directory for agent workspace files

    Returns:
        List of planning tools
    """
    workspace_path = Path(workspace_dir)
    workspace_path.mkdir(exist_ok=True)

    @tool
    def write_todos(todos: list[dict[str, str]]) -> str:
        """
        Write or update the task list for the current project.

        This tool helps agents break down complex tasks into manageable steps
        and track progress. Each todo should have:
        - content: Description of the task
        - status: One of 'pending', 'in_progress', or 'completed'
        - activeForm: Present continuous form (e.g., "Planning project structure")

        Args:
            todos: List of todo items with content, status, and activeForm

        Returns:
            Confirmation message with todo count

        Example:
            write_todos([
                {
                    "content": "Analyze brief requirements",
                    "status": "completed",
                    "activeForm": "Analyzing brief requirements"
                },
                {
                    "content": "Search for qualified staff",
                    "status": "in_progress",
                    "activeForm": "Searching for qualified staff"
                },
                {
                    "content": "Send validation emails",
                    "status": "pending",
                    "activeForm": "Sending validation emails"
                }
            ])
        """
        # Validate todo structure
        for todo in todos:
            if not all(key in todo for key in ["content", "status", "activeForm"]):
                return "Error: Each todo must have 'content', 'status', and 'activeForm' fields"

            if todo["status"] not in ["pending", "in_progress", "completed"]:
                return f"Error: Invalid status '{todo['status']}'. Must be pending, in_progress, or completed"

        # Save todos to workspace
        todos_file = workspace_path / "todos.json"
        with open(todos_file, "w") as f:
            json.dump(todos, f, indent=2)

        # Count statuses
        pending = sum(1 for t in todos if t["status"] == "pending")
        in_progress = sum(1 for t in todos if t["status"] == "in_progress")
        completed = sum(1 for t in todos if t["status"] == "completed")

        return (
            f"Updated todo list: {len(todos)} total tasks "
            f"({completed} completed, {in_progress} in progress, {pending} pending)"
        )

    @tool
    def read_todos() -> list[dict[str, str]]:
        """
        Read the current todo list.

        Returns:
            List of current todo items
        """
        todos_file = workspace_path / "todos.json"

        if not todos_file.exists():
            return []

        with open(todos_file, "r") as f:
            todos = json.load(f)

        return todos

    @tool
    def mark_todo_complete(todo_content: str) -> str:
        """
        Mark a specific todo as completed.

        Args:
            todo_content: The exact content of the todo to mark as complete

        Returns:
            Confirmation message
        """
        todos = read_todos()

        if not todos:
            return "No todos found"

        found = False
        for todo in todos:
            if todo["content"] == todo_content:
                todo["status"] = "completed"
                found = True
                break

        if not found:
            return f"Todo not found: {todo_content}"

        # Save updated todos
        todos_file = workspace_path / "todos.json"
        with open(todos_file, "w") as f:
            json.dump(todos, f, indent=2)

        return f"Marked as completed: {todo_content}"

    @tool
    def mark_todo_in_progress(todo_content: str) -> str:
        """
        Mark a specific todo as in progress.

        Args:
            todo_content: The exact content of the todo to mark as in progress

        Returns:
            Confirmation message
        """
        todos = read_todos()

        if not todos:
            return "No todos found"

        found = False
        for todo in todos:
            if todo["content"] == todo_content:
                todo["status"] = "in_progress"
                found = True
                break

        if not found:
            return f"Todo not found: {todo_content}"

        # Save updated todos
        todos_file = workspace_path / "todos.json"
        with open(todos_file, "w") as f:
            json.dump(todos, f, indent=2)

        return f"Marked as in progress: {todo_content}"

    return [
        write_todos,
        read_todos,
        mark_todo_complete,
        mark_todo_in_progress,
    ]
