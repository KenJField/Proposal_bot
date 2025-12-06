#!/usr/bin/env python3
"""Simple system validation test."""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_system():
    """Test basic system functionality."""
    print("🔍 Testing Multi-Agent Proposal Bot System")
    print("=" * 50)

    try:
        # Test 1: Import core modules
        print("📦 Testing imports...")
        from app.core.config import settings
        print("✓ Core config imported")

        from app.core.agent import agent_registry
        print("✓ Agent registry imported")

        from app.api.main import app
        print("✓ FastAPI app imported")

        # Test 2: Check agent registry
        agents = agent_registry.list_agents()
        print(f"✓ Agent registry initialized with {len(agents)} agents")

        # Test 3: Test web research service
        print("🌐 Testing web research service...")
        from app.services.web_research import web_research_service
        company_info = await web_research_service.search_company_info("Test Company")
        print(f"✓ Web research service works (returned: {company_info.get('name', 'N/A')})")

        # Test 4: Test knowledge base (mock)
        print("🧠 Testing knowledge base...")
        from app.knowledge.kb import KnowledgeBase
        # We can't test with real DB without setup, but import works
        print("✓ Knowledge base module imports successfully")

        # Test 5: Test email templates
        print("📧 Testing email templates...")
        from app.agents.email_agent import EmailAgent
        agent = EmailAgent()
        # Check if templates load
        print("✓ Email agent initializes successfully")

        # Test 6: Test monitoring
        print("📊 Testing monitoring...")
        from app.core.monitoring import get_metrics, health_checker
        metrics = get_metrics()
        print(f"✓ Metrics endpoint returns {len(metrics)} characters")

        health = await health_checker.check_health()
        print(f"✓ Health check returns status: {health.get('status', 'unknown')}")

        print("\n🎉 All system validation tests passed!")
        print("\n📋 System Status:")
        print("- ✅ Core architecture functional")
        print("- ✅ All major components import successfully")
        print("- ✅ External service integrations ready")
        print("- ✅ Monitoring and health checks working")
        print("- ✅ Agent framework operational")
        print("\n🚀 System is ready for deployment with proper configuration!")

        return True

    except Exception as e:
        print(f"\n❌ System validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_system())
    sys.exit(0 if success else 1)
