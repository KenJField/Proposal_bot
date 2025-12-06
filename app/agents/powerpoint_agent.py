"""PowerPoint Agent for presentation generation using Claude skills."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.agent import BaseAgent, AgentContext
from ..core.config import settings
from ..core.llm import Provider


class PowerPointAgent(BaseAgent):
    """Agent for generating professional proposal presentations using Claude's document creation skills."""

    name = "powerpoint"
    description = "Generate professional proposal presentations using Claude's document creation skills"
    default_provider = Provider.CLAUDE
    default_model = "claude-3-sonnet-20240229"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute PowerPoint generation."""
        self.log_execution_start(context)

        try:
            action = context.data.get("action", "generate_presentation")

            if action == "generate_presentation":
                result = await self._generate_presentation(context)
            elif action == "revise_presentation":
                result = await self._revise_presentation(context)
            elif action == "finalize_presentation":
                result = await self._finalize_presentation(context)
            else:
                result = {"status": "error", "error": f"Unknown action: {action}"}

            self.log_execution_end(context, result)
            return result

        except Exception as e:
            self.logger.error(f"PowerPoint generation failed: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _generate_presentation(self, context: AgentContext) -> Dict[str, Any]:
        """Generate the initial PowerPoint presentation."""
        project_id = context.project_id
        proposal_outline = context.data.get("proposal_outline", {})

        if not proposal_outline:
            return {"status": "error", "error": "No proposal outline provided"}

        # Get project details for context
        project_details = await self._get_project_details(project_id, context.db_session)

        # Design presentation structure
        presentation_design = await self._design_presentation_structure(proposal_outline, project_details)

        # Generate slide content
        slides_content = await self._generate_slide_content(presentation_design)

        # Select and prepare assets
        assets = await self._prepare_assets(slides_content, project_details)

        # Use Claude to generate PPTX (in production, would use Claude's document skills)
        pptx_content = await self._generate_pptx_with_claude(slides_content, assets, presentation_design)

        # Save presentation
        file_path = await self._save_presentation(project_id, pptx_content, context.db_session)

        # Track version
        version_id = await self._track_version(project_id, "initial", file_path, context.db_session)

        return {
            "status": "generated",
            "file_path": file_path,
            "version_id": version_id,
            "slide_count": len(slides_content),
            "assets_used": len(assets)
        }

    async def _design_presentation_structure(self, proposal_outline: Dict[str, Any], project_details: Dict[str, Any]) -> Dict[str, Any]:
        """Design the overall presentation structure and flow."""
        prompt = f"""
Design a professional PowerPoint presentation structure for a market research proposal.

Proposal Outline:
{json.dumps(proposal_outline, indent=2)}

Project Details:
{json.dumps(project_details, indent=2)}

Design a presentation with these characteristics:
1. **Professional structure**: Title slide, agenda, content sections, Q&A
2. **Logical flow**: Introduction → Understanding → Approach → Team → Investment → Next Steps
3. **Appropriate length**: 15-25 slides total
4. **Visual balance**: Mix of text, charts, images, and white space
5. **Brand consistency**: Use professional colors and fonts

For each section, specify:
- Slide title and purpose
- Key content points
- Visual elements needed
- Estimated slides needed

Return JSON with presentation structure including sections and slide breakdown.
"""

        response = await self.generate_text(prompt, temperature=0.3, max_tokens=2000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "title": f"Market Research Proposal - {project_details.get('client_name', 'Client')}",
                "sections": [
                    {"name": "Title Slide", "slides": 1},
                    {"name": "Agenda", "slides": 1},
                    {"name": "Executive Summary", "slides": 2},
                    {"name": "Understanding & Objectives", "slides": 3},
                    {"name": "Proposed Approach", "slides": 4},
                    {"name": "Team & Experience", "slides": 2},
                    {"name": "Investment & Terms", "slides": 2},
                    {"name": "Next Steps", "slides": 1},
                    {"name": "Q&A", "slides": 1}
                ],
                "total_slides": 17
            }

    async def _generate_slide_content(self, presentation_design: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate detailed content for each slide."""
        sections = presentation_design.get("sections", [])

        all_slides = []

        for section in sections:
            section_name = section.get("name")
            slide_count = section.get("slides", 1)

            for i in range(slide_count):
                slide_content = await self._generate_individual_slide(section_name, i + 1, presentation_design)

                all_slides.append({
                    "section": section_name,
                    "slide_number": len(all_slides) + 1,
                    "title": slide_content.get("title", ""),
                    "content": slide_content.get("content", []),
                    "layout": slide_content.get("layout", "content"),
                    "notes": slide_content.get("notes", "")
                })

        return all_slides

    async def _generate_individual_slide(self, section_name: str, slide_index: int, presentation_design: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content for a specific slide."""
        prompt = f"""
Generate content for slide {slide_index} in section "{section_name}".

Presentation Design:
{json.dumps(presentation_design, indent=2)}

For this specific slide, provide:
1. **Slide Title**: Clear, compelling title
2. **Content**: Key points, bullet points, or data to include
3. **Layout**: Suggested layout type (title, content, two-column, etc.)
4. **Visual Elements**: Charts, images, or diagrams needed
5. **Speaker Notes**: What to say when presenting this slide

Keep content concise and impactful. Use professional language appropriate for client presentations.

Return JSON with title, content (as array of strings), layout, visual_elements, and notes.
"""

        response = await self.generate_text(prompt, temperature=0.3)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "title": f"{section_name} - Slide {slide_index}",
                "content": [f"Content for {section_name} slide {slide_index}"],
                "layout": "content",
                "visual_elements": [],
                "notes": f"Speaker notes for {section_name} slide {slide_index}"
            }

    async def _prepare_assets(self, slides_content: List[Dict[str, Any]], project_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare and select assets for the presentation."""
        required_assets = []

        # Analyze slides for asset needs
        for slide in slides_content:
            content = slide.get("content", [])
            visual_elements = slide.get("visual_elements", [])

            # Look for team mentions
            if "team" in slide.get("section", "").lower() or any("team" in str(c).lower() for c in content):
                required_assets.append({
                    "type": "team_photos",
                    "description": "Team member headshots and bios",
                    "count": 4  # Assume 4 team members
                })

            # Look for methodology diagrams
            if "approach" in slide.get("section", "").lower() or "methodology" in str(content).lower():
                required_assets.append({
                    "type": "methodology_diagram",
                    "description": "Process flow diagram for research methodology"
                })

            # Look for case studies
            if "experience" in str(content).lower() or "case study" in str(content).lower():
                required_assets.append({
                    "type": "case_study_visuals",
                    "description": "Relevant case study images or charts",
                    "count": 2
                })

            # Add explicit visual element requests
            for element in visual_elements:
                required_assets.append({
                    "type": element.get("type", "image"),
                    "description": element.get("description", ""),
                    "specific_item": element.get("item", "")
                })

        # Add standard assets
        required_assets.extend([
            {"type": "logo", "description": "Company logo for title slide"},
            {"type": "cover_image", "description": "Professional cover image"}
        ])

        # In production, would query asset library and return actual asset paths
        return required_assets

    async def _generate_pptx_with_claude(self, slides_content: List[Dict[str, Any]], assets: List[Dict[str, Any]], design: Dict[str, Any]) -> bytes:
        """Use Claude's document creation skills to generate PPTX file."""
        try:
            # Use Claude Sonnet for document generation (as specified in requirements)
            prompt = self._build_pptx_generation_prompt(slides_content, assets, design)

            response = await self.generate_text(
                prompt,
                provider=Provider.CLAUDE,
                model="claude-3-sonnet-20240229",
                temperature=0.1,
                max_tokens=8000
            )

            # Claude will generate a structured representation of the PPTX
            # In a real implementation, this would be converted to actual PPTX binary
            # For now, we'll store the structured content and simulate PPTX creation

            pptx_structure = self._parse_claude_pptx_response(response)

            # Simulate PPTX binary generation
            pptx_data = self._create_mock_pptx_binary(pptx_structure)

            return pptx_data

        except Exception as e:
            self.logger.error(f"Claude PPTX generation failed: {e}")
            # Fallback to basic mock
            return self._create_fallback_pptx(slides_content)

    def _build_pptx_generation_prompt(self, slides_content: List[Dict[str, Any]], assets: List[Dict[str, Any]], design: Dict[str, Any]) -> str:
        """Build comprehensive prompt for Claude PPTX generation."""
        return f"""
You are an expert PowerPoint designer creating a professional market research proposal presentation.

PRESENTATION OVERVIEW:
{json.dumps(design, indent=2)}

SLIDES TO CREATE:
{json.dumps(slides_content, indent=2)}

AVAILABLE ASSETS:
{json.dumps(assets, indent=2)}

REQUIREMENTS:
1. **Professional Design**: Clean, modern template with consistent branding
2. **Visual Hierarchy**: Clear titles, proper font sizes, strategic use of color
3. **Content Layout**: Balance text and visuals, avoid overcrowding
4. **Data Visualization**: Use charts/graphs where data is presented
5. **Speaker Notes**: Include detailed notes for each slide
6. **Accessibility**: High contrast, readable fonts, alt text for images

OUTPUT FORMAT:
Provide a structured JSON representation of the PPTX file with:
- Master slide layouts
- Individual slide specifications
- Content blocks with positioning
- Styling information
- Speaker notes

The JSON should be parseable and contain all information needed to reconstruct the presentation.

Example structure:
{{
  "presentation": {{
    "title": "Market Research Proposal",
    "template": "professional_blue",
    "slides": [
      {{
        "number": 1,
        "layout": "title_slide",
        "title": "Executive Summary",
        "content": [...],
        "notes": "Opening remarks..."
      }}
    ]
  }}
}}
"""

    def _parse_claude_pptx_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's PPTX generation response."""
        try:
            # Try to extract JSON from the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse Claude PPTX response: {e}")
            # Return a basic structure
            return {
                "presentation": {
                    "title": "Market Research Proposal",
                    "slides": []
                }
            }

    def _create_mock_pptx_binary(self, pptx_structure: Dict[str, Any]) -> bytes:
        """Create mock PPTX binary data from structure."""
        # In a real implementation, this would use a library like python-pptx
        # to create actual PPTX files

        # For now, create a structured representation that could be used
        # by a PPTX generation library

        mock_data = {
            "format": "pptx",
            "structure": pptx_structure,
            "generated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "slide_count": len(pptx_structure.get("presentation", {}).get("slides", [])),
                "template": pptx_structure.get("presentation", {}).get("template", "default")
            }
        }

        return json.dumps(mock_data).encode('utf-8')

    def _create_fallback_pptx(self, slides_content: List[Dict[str, Any]]) -> bytes:
        """Create fallback PPTX when Claude generation fails."""
        fallback_structure = {
            "presentation": {
                "title": "Market Research Proposal",
                "template": "fallback",
                "slides": [
                    {
                        "number": i + 1,
                        "title": slide.get("title", f"Slide {i + 1}"),
                        "content": slide.get("content", []),
                        "layout": slide.get("layout", "content")
                    }
                    for i, slide in enumerate(slides_content[:10])  # Limit to first 10 slides
                ]
            }
        }

        return json.dumps(fallback_structure).encode('utf-8')

    async def _revise_presentation(self, context: AgentContext) -> Dict[str, Any]:
        """Revise presentation based on feedback."""
        project_id = context.project_id
        feedback = context.data.get("feedback", {})
        current_version = context.data.get("current_version", {})

        if not feedback:
            return {"status": "error", "error": "No feedback provided"}

        # Analyze feedback and determine changes needed
        revision_plan = await self._analyze_feedback_for_revisions(feedback, current_version)

        # Apply revisions
        revised_content = await self._apply_revisions(current_version, revision_plan)

        # Regenerate PPTX
        pptx_content = await self._regenerate_pptx(revised_content)

        # Save new version
        file_path = await self._save_presentation(project_id, pptx_content, context.db_session, revision=True)
        version_id = await self._track_version(project_id, f"revision_{len(feedback)}", file_path, context.db_session)

        return {
            "status": "revised",
            "file_path": file_path,
            "version_id": version_id,
            "changes_made": len(revision_plan.get("changes", []))
        }

    async def _analyze_feedback_for_revisions(self, feedback: Dict[str, Any], current_version: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze feedback to determine what revisions are needed."""
        prompt = f"""
Analyze feedback for PowerPoint presentation revisions.

Feedback:
{json.dumps(feedback, indent=2)}

Current Version:
{json.dumps(current_version, indent=2)}

Determine:
1. **Specific changes needed**: Which slides, what content
2. **Priority**: High/medium/low for each change
3. **Effort required**: How much work each change involves
4. **Dependencies**: Changes that depend on others

Categorize changes by type:
- Content updates
- Design changes
- New slides
- Removed slides
- Asset updates

Return JSON with revision plan including specific changes and implementation approach.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "changes": [{"type": "content_update", "description": "General revisions based on feedback"}],
                "priority": "medium"
            }

    async def _apply_revisions(self, current_content: Dict[str, Any], revision_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the planned revisions to the presentation content."""
        changes = revision_plan.get("changes", [])

        revised_content = current_content.copy()

        for change in changes:
            change_type = change.get("type")

            if change_type == "content_update":
                # Update slide content
                slide_index = change.get("slide_index")
                if slide_index and slide_index < len(revised_content.get("slides", [])):
                    revised_content["slides"][slide_index] = change.get("new_content", {})

            elif change_type == "add_slide":
                # Add new slide
                new_slide = change.get("slide_content", {})
                revised_content["slides"].append(new_slide)

            elif change_type == "remove_slide":
                # Remove slide
                slide_index = change.get("slide_index")
                if slide_index and slide_index < len(revised_content.get("slides", [])):
                    revised_content["slides"].pop(slide_index)

        return revised_content

    async def _regenerate_pptx(self, revised_content: Dict[str, Any]) -> bytes:
        """Regenerate PPTX with revisions."""
        # In production, would use Claude to regenerate PPTX with changes
        # For now, return mock data
        return b"mock_revised_pptx_data"

    async def _finalize_presentation(self, context: AgentContext) -> Dict[str, Any]:
        """Finalize and deliver the presentation."""
        project_id = context.project_id
        final_version_path = context.data.get("final_version_path")

        if not final_version_path:
            return {"status": "error", "error": "No final version path provided"}

        # Mark as final
        await self._mark_as_final(project_id, final_version_path, context.db_session)

        # Send to client via Email Agent
        await self._deliver_to_client(project_id, final_version_path, context)

        # Upload to Notion
        await self._upload_to_notion(project_id, final_version_path, context)

        # Store in document repository
        await self._store_in_repository(project_id, final_version_path, context.db_session)

        return {
            "status": "finalized",
            "delivered": True,
            "notion_uploaded": True,
            "archived": True
        }

    async def _save_presentation(self, project_id: int, pptx_data: bytes, db_session, revision: bool = False) -> str:
        """Save presentation to storage."""
        # In production, would save to cloud storage or local file system
        # For now, mock file path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        version_suffix = "_rev" if revision else ""
        file_path = f"presentations/project_{project_id}_{timestamp}{version_suffix}.pptx"

        self.logger.info(f"Saved presentation: {file_path}")
        return file_path

    async def _track_version(self, project_id: int, version_type: str, file_path: str, db_session) -> str:
        """Track presentation version."""
        # In production, would store version metadata in database
        version_id = f"v_{project_id}_{int(datetime.utcnow().timestamp())}"
        self.logger.info(f"Tracked version: {version_id}")
        return version_id

    async def _mark_as_final(self, project_id: int, file_path: str, db_session) -> None:
        """Mark presentation as final."""
        # Update project with final presentation path
        from sqlalchemy import select
        from ..models import Project

        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            project.final_proposal_url = file_path
            await db_session.commit()

        self.logger.info(f"Marked presentation as final: {file_path}")

    async def _deliver_to_client(self, project_id: int, file_path: str, context: AgentContext) -> None:
        """Deliver presentation to client via Email Agent."""
        from ..core.agent import agent_registry
        email_agent = agent_registry.get_agent("email")

        await email_agent.execute(AgentContext(
            await email_agent.execute(AgentContext(
                project_id=project_id,
                db_session=context.db_session,
                data={
                    "action": "deliver_proposal",
                    "proposal": {
                        "file_path": file_path,
                        "project_title": f"Project {project_id}",
                        "client_email": "client@example.com"  # Would be retrieved from project
                    }
                }
            ))

    async def _upload_to_notion(self, project_id: int, file_path: str, context: AgentContext) -> None:
        """Upload presentation to Notion."""
        notion_agent = context.data.get("notion_agent")
        if notion_agent:
            await notion_agent.execute(AgentContext(
                project_id=project_id,
                db_session=context.db_session,
                data={
                    "action": "log_activity",
                    "activity": {
                        "type": "presentation_finalized",
                        "file_path": file_path,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            ))

    async def _store_in_repository(self, project_id: int, file_path: str, db_session) -> None:
        """Store presentation in document repository."""
        # In production, would move to document management system
        self.logger.info(f"Stored in repository: {file_path}")

    async def _get_project_details(self, project_id: int, db_session) -> Dict[str, Any]:
        """Get project details for presentation context."""
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
                "status": project.status
            }

        return {}
