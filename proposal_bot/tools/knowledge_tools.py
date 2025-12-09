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
        knowledge_data: str,
    ) -> str:
        """
        Store knowledge for future use.

        Args:
            knowledge_data: Dictionary containing:
                - category: Category of knowledge (e.g., "vendor_pricing", "staff_skills", "design_patterns")
                - key: Unique identifier for this knowledge item
                - value: The knowledge to store (will be JSON serialized)
                - metadata: Optional metadata about this knowledge

        Returns:
            Confirmation message
        """
        # Parse the JSON string input - handle multi-line strings
        try:
            if isinstance(knowledge_data, str):
                # Clean up the string - remove extra whitespace and newlines
                knowledge_data = knowledge_data.strip()
                knowledge_data = json.loads(knowledge_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {knowledge_data[:200]}..."

        category = knowledge_data.get("category")
        key = knowledge_data.get("key")
        value = knowledge_data.get("value")
        metadata = knowledge_data.get("metadata", {})

        if not category or not key:
            return "Error: category and key are required"

        category_file = knowledge_path / f"{category}.json"

        # Load existing knowledge for this category
        if category_file.exists():
            with open(category_file, "r") as f:
                existing_data = json.load(f)
        else:
            existing_data = {}

        # Store the knowledge with timestamp
        existing_data[key] = {
            "value": value,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Save back to file
        with open(category_file, "w") as f:
            json.dump(existing_data, f, indent=2)

        return f"Stored knowledge: {category}/{key}"

    @tool
    def retrieve_knowledge(query_data: str) -> Any:
        """
        Retrieve stored knowledge.

        Args:
            query_data: Dictionary containing:
                - category: Category of knowledge
                - key: Optional specific key to retrieve. If not provided, returns all knowledge in category.

        Returns:
            The requested knowledge or error message
        """
        # Parse the JSON string input - handle multi-line strings
        try:
            if isinstance(query_data, str):
                # Clean up the string - remove extra whitespace and newlines
                query_data = query_data.strip()
                query_data = json.loads(query_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {query_data[:200]}..."

        category = query_data.get("category")
        key = query_data.get("key")

        if not category:
            return "Error: category is required"

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
    def update_knowledge(update_data: str) -> str:
        """
        Update existing knowledge.

        Args:
            update_data: Dictionary containing:
                - category: Category of knowledge
                - key: Key to update
                - value: New value
                - metadata: Optional new metadata (merges with existing)

        Returns:
            Confirmation message
        """
        # Parse the JSON string input - handle multi-line strings
        try:
            if isinstance(update_data, str):
                # Clean up the string - remove extra whitespace and newlines
                update_data = update_data.strip()
                update_data = json.loads(update_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {update_data[:200]}..."

        category = update_data.get("category")
        key = update_data.get("key")
        value = update_data.get("value")
        metadata = update_data.get("metadata", {})

        if not category or not key:
            return "Error: category and key are required"

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
            "metadata": {**knowledge_data[key].get("metadata", {}), **metadata},
            "created_at": old_created_at,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with open(category_file, "w") as f:
            json.dump(knowledge_data, f, indent=2)

        return f"Updated knowledge: {category}/{key}"

    @tool
    def search_knowledge(search_data: str) -> list[dict[str, Any]]:
        """
        Search for knowledge containing a search term.

        Args:
            search_data: Dictionary containing:
                - category: Category to search in
                - search_term: Term to search for (case-insensitive)

        Returns:
            List of matching knowledge items
        """
        # Parse the JSON string input - handle multi-line strings
        try:
            if isinstance(search_data, str):
                # Clean up the string - remove extra whitespace and newlines
                search_data = search_data.strip()
                search_data = json.loads(search_data)
        except json.JSONDecodeError:
            return []

        category = search_data.get("category")
        search_term = search_data.get("search_term")

        if not category or not search_term:
            return []

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
    def list_knowledge_categories(dummy_param: str = "unused") -> list[str]:
        """
        List all knowledge categories.

        Args:
            dummy_param: Dummy parameter for consistency (unused)

        Returns:
            List of category names
        """
        # Parse the JSON string input (even though we don't use it)
        try:
            if isinstance(dummy_param, str):
                dummy_param = dummy_param.strip()
                dummy_param = json.loads(dummy_param)
        except json.JSONDecodeError:
            pass  # Ignore parsing errors for dummy param

        categories = []
        for file in knowledge_path.glob("*.json"):
            categories.append(file.stem)

        return sorted(categories)

    @tool
    def log_validation_response(validation_data: str) -> str:
        """
        Log a validation response for future learning.

        This helps the system learn about resource pricing and availability over time.

        Args:
            validation_data: Dictionary containing:
                - resource_id: Resource identifier
                - resource_type: Type of resource (staff/vendor)
                - confirmed_rate: Confirmed rate/price
                - confirmed_availability: Whether resource was available
                - notes: Additional notes from the validation

        Returns:
            Confirmation message
        """
        # Parse the JSON string input - handle multi-line strings
        try:
            if isinstance(validation_data, str):
                # Clean up the string - remove extra whitespace and newlines
                validation_data = validation_data.strip()
                validation_data = json.loads(validation_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {validation_data[:200]}..."

        resource_id = validation_data.get("resource_id")
        resource_type = validation_data.get("resource_type")
        confirmed_rate = validation_data.get("confirmed_rate")
        confirmed_availability = validation_data.get("confirmed_availability")
        notes = validation_data.get("notes", "")

        if not resource_id or resource_type is None:
            return "Error: resource_id and resource_type are required"

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
    def log_successful_proposal_pattern(pattern_data: str) -> str:
        """
        Log a successful proposal pattern for future reference.

        Args:
            pattern_data: Dictionary containing:
                - project_type: Type of project
                - methodology: Research methodology used
                - team_structure: Structure of the project team
                - pricing_approach: Pricing approach that was successful
                - client_feedback: Optional client feedback

        Returns:
            Confirmation message
        """
        # Parse the JSON string input - handle multi-line strings
        try:
            if isinstance(pattern_data, str):
                # Clean up the string - remove extra whitespace and newlines
                pattern_data = pattern_data.strip()
                pattern_data = json.loads(pattern_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {pattern_data[:200]}..."

        project_type = pattern_data.get("project_type")
        methodology = pattern_data.get("methodology")
        team_structure = pattern_data.get("team_structure", {})
        pricing_approach = pattern_data.get("pricing_approach")
        client_feedback = pattern_data.get("client_feedback")

        if not project_type or not methodology or not pricing_approach:
            return "Error: project_type, methodology, and pricing_approach are required"

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
