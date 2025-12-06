"""Notion Agent for workspace management and visibility."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from ..core.agent import BaseAgent, AgentContext
from ..core.config import settings
from ..core.llm import Provider


class NotionAgent(BaseAgent):
    """Agent for providing visibility into all agent activity via Notion workspace."""

    name = "notion"
    description = "Provide visibility into all agent activity via Notion workspace"
    default_provider = Provider.GEMINI
    default_model = "gemini-1.5-flash"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize Notion client
        if settings.notion_token:
            self.notion_client = Client(auth=settings.notion_token)
            self.logger.info("Notion client initialized successfully")
        else:
            self.notion_client = None
            self.logger.warning("Notion token not configured - running in mock mode")

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute Notion workspace management tasks."""
        self.log_execution_start(context)

        try:
            action = context.data.get("action", "update_project_status")

            if action == "create_rfp_page":
                result = await self._create_rfp_analysis_page(context)
            elif action == "update_project_status":
                result = await self._update_project_status(context)
            elif action == "create_project_plan":
                result = await self._create_project_plan_page(context)
            elif action == "log_activity":
                result = await self._log_activity(context)
            elif action == "update_resource_calendar":
                result = await self._update_resource_calendar(context)
            elif action == "check_user_feedback":
                result = await self._check_user_feedback(context)
            else:
                result = {"status": "error", "error": f"Unknown action: {action}"}

            self.log_execution_end(context, result)
            return result

        except Exception as e:
            self.logger.error(f"Notion agent execution failed: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _create_rfp_analysis_page(self, context: AgentContext) -> Dict[str, Any]:
        """Create a Notion page for RFP analysis."""
        project_id = context.project_id
        analysis_data = context.data.get("analysis_data", {})

        # Get project details
        project_details = await self._get_project_details(project_id, context.db_session)

        # Structure page content
        page_content = await self._structure_rfp_page_content(project_details, analysis_data)

        # Create page in Notion (mock implementation)
        page_id = await self._create_notion_page(
            title=f"RFP Analysis: {project_details.get('title', 'Unknown')}",
            content=page_content,
            database_id=settings.notion_database_ids.get("rfp_tracking")
        )

        # Update project with Notion page ID
        await self._link_notion_page(project_id, page_id, context.db_session)

        return {
            "status": "created",
            "page_id": page_id,
            "page_url": f"https://notion.so/{page_id.replace('-', '')}"
        }

    async def _structure_rfp_page_content(self, project_details: Dict[str, Any], analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Structure content for RFP analysis page."""
        prompt = f"""
Create a structured Notion page for RFP analysis.

Project Details:
{json.dumps(project_details, indent=2)}

Analysis Data:
{json.dumps(analysis_data, indent=2)}

Structure the page with these sections:
1. **Overview**: Client, opportunity value, deadline
2. **Requirements Summary**: Key requirements extracted
3. **Go/No-Go Analysis**: Score, recommendation, key factors
4. **Methodology Fit**: How well we match requirements
5. **Resource Considerations**: Initial resource assessment
6. **Risks & Issues**: Potential challenges identified
7. **Next Steps**: Recommended actions

Use Notion formatting with headings, bullet points, and callouts for important information.

Return JSON with page structure including blocks and properties.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "title": f"RFP Analysis: {project_details.get('title', 'Unknown')}",
                "blocks": [
                    {"type": "heading_1", "content": "RFP Analysis"},
                    {"type": "paragraph", "content": "Analysis in progress..."}
                ]
            }

    async def _update_project_status(self, context: AgentContext) -> Dict[str, Any]:
        """Update project status in Notion."""
        project_id = context.project_id
        new_status = context.data.get("status")
        status_details = context.data.get("status_details", {})

        if not new_status:
            return {"status": "error", "error": "No status provided"}

        # Find existing Notion page
        notion_page_id = await self._get_notion_page_id(project_id, context.db_session)

        if not notion_page_id:
            return {"status": "error", "error": "No Notion page found for project"}

        # Update page properties and content
        update_content = await self._create_status_update_content(new_status, status_details)

        await self._update_notion_page(notion_page_id, update_content)

        # Log status change in activity feed
        await self._log_status_change(project_id, new_status, status_details, context.db_session)

        return {"status": "updated", "page_id": notion_page_id}

    async def _create_status_update_content(self, new_status: str, status_details: Dict[str, Any]) -> Dict[str, Any]:
        """Create content for status update."""
        prompt = f"""
Create Notion content for a project status update.

New Status: {new_status}
Details: {json.dumps(status_details, indent=2)}

Create appropriate Notion blocks to add to the page:
- Status indicator/callout
- Timestamp
- Key details about the status change
- Next steps or actions needed

Use Notion formatting with callouts, timestamps, and clear section headers.
"""

        response = await self.generate_text(prompt, temperature=0.1)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "blocks": [
                    {"type": "callout", "content": f"Status updated to: {new_status}"},
                    {"type": "paragraph", "content": json.dumps(status_details)}
                ]
            }

    async def _create_project_plan_page(self, context: AgentContext) -> Dict[str, Any]:
        """Create a detailed project plan page with phases as databases."""
        project_id = context.project_id
        plan_data = context.data.get("plan_data", {})

        # Create main project plan page
        plan_page_content = await self._structure_plan_page_content(plan_data)

        page_id = await self._create_notion_page(
            title=f"Project Plan: {plan_data.get('project_title', 'Unknown')}",
            content=plan_page_content,
            database_id=settings.notion_database_ids.get("project_plans")
        )

        # Create phase database
        phases = plan_data.get("phases", [])
        phase_db_id = await self._create_phase_database(page_id, phases)

        # Create resource allocation database
        resources = plan_data.get("resource_allocation", [])
        resource_db_id = await self._create_resource_allocation_database(page_id, resources)

        return {
            "status": "created",
            "plan_page_id": page_id,
            "phase_database_id": phase_db_id,
            "resource_database_id": resource_db_id
        }

    async def _structure_plan_page_content(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Structure content for project plan page."""
        prompt = f"""
Create a comprehensive Notion project plan page.

Plan Data:
{json.dumps(plan_data, indent=2)}

Structure with:
1. **Executive Summary**: High-level plan overview
2. **Timeline Overview**: Key milestones and duration
3. **Resource Summary**: Team composition and allocation
4. **Budget Summary**: Cost breakdown and assumptions
5. **Risk Register**: Key risks and mitigation
6. **Phases & Deliverables**: Detailed breakdown (will link to database)
7. **Success Criteria**: How success will be measured

Use Notion formatting with databases for phases and resources.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "title": "Project Plan",
                "blocks": [
                    {"type": "heading_1", "content": "Project Plan Overview"},
                    {"type": "paragraph", "content": json.dumps(plan_data, indent=2)}
                ]
            }

    async def _log_activity(self, context: AgentContext) -> Dict[str, Any]:
        """Log activity in the Notion activity feed."""
        activity_data = context.data.get("activity", {})

        # Add to activity feed database
        await self._add_to_activity_feed(activity_data, context.db_session)

        return {"status": "logged"}

    async def _update_resource_calendar(self, context: AgentContext) -> Dict[str, Any]:
        """Update resource availability calendar."""
        calendar_data = context.data.get("calendar_data", {})

        # Update resource calendar database
        await self._update_calendar_database(calendar_data)

        return {"status": "updated"}

    async def _check_user_feedback(self, context: AgentContext) -> Dict[str, Any]:
        """Check for user feedback and comments on Notion pages."""
        project_id = context.project_id

        # Get Notion page ID
        notion_page_id = await self._get_notion_page_id(project_id, context.db_session)

        if not notion_page_id:
            return {"status": "no_page"}

        # Check for comments and updates (mock implementation)
        feedback = await self._get_page_feedback(notion_page_id)

        if feedback:
            # Process feedback and relay to appropriate agents
            await self._relay_feedback_to_agents(feedback, context)

        return {
            "status": "checked",
            "feedback_found": len(feedback),
            "feedback": feedback
        }

    async def _relay_feedback_to_agents(self, feedback: List[Dict[str, Any]], context: AgentContext) -> None:
        """Relay user feedback to appropriate agents."""
        for item in feedback:
            feedback_type = item.get("type")

            if feedback_type == "approval":
                # Relay to GTM agent
                gtm_agent = context.data.get("gtm_agent")
                if gtm_agent:
                    await gtm_agent.incorporate_feedback(AgentContext(
                        project_id=context.project_id,
                        db_session=context.db_session,
                        data={"feedback": item}
                    ))

            elif feedback_type == "resource_override":
                # Relay to Planning agent
                planning_agent = context.data.get("planning_agent")
                if planning_agent:
                    await planning_agent.execute(AgentContext(
                        project_id=context.project_id,
                        db_session=context.db_session,
                        data={"action": "apply_override", "override": item}
                    ))

            elif feedback_type == "status_update":
                # Update project status
                await self._update_project_status_from_feedback(item, context)

    async def _update_project_status_from_feedback(self, feedback: Dict[str, Any], context: AgentContext) -> None:
        """Update project status based on user feedback."""
        new_status = feedback.get("status")
        if new_status:
            # Update in database
            await self._update_project_status_in_db(context.project_id, new_status, context.db_session)

            # Update in Notion
            await self._update_project_status(AgentContext(
                project_id=context.project_id,
                db_session=context.db_session,
                data={"status": new_status, "status_details": feedback}
            ))

    # Real Notion API implementations

    async def _create_notion_page(self, title: str, content: Dict[str, Any], database_id: Optional[str] = None) -> str:
        """Create a new page in Notion."""
        if not self.notion_client:
            return self._mock_create_page(title, content, database_id)

        try:
            # Prepare page properties
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }

            # Add creation timestamp
            properties["Created"] = {
                "date": {
                    "start": datetime.utcnow().isoformat()
                }
            }

            # Prepare page data
            page_data = {
                "properties": properties,
            }

            # If database_id provided, create in database
            if database_id:
                page_data["parent"] = {"database_id": database_id}
            else:
                # Create in default location (would need to configure a default page)
                page_data["parent"] = {"type": "page_id", "page_id": settings.notion_database_ids.get("root_page")}

            # Add content blocks
            if content.get("blocks"):
                page_data["children"] = self._convert_content_to_blocks(content)

            # Create the page
            response = self.notion_client.pages.create(**page_data)
            page_id = response["id"]

            self.logger.info(f"Created Notion page: {page_id} - {title}")
            return page_id

        except APIResponseError as e:
            self.logger.error(f"Notion API error creating page: {e}")
            return self._mock_create_page(title, content, database_id)
        except Exception as e:
            self.logger.error(f"Unexpected error creating Notion page: {e}")
            return self._mock_create_page(title, content, database_id)

    def _convert_content_to_blocks(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert content structure to Notion blocks."""
        blocks = []

        if content.get("blocks"):
            for block in content["blocks"]:
                block_type = block.get("type", "paragraph")
                block_content = block.get("content", "")

                if block_type == "heading_1":
                    blocks.append({
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": block_content}}]
                        }
                    })
                elif block_type == "heading_2":
                    blocks.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": block_content}}]
                        }
                    })
                elif block_type == "callout":
                    blocks.append({
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{"type": "text", "text": {"content": block_content}}],
                            "icon": {"emoji": "ℹ️"}
                        }
                    })
                else:  # default to paragraph
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": block_content}}]
                        }
                    })

        return blocks

    def _mock_create_page(self, title: str, content: Dict[str, Any], database_id: Optional[str] = None) -> str:
        """Fallback mock implementation."""
        page_id = f"mock_page_{hash(title + str(datetime.utcnow()))}"
        self.logger.warning(f"Created mock Notion page (API unavailable): {page_id} - {title}")
        return page_id

    async def _update_notion_page(self, page_id: str, content: Dict[str, Any]) -> None:
        """Update an existing Notion page."""
        if not self.notion_client:
            self.logger.warning(f"Mock update Notion page (API unavailable): {page_id}")
            return

        try:
            # Append new blocks to the page
            if content.get("blocks"):
                blocks = self._convert_content_to_blocks(content)

                for block in blocks:
                    self.notion_client.blocks.children.append(
                        block_id=page_id,
                        children=[block]
                    )

            self.logger.info(f"Updated Notion page: {page_id}")

        except APIResponseError as e:
            self.logger.error(f"Notion API error updating page: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error updating Notion page: {e}")

    async def _create_phase_database(self, parent_page_id: str, phases: List[Dict[str, Any]]) -> str:
        """Create a database for project phases."""
        if not self.notion_client:
            db_id = f"mock_phase_db_{hash(parent_page_id)}"
            self.logger.warning(f"Created mock phase database (API unavailable): {db_id}")
            return db_id

        try:
            # Create database properties
            properties = {
                "Name": {"title": {}},
                "Phase": {"rich_text": {}},
                "Start Date": {"date": {}},
                "End Date": {"date": {}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Not Started", "color": "gray"},
                            {"name": "In Progress", "color": "blue"},
                            {"name": "Completed", "color": "green"},
                            {"name": "Blocked", "color": "red"}
                        ]
                    }
                },
                "Assigned To": {"rich_text": {}}
            }

            database_data = {
                "parent": {"type": "page_id", "page_id": parent_page_id},
                "title": [{"type": "text", "text": {"content": "Project Phases"}}],
                "properties": properties
            }

            response = self.notion_client.databases.create(**database_data)
            db_id = response["id"]

            # Add initial phase entries
            if phases:
                await self._populate_phase_database(db_id, phases)

            self.logger.info(f"Created phase database: {db_id}")
            return db_id

        except APIResponseError as e:
            self.logger.error(f"Notion API error creating phase database: {e}")
            return f"mock_phase_db_{hash(parent_page_id)}"
        except Exception as e:
            self.logger.error(f"Unexpected error creating phase database: {e}")
            return f"mock_phase_db_{hash(parent_page_id)}"

    async def _create_resource_allocation_database(self, parent_page_id: str, resources: List[Dict[str, Any]]) -> str:
        """Create a database for resource allocation."""
        if not self.notion_client:
            db_id = f"mock_resource_db_{hash(parent_page_id)}"
            self.logger.warning(f"Created mock resource database (API unavailable): {db_id}")
            return db_id

        try:
            # Create database properties
            properties = {
                "Name": {"title": {}},
                "Role": {"rich_text": {}},
                "Type": {
                    "select": {
                        "options": [
                            {"name": "Person", "color": "blue"},
                            {"name": "Vendor", "color": "green"},
                            {"name": "Tool", "color": "yellow"}
                        ]
                    }
                },
                "Availability": {"rich_text": {}},
                "Allocation %": {"number": {}},
                "Start Date": {"date": {}},
                "End Date": {"date": {}}
            }

            database_data = {
                "parent": {"type": "page_id", "page_id": parent_page_id},
                "title": [{"type": "text", "text": {"content": "Resource Allocation"}}],
                "properties": properties
            }

            response = self.notion_client.databases.create(**database_data)
            db_id = response["id"]

            # Add initial resource entries
            if resources:
                await self._populate_resource_database(db_id, resources)

            self.logger.info(f"Created resource database: {db_id}")
            return db_id

        except APIResponseError as e:
            self.logger.error(f"Notion API error creating resource database: {e}")
            return f"mock_resource_db_{hash(parent_page_id)}"
        except Exception as e:
            self.logger.error(f"Unexpected error creating resource database: {e}")
            return f"mock_resource_db_{hash(parent_page_id)}"

    async def _populate_phase_database(self, database_id: str, phases: List[Dict[str, Any]]) -> None:
        """Populate phase database with initial data."""
        if not self.notion_client:
            return

        for phase in phases:
            try:
                page_data = {
                    "parent": {"database_id": database_id},
                    "properties": {
                        "Name": {
                            "title": [
                                {
                                    "text": {
                                        "content": phase.get("name", "Unnamed Phase")
                                    }
                                }
                            ]
                        },
                        "Phase": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": phase.get("description", "")
                                    }
                                }
                            ]
                        },
                        "Status": {
                            "select": {
                                "name": "Not Started"
                            }
                        }
                    }
                }

                self.notion_client.pages.create(**page_data)

            except Exception as e:
                self.logger.error(f"Failed to add phase to database: {e}")

    async def _populate_resource_database(self, database_id: str, resources: List[Dict[str, Any]]) -> None:
        """Populate resource database with initial data."""
        if not self.notion_client:
            return

        for resource in resources:
            try:
                page_data = {
                    "parent": {"database_id": database_id},
                    "properties": {
                        "Name": {
                            "title": [
                                {
                                    "text": {
                                        "content": resource.get("name", "Unnamed Resource")
                                    }
                                }
                            ]
                        },
                        "Role": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": resource.get("role", "")
                                    }
                                }
                            ]
                        },
                        "Type": {
                            "select": {
                                "name": resource.get("type", "Person").title()
                            }
                        },
                        "Availability": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": resource.get("availability", "Unknown")
                                    }
                                }
                            ]
                        }
                    }
                }

                self.notion_client.pages.create(**page_data)

            except Exception as e:
                self.logger.error(f"Failed to add resource to database: {e}")

    async def _add_to_activity_feed(self, activity_data: Dict[str, Any], db_session) -> None:
        """Add activity to the activity feed database."""
        # Mock implementation
        self.logger.info(f"Added to activity feed: {activity_data}")

    async def _update_calendar_database(self, calendar_data: Dict[str, Any]) -> None:
        """Update resource calendar database."""
        # Mock implementation
        self.logger.info(f"Updated calendar: {calendar_data}")

    async def _get_page_feedback(self, page_id: str) -> List[Dict[str, Any]]:
        """Get user feedback from Notion page."""
        # Mock implementation - in production would query Notion API for comments
        return []  # No feedback in mock

    async def _get_project_details(self, project_id: int, db_session) -> Dict[str, Any]:
        """Get project details from database."""
        from sqlalchemy import select
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            return {
                "id": project.id,
                "title": project.title,
                "client_name": project.client_name,
                "status": project.status,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "estimated_value": project.estimated_value
            }

        return {}

    async def _get_notion_page_id(self, project_id: int, db_session) -> Optional[str]:
        """Get Notion page ID for project."""
        # In production, would store this in project metadata
        # Mock implementation
        return f"notion_page_{project_id}"

    async def _link_notion_page(self, project_id: int, page_id: str, db_session) -> None:
        """Link Notion page to project."""
        # Mock implementation - would update project metadata
        self.logger.info(f"Linked project {project_id} to Notion page {page_id}")

    async def _log_status_change(self, project_id: int, new_status: str, details: Dict[str, Any], db_session) -> None:
        """Log status change in activity feed."""
        # Mock implementation
        self.logger.info(f"Status change logged: Project {project_id} -> {new_status}")

    async def _update_project_status_in_db(self, project_id: int, new_status: str, db_session) -> None:
        """Update project status in database."""
        from sqlalchemy import select
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            project.status = new_status
            await db_session.commit()
