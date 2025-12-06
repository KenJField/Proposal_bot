"""
LangChain Deep Agents Memory Management - Composite Backend Implementation

This module implements long-term memory for deep agents using LangChain's
CompositeBackend pattern, providing hybrid storage where /memories/* paths
are persisted across threads while other paths remain ephemeral.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from deepagents import CompositeBackend, StateBackend, StoreBackend


class LangSmithMemoryBackend(StoreBackend):
    """
    Persistent memory backend using LangSmith's recommended patterns.

    This backend stores knowledge in a structured format that can be
    easily queried and maintained across agent sessions.
    """

    def __init__(self, base_path: str = ".agent_memory"):
        """
        Initialize the persistent memory backend.

        Args:
            base_path: Base directory for memory storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for different memory types
        self.memories_path = self.base_path / "memories"
        self.knowledge_path = self.base_path / "knowledge"
        self.memories_path.mkdir(exist_ok=True)
        self.knowledge_path.mkdir(exist_ok=True)

    def get(self, path: str) -> Optional[str]:
        """Retrieve content from persistent storage."""
        try:
            file_path = self._resolve_path(path)
            if file_path.exists():
                return file_path.read_text()
            return None
        except Exception:
            return None

    def put(self, path: str, content: str) -> None:
        """Store content in persistent storage."""
        try:
            file_path = self._resolve_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        except Exception as e:
            # Log error but don't fail - memory operations should be resilient
            print(f"Error storing memory at {path}: {e}")

    def delete(self, path: str) -> None:
        """Delete content from persistent storage."""
        try:
            file_path = self._resolve_path(path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Error deleting memory at {path}: {e}")

    def list(self, prefix: str = "") -> list[str]:
        """List all paths with the given prefix."""
        try:
            search_path = self._resolve_path(prefix)
            if search_path.is_file():
                return [str(search_path.relative_to(self.base_path))]

            paths = []
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    paths.append(str(file_path.relative_to(self.base_path)))

            return paths
        except Exception:
            return []

    def _resolve_path(self, path: str) -> Path:
        """Resolve a memory path to a filesystem path."""
        # Remove leading slash if present
        clean_path = path.lstrip("/")

        # Route different types of content to appropriate directories
        if clean_path.startswith("memories/"):
            return self.memories_path / clean_path[9:]  # Remove "memories/" prefix
        elif clean_path.startswith("knowledge/"):
            return self.knowledge_path / clean_path[10:]  # Remove "knowledge/" prefix
        else:
            # Default to memories for backward compatibility
            return self.memories_path / clean_path


class KnowledgeStore:
    """
    High-level knowledge management interface for deep agents.

    This provides a structured way to store and retrieve different types
    of knowledge that agents learn over time.
    """

    def __init__(self, backend: StoreBackend):
        """
        Initialize the knowledge store.

        Args:
            backend: The persistent storage backend
        """
        self.backend = backend

    def store_memory(self, key: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a memory with optional metadata.

        Args:
            key: Unique identifier for the memory
            content: The memory content
            metadata: Optional metadata about the memory
        """
        memory_data = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": "2025-12-06T12:00:00Z",  # Would use datetime.utcnow() in production
        }

        path = f"memories/{key}.json"
        self.backend.put(path, json.dumps(memory_data, indent=2))

    def retrieve_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a memory by key.

        Args:
            key: The memory key

        Returns:
            The memory data or None if not found
        """
        path = f"memories/{key}.json"
        content = self.backend.get(path)

        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None

    def store_knowledge(self, category: str, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store structured knowledge in a category.

        Args:
            category: Knowledge category (e.g., "vendor_pricing", "staff_skills")
            key: Unique key within the category
            value: The knowledge value
            metadata: Optional metadata
        """
        knowledge_data = {
            "value": value,
            "metadata": metadata or {},
            "created_at": "2025-12-06T12:00:00Z",
            "updated_at": "2025-12-06T12:00:00Z",
        }

        path = f"knowledge/{category}/{key}.json"
        self.backend.put(path, json.dumps(knowledge_data, indent=2))

    def retrieve_knowledge(self, category: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve knowledge from a category.

        Args:
            category: Knowledge category
            key: The key within the category

        Returns:
            The knowledge data or None if not found
        """
        path = f"knowledge/{category}/{key}.json"
        content = self.backend.get(path)

        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None

    def search_memories(self, query: str) -> list[Dict[str, Any]]:
        """
        Search memories containing the query string.

        Args:
            query: Search query

        Returns:
            List of matching memories
        """
        results = []
        memory_paths = self.backend.list("memories/")

        for path in memory_paths:
            content = self.backend.get(path)
            if content and query.lower() in content.lower():
                try:
                    memory_data = json.loads(content)
                    memory_data["key"] = Path(path).stem
                    results.append(memory_data)
                except json.JSONDecodeError:
                    continue

        return results


def create_composite_memory_backend(memory_dir: str = ".agent_memory") -> CompositeBackend:
    """
    Create a composite backend that routes memory paths to persistent storage.

    This follows LangChain's recommended pattern for long-term memory in deep agents,
    where /memories/* and /knowledge/* paths are persisted while other paths
    remain ephemeral to the current thread.

    Args:
        memory_dir: Directory for persistent memory storage

    Returns:
        Configured CompositeBackend
    """
    # Create persistent backend for memories and knowledge
    persistent_backend = LangSmithMemoryBackend(memory_dir)

    # Create composite backend with routing rules
    composite_backend = CompositeBackend()

    # Route memory and knowledge paths to persistent storage
    composite_backend.add_route("/memories/*", persistent_backend)
    composite_backend.add_route("/knowledge/*", persistent_backend)

    # Everything else uses the default state backend (ephemeral)

    return composite_backend


def create_knowledge_store(memory_dir: str = ".agent_memory") -> KnowledgeStore:
    """
    Create a knowledge store for structured memory management.

    Args:
        memory_dir: Directory for memory storage

    Returns:
        Configured KnowledgeStore
    """
    persistent_backend = LangSmithMemoryBackend(memory_dir)
    return KnowledgeStore(persistent_backend)
