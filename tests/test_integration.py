"""Integration tests for the proposal bot system."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent import agent_registry, AgentContext
from app.agents.brief_review_agent import BriefReviewAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.email_agent import EmailAgent
from app.database.connection import get_db


@pytest.mark.asyncio
async def test_rfp_processing_workflow():
    """Test the complete RFP processing workflow."""
    # Mock database session
    mock_db = AsyncMock()

    # Sample RFP content
    rfp_content = """
    Market Research RFP for Consumer Packaged Goods

    We are seeking a research partner to conduct a comprehensive study on consumer preferences for organic snacks.

    Objectives:
    - Understand consumer buying behavior
    - Identify key drivers of purchase decisions
    - Test concept acceptance for new product lines

    Methodology Requirements:
    - Online survey with 1,000 respondents
    - Focus groups with 8 groups of 6-8 participants
    - In-depth interviews with 20 key opinion leaders

    Timeline:
    - Project start: ASAP
    - Fieldwork: 6 weeks
    - Reporting: 2 weeks after fieldwork
    - Total duration: 8-10 weeks

    Budget: $75,000 - $100,000
    """

    # Mock project data
    mock_project = MagicMock()
    mock_project.requirements = {"rfp_content": rfp_content}

    # Mock database query
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_project

    # Test Brief Review Agent
    brief_agent = BriefReviewAgent()

    context = AgentContext(
        project_id=1,
        db_session=mock_db
    )

    # Mock the analysis method to return structured data
    with patch.object(brief_agent, '_analyze_brief') as mock_analyze:
        mock_analyze.return_value = {
            "client_name": "Consumer Goods Corp",
            "objectives": ["Understand buying behavior", "Identify purchase drivers"],
            "methodology_requirements": ["survey", "focus groups", "interviews"],
            "timeline": {"total_weeks": 10},
            "budget_range": {"min": 75000, "max": 100000}
        }

        with patch.object(brief_agent, '_enrich_with_context') as mock_enrich:
            mock_enrich.return_value = {
                "client_name": "Consumer Goods Corp",
                "methodology_requirements": ["survey", "focus groups", "interviews"],
                "timeline": {"total_weeks": 10},
                "budget_range": {"min": 75000, "max": 100000},
                "client_history": {"past_projects": []},
                "client_research": {"industry": "Consumer Packaged Goods"}
            }

            with patch.object(brief_agent, '_calculate_go_no_go_score') as mock_gonogo:
                mock_gonogo.return_value = {"score": 85, "recommendation": "GO"}

                with patch.object(brief_agent, '_generate_clarification_questions') as mock_questions:
                    mock_questions.return_value = []

                    with patch.object(brief_agent, '_recommend_project_lead') as mock_lead:
                        mock_lead.return_value = {"name": "Sarah Johnson", "confidence_score": 0.9}

                        with patch.object(brief_agent, '_save_analysis_results') as mock_save:
                            with patch.object(brief_agent, '_create_notion_page') as mock_notion:
                                # Execute the agent
                                result = await brief_agent.execute(context)

                                # Assertions
                                assert result["status"] == "completed"
                                assert "analysis" in result
                                assert result["go_no_go_score"] == 85
                                assert len(result["clarification_questions"]) == 0
                                assert result["recommended_lead"]["name"] == "Sarah Johnson"


@pytest.mark.asyncio
async def test_email_validation_workflow():
    """Test email validation request and response workflow."""
    # Mock database session
    mock_db = AsyncMock()

    # Test Email Agent validation request
    email_agent = EmailAgent()

    validation_data = {
        "validation_id": 123,
        "recipient_email": "researcher@company.com",
        "recipient_name": "Dr. Smith",
        "question": "Do you have experience conducting conjoint analysis studies?",
        "project_title": "Consumer Preferences Study",
        "attribute_path": "capabilities.conjoint_analysis"
    }

    context = AgentContext(
        project_id=1,
        db_session=mock_db,
        data={"action": "send_validation_request", "validation": validation_data}
    )

    # Mock SMTP to avoid actual email sending
    with patch.object(email_agent, '_send_email_via_smtp') as mock_smtp:
        mock_smtp.return_value = None

        with patch.object(email_agent, '_track_thread') as mock_track:
            with patch.object(email_agent, '_mark_email_sent') as mock_mark:
                # Execute the agent
                result = await email_agent.execute(context)

                # Assertions
                assert result["status"] == "sent"
                assert "thread_id" in result
                mock_smtp.assert_called_once()
                mock_track.assert_called_once()


@pytest.mark.asyncio
async def test_knowledge_base_integration():
    """Test knowledge base integration with planning agent."""
    # Mock database session
    mock_db = AsyncMock()

    # Test Planning Agent with KB integration
    planning_agent = PlanningAgent()

    # Mock requirements
    requirements = {
        "client_name": "Test Corp",
        "methodology_requirements": ["survey", "focus groups"],
        "timeline": {"total_weeks": 8},
        "budget_range": {"max": 50000}
    }

    context = AgentContext(
        project_id=1,
        db_session=mock_db,
        data={"requirements": requirements}
    )

    # Mock KB search
    with patch('app.agents.planning_agent.KnowledgeBase') as mock_kb_class:
        mock_kb = AsyncMock()
        mock_kb_class.return_value = mock_kb

        # Mock search results
        mock_kb.search_resources.return_value = [
            {
                "id": 1,
                "name": "Jane Doe",
                "type": "person",
                "capabilities": ["survey", "focus groups"],
                "availability": "available",
                "similarity_score": 0.9,
                "confidence_score": 0.8
            }
        ]

        with patch.object(planning_agent, '_calculate_match_scores') as mock_match:
            mock_match.return_value = [{
                "id": 1,
                "name": "Jane Doe",
                "capability_match": 90,
                "availability_score": 85,
                "overall_score": 88,
                "strengths": ["Survey expertise"],
                "concerns": []
            }]

            with patch.object(planning_agent, '_identify_resource_gaps') as mock_gaps:
                mock_gaps.return_value = []

                with patch.object(planning_agent, '_identify_validation_needs') as mock_validation:
                    mock_validation.return_value = {"validations_needed": []}

                    with patch.object(planning_agent, '_orchestrate_validations') as mock_orchestrate:
                        mock_orchestrate.return_value = {"status": "validations_triggered", "pending": []}

                        with patch.object(planning_agent, '_create_project_plan') as mock_plan:
                            mock_plan.return_value = {
                                "phases": [{"name": "Fieldwork", "duration": 4}],
                                "resources": [{"name": "Jane Doe"}],
                                "costs": {"total": 35000}
                            }

                            with patch.object(planning_agent, '_refine_plan_with_validations') as mock_refine:
                                mock_refine.return_value = {"status": "refined"}

                                with patch.object(planning_agent, '_save_project_plan') as mock_save:
                                    # Execute the agent
                                    result = await planning_agent.execute(context)

                                    # Assertions
                                    assert result["status"] == "completed"
                                    assert "resource_matches" in result
                                    assert "validations_completed" in result
                                    mock_kb.search_resources.assert_called()


@pytest.mark.asyncio
async def test_error_recovery():
    """Test error recovery and checkpoint system."""
    # Mock database session
    mock_db = AsyncMock()

    # Test agent with error recovery
    brief_agent = BriefReviewAgent()

    context = AgentContext(
        project_id=1,
        db_session=mock_db
    )

    # Mock checkpoint loading (simulating recovery from failure)
    with patch.object(brief_agent, '_load_checkpoint') as mock_load:
        mock_load.return_value = {
            "status": "failed",
            "data": {"error": "Previous failure", "project_id": 1}
        }

        with patch.object(brief_agent, '_resume_from_checkpoint') as mock_resume:
            mock_resume.return_value = {"status": "recovered", "recovered_from_checkpoint": True}

            # Execute the agent
            result = await brief_agent.execute(context)

            # Assertions
            assert result["recovered_from_checkpoint"] is True
            mock_load.assert_called_once_with(1, "brief_review")
            mock_resume.assert_called_once()


@pytest.mark.asyncio
async def test_web_research_integration():
    """Test web research service integration."""
    from app.services.web_research import web_research_service

    # Test company research (mocked since no API key)
    company_info = await web_research_service.search_company_info("Test Company")

    # Should return basic structure even with mock data
    assert "name" in company_info
    assert company_info["name"] == "Test Company"


@pytest.mark.asyncio
async def test_notion_workspace_integration():
    """Test Notion workspace integration (mocked)."""
    from app.agents.notion_agent import NotionAgent

    notion_agent = NotionAgent()

    # Test RFP page creation (should work with mock)
    context = AgentContext(
        project_id=1,
        data={
            "analysis_data": {
                "client_name": "Test Corp",
                "go_no_go_score": 85,
                "recommendation": "GO"
            }
        }
    )

    result = await notion_agent._create_rfp_analysis_page(context)

    # Should return mock page ID
    assert "page_id" in result
    assert result["page_id"].startswith("mock_page_")


if __name__ == "__main__":
    # Run basic smoke tests
    print("Running integration smoke tests...")

    async def run_smoke_tests():
        try:
            # Test agent registry
            agents = agent_registry.list_agents()
            print(f"✓ Agent registry has {len(agents)} agents: {agents}")

            # Test web research service
            company_info = await web_research_service.search_company_info("TestCorp")
            print(f"✓ Web research service returned: {company_info['name']}")

            print("✓ All smoke tests passed!")

        except Exception as e:
            print(f"✗ Smoke test failed: {e}")
            raise

    asyncio.run(run_smoke_tests())
