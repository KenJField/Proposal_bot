"""File system tools for Deep Agents."""

from pathlib import Path
from typing import Any

from langchain.tools import tool


def create_file_tools(workspace_dir: str = ".agent_workspace") -> list[Any]:
    """
    Create file system tools for agents.

    Args:
        workspace_dir: Directory for agent workspace files

    Returns:
        List of file system tools
    """
    workspace_path = Path(workspace_dir)
    workspace_path.mkdir(exist_ok=True)

    @tool
    def ls(path: str = ".") -> list[str]:
        """
        List files and directories in the specified path.

        Args:
            path: Path to list (relative to workspace). Defaults to current directory.

        Returns:
            List of file and directory names
        """
        full_path = workspace_path / path
        if not full_path.exists():
            return [f"Error: Path does not exist: {path}"]

        if not full_path.is_dir():
            return [f"Error: Not a directory: {path}"]

        items = []
        for item in full_path.iterdir():
            if item.is_dir():
                items.append(f"{item.name}/")
            else:
                items.append(item.name)

        return sorted(items)

    @tool
    def read_file(file_path: str) -> str:
        """
        Read the contents of a file.

        Args:
            file_path: Path to the file (relative to workspace)

        Returns:
            File contents as string
        """
        full_path = workspace_path / file_path
        if not full_path.exists():
            return f"Error: File does not exist: {file_path}"

        if not full_path.is_file():
            return f"Error: Not a file: {file_path}"

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @tool
    def write_file(file_path: str, content: str) -> str:
        """
        Write content to a file (creates or overwrites).

        Args:
            file_path: Path to the file (relative to workspace)
            content: Content to write

        Returns:
            Confirmation message
        """
        full_path = workspace_path / file_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    @tool
    def edit_file(edit_data: str) -> str:
        """
        Edit a file by replacing old_text with new_text.

        Args:
            edit_data: JSON string containing:
                - file_path: Path to the file (relative to workspace)
                - old_text: Text to find and replace
                - new_text: Replacement text

        Returns:
            Confirmation message
        """
        # Parse the JSON string input
        try:
            if isinstance(edit_data, str):
                edit_data = edit_data.strip()
                edit_data = json.loads(edit_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {edit_data[:200]}..."

        file_path = edit_data.get("file_path")
        old_text = edit_data.get("old_text")
        new_text = edit_data.get("new_text")

        if not file_path or old_text is None or new_text is None:
            return "Error: file_path, old_text, and new_text are required"

        full_path = workspace_path / file_path

        if not full_path.exists():
            return f"Error: File does not exist: {file_path}"

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_text not in content:
                return f"Error: Text not found in file: {old_text[:50]}..."

            new_content = content.replace(old_text, new_text)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"Successfully edited {file_path}"
        except Exception as e:
            return f"Error editing file: {str(e)}"

    @tool
    def append_file(file_path: str, content: str) -> str:
        """
        Append content to a file (creates if doesn't exist).

        Args:
            file_path: Path to the file (relative to workspace)
            content: Content to append

        Returns:
            Confirmation message
        """
        full_path = workspace_path / file_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully appended {len(content)} characters to {file_path}"
        except Exception as e:
            return f"Error appending to file: {str(e)}"

    return [
        ls,
        read_file,
        write_file,
        edit_file,
        append_file,
    ]
