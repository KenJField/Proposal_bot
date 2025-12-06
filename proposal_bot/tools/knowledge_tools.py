"""Knowledge base tools for memory and learning."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langchain.tools import tool


def create_knowledge_tools(workspace_dir: str = ".agent_workspace") -> list[Any]:
    """
    Create knowledge base tools for memory and learning.

    Args:
        workspace_dir: Directory for agent workspace files

    Returns:
        List of knowledge tools
    """
    workspace_path = Path(workspace_dir)
    knowledge_path = workspace_path / "knowledge"
    knowledge_path.mkdir(parents=True, exist_ok=True)

    @tool
    def store_knowledge(
        category: str,
        key: str,
        value: Any,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Store knowledge for future use.

        Args:
            category: Category of knowledge (e.g., "vendor_pricing", "staff_skills", "design_patterns")
            key: Unique identifier for this knowledge item
            value: The knowledge to store (will be JSON serialized)
            metadata: Optional metadata about this knowledge

        Returns:
            Confirmation message
        """
        category_file = knowledge_path / f"{category}.json"

        # Load existing knowledge for this category
        if category_file.exists():
            with open(category_file, "r") as f:
                knowledge_data = json.load(f)
        else:
            knowledge_data = {}

        # Store the knowledge with timestamp
        knowledge_data[key] = {
            "value": value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Save back to file
        with open(category_file, "w") as f:
            json.dump(knowledge_data, f, indent=2)

        return f"Stored knowledge: {category}/{key}"

    @tool
    def retrieve_knowledge(category: str, key: Optional[str] = None) -> Any:
        """
        Retrieve stored knowledge.

        Args:
            category: Category of knowledge
            key: Optional specific key to retrieve. If not provided, returns all knowledge in category.

        Returns:
            The requested knowledge or error message
        """
        category_file = knowledge_path / f"{category}.json"

        if not category_file.exists():
            return f"No knowledge found for category: {category}"

        with open(category_file, "r") as f:
            knowledge_data = json.load(f)

        if key is None:
            return knowledge_data

        if key not in knowledge_data:
            return f"Knowledge not found: {category}/{key}"

        return knowledge_data[key]

    @tool
    def update_knowledge(
        category: str,
        key: str,
        value: Any,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Update existing knowledge.

        Args:
            category: Category of knowledge
            key: Key to update
            value: New value
            metadata: Optional new metadata (merges with existing)

        Returns:
            Confirmation message
        """
        category_file = knowledge_path / f"{category}.json"

        if not category_file.exists():
            return f"Category not found: {category}"

        with open(category_file, "r") as f:
            knowledge_data = json.load(f)

        if key not in knowledge_data:
            return f"Knowledge not found: {category}/{key}"

        # Preserve creation timestamp, update the rest
        old_created_at = knowledge_data[key].get("created_at")

        knowledge_data[key] = {
            "value": value,
            "metadata": {**knowledge_data[key].get("metadata", {}), **(metadata or {})},
            "created_at": old_created_at,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with open(category_file, "w") as f:
            json.dump(knowledge_data, f, indent=2)

        return f"Updated knowledge: {category}/{key}"

    @tool
    def search_knowledge(category: str, search_term: str) -> list[dict[str, Any]]:
        """
        Search for knowledge containing a search term.

        Args:
            category: Category to search in
            search_term: Term to search for (case-insensitive)

        Returns:
            List of matching knowledge items
        """
        category_file = knowledge_path / f"{category}.json"

        if not category_file.exists():
            return []

        with open(category_file, "r") as f:
            knowledge_data = json.load(f)

        results = []
        search_lower = search_term.lower()

        for key, item in knowledge_data.items():
            # Search in key and value
            item_str = json.dumps(item).lower()
            if search_lower in key.lower() or search_lower in item_str:
                results.append({"key": key, **item})

        return results

    @tool
    def list_knowledge_categories() -> list[str]:
        """
        List all knowledge categories.

        Returns:
            List of category names
        """
        categories = []
        for file in knowledge_path.glob("*.json"):
            categories.append(file.stem)

        return sorted(categories)

    @tool
    def log_validation_response(
        resource_id: str,
        resource_type: str,
        confirmed_rate: Optional[float],
        confirmed_availability: bool,
        notes: str,
    ) -> str:
        """
        Log a validation response for future learning.

        This helps the system learn about resource pricing and availability over time.

        Args:
            resource_id: Resource identifier
            resource_type: Type of resource (staff/vendor)
            confirmed_rate: Confirmed rate/price
            confirmed_availability: Whether resource was available
            notes: Additional notes from the validation

        Returns:
            Confirmation message
        """
        validation_log_file = knowledge_path / "validation_history.json"

        if validation_log_file.exists():
            with open(validation_log_file, "r") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(
            {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "confirmed_rate": confirmed_rate,
                "confirmed_availability": confirmed_availability,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        with open(validation_log_file, "w") as f:
            json.dump(logs, f, indent=2)

        return f"Logged validation response for {resource_id}"

    @tool
    def log_successful_proposal_pattern(
        project_type: str,
        methodology: str,
        team_structure: dict[str, Any],
        pricing_approach: str,
        client_feedback: Optional[str] = None,
    ) -> str:
        """
        Log a successful proposal pattern for future reference.

        Args:
            project_type: Type of project
            methodology: Research methodology used
            team_structure: Structure of the project team
            pricing_approach: Pricing approach that was successful
            client_feedback: Optional client feedback

        Returns:
            Confirmation message
        """
        patterns_file = knowledge_path / "successful_patterns.json"

        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                patterns = json.load(f)
        else:
            patterns = []

        patterns.append(
            {
                "project_type": project_type,
                "methodology": methodology,
                "team_structure": team_structure,
                "pricing_approach": pricing_approach,
                "client_feedback": client_feedback,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        with open(patterns_file, "w") as f:
            json.dump(patterns, f, indent=2)

        return f"Logged successful proposal pattern for {project_type}"

    return [
        store_knowledge,
        retrieve_knowledge,
        update_knowledge,
        search_knowledge,
        list_knowledge_categories,
        log_validation_response,
        log_successful_proposal_pattern,
    ]
