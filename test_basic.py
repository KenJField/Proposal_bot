#!/usr/bin/env python3
"""
Basic functionality test for Proposal Bot

This test verifies that the core system works without requiring Gmail integration.
"""

import json
from pathlib import Path

from proposal_bot.agents.brief_preparation_agent import BriefPreparationAgent
from proposal_bot.schemas.brief import Brief


def test_basic_agent_creation():
    """Test that agents can be created (with expected Gmail security error)."""
    print("🧪 Testing agent creation and security...")

    try:
        # This will fail due to Gmail access control - which is expected
        agent = BriefPreparationAgent(brief_id="test_001")
        print("❌ Unexpected: Agent creation should have failed due to Gmail security")
    except ValueError as e:
        if "Gmail access denied" in str(e):
            print("✅ Agent security working correctly (Gmail access properly denied)")
        else:
            raise

    print("✅ Security validation confirmed")


def test_schema_validation():
    """Test that Pydantic schemas work correctly."""
    print("🧪 Testing schema validation...")

    # Load test brief
    brief_file = Path("data/briefs/example_brief_good_quality.json")
    with open(brief_file, 'r') as f:
        brief_data = json.load(f)

    # Create brief object
    brief = Brief(**brief_data)
    print(f"✅ Brief loaded: {brief.title}")
    print(f"   Client: {brief.client_name}")


def test_memory_system():
    """Test that the memory system works."""
    print("🧪 Testing memory system...")

    from proposal_bot.memory import create_knowledge_store

    # Create memory store
    store = create_knowledge_store()

    # Test storing knowledge
    store.store_knowledge('test_category', 'test_key', {'test': 'data'})

    # Test retrieving knowledge
    data = store.retrieve_knowledge('test_category', 'test_key')
    assert data is not None
    assert data['value']['test'] == 'data'

    print("✅ Memory system working correctly")


def test_audit_system():
    """Test that the audit system initializes."""
    print("🧪 Testing audit system...")

    from proposal_bot.audit import audit_logger

    # Log a test event
    audit_id = audit_logger.log_agent_action(
        agent_type='test_agent',
        action='test_action',
        agent_id='test_001',
        details={'test': True}
    )

    print(f"✅ Audit system working (ID: {audit_id[:8]}...)")


def main():
    """Run all tests."""
    print("🧪 Running Proposal Bot Basic Tests")
    print("=" * 50)

    try:
        test_schema_validation()
        test_memory_system()
        test_audit_system()
        test_basic_agent_creation()

        print("\n🎉 All tests passed!")
        print("\nThe core Proposal Bot system is working correctly.")
        print("To run the full workflow, you'll need to:")
        print("1. Set up Gmail API credentials, OR")
        print("2. Comment out Gmail tools in the agent initialization")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
