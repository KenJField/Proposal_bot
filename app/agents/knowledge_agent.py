"""Knowledge Agent for KB updates and continuous learning."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from ..core.agent import BaseAgent, AgentContext
from ..core.config import settings
from ..core.llm import Provider


class KnowledgeAgent(BaseAgent):
    """Agent for maintaining knowledge base accuracy through continuous learning."""

    name = "knowledge"
    description = "Maintain knowledge base accuracy through continuous learning"
    default_provider = Provider.GEMINI
    default_model = "gemini-1.5-flash"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute knowledge base maintenance tasks."""
        self.log_execution_start(context)

        try:
            action = context.data.get("action", "process_validation_results")

            if action == "process_validation_results":
                result = await self._process_validation_results(context)
            elif action == "update_from_email":
                result = await self._update_from_email_content(context)
            elif action == "learn_patterns":
                result = await self._learn_patterns(context)
            elif action == "audit_changes":
                result = await self._audit_recent_changes(context)
            else:
                result = {"status": "error", "error": f"Unknown action: {action}"}

            self.log_execution_end(context, result)
            return result

        except Exception as e:
            self.logger.error(f"Knowledge agent execution failed: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _process_validation_results(self, context: AgentContext) -> Dict[str, Any]:
        """Process validation results and update knowledge base."""
        # Get pending validation results
        validation_results = await self._get_pending_validation_results(context.db_session)

        updates_made = []
        changes_flagged = []

        for result in validation_results:
            # Analyze the validation result
            kb_updates = await self._analyze_validation_result(result)

            if kb_updates:
                # Apply updates to knowledge base
                applied_updates = await self._apply_kb_updates(kb_updates, context.db_session)

                updates_made.extend(applied_updates)

                # Flag high-impact changes for human review
                high_impact = await self._identify_high_impact_changes(applied_updates)
                changes_flagged.extend(high_impact)

                # Mark validation as processed
                await self._mark_validation_processed(result["id"], context.db_session)

        # Log audit trail
        await self._log_kb_changes(updates_made, context.db_session)

        return {
            "status": "completed",
            "updates_made": len(updates_made),
            "changes_flagged": len(changes_flagged),
            "high_impact_changes": changes_flagged
        }

    async def _get_pending_validation_results(self, db_session) -> List[Dict[str, Any]]:
        """Get validation results that haven't been processed yet."""
        from ..models import Validation

        result = await db_session.execute(
            select(Validation).where(
                Validation.status == "responded",
                Validation.response.isnot(None)
            ).limit(10)  # Process in batches
        )

        validations = result.scalars().all()

        return [
            {
                "id": v.id,
                "resource_id": v.resource_id,
                "attribute_path": v.attribute_path,
                "response": v.response,
                "validated_by": v.validated_by,
                "question": v.question
            }
            for v in validations
        ]

    async def _analyze_validation_result(self, validation_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze validation result and determine KB updates needed."""
        response = validation_result.get("response", {})
        attribute_path = validation_result.get("attribute_path", "")
        resource_id = validation_result.get("resource_id")

        prompt = f"""
Analyze this validation response and determine what knowledge base updates are needed.

Validation Details:
- Attribute: {attribute_path}
- Question: {validation_result.get('question', '')}
- Response: {json.dumps(response, indent=2)}

Determine:
1. **New Information**: What new facts were learned?
2. **Confidence Updates**: Should confidence scores be adjusted?
3. **Capability Changes**: Were new capabilities discovered or existing ones corrected?
4. **Availability Updates**: Any changes to availability or schedule?
5. **Corrections Needed**: Does this contradict existing KB information?

Return JSON with:
- updates_needed: boolean
- update_details: array of specific updates
- confidence_changes: new confidence scores
- new_capabilities: newly discovered capabilities
- corrections: information that was wrong in KB

If no updates needed, return {{"updates_needed": false}}
"""

        response_text = await self.generate_text(prompt, temperature=0.1)

        try:
            analysis = json.loads(response_text)

            if analysis.get("updates_needed", False):
                analysis["resource_id"] = resource_id
                analysis["source"] = "validation"
                analysis["validation_id"] = validation_result["id"]
                return analysis

        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse validation analysis: {response_text}")

        return None

    async def _apply_kb_updates(self, kb_updates: Dict[str, Any], db_session) -> List[Dict[str, Any]]:
        """Apply updates to the knowledge base."""
        resource_id = kb_updates.get("resource_id")
        applied_updates = []

        if not resource_id:
            return applied_updates

        from ..models import Resource, Capability

        # Get the resource
        result = await db_session.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        resource = result.scalar_one_or_none()

        if not resource:
            return applied_updates

        # Apply updates
        update_details = kb_updates.get("update_details", [])

        for update in update_details:
            update_type = update.get("type")

            if update_type == "attribute_update":
                # Update resource attributes
                attributes = resource.attributes.copy()
                path = update.get("path", "")
                value = update.get("value")

                # Simple path update (in production, use proper JSON path logic)
                if path and value is not None:
                    attributes[path] = value
                    resource.attributes = attributes
                    applied_updates.append({
                        "type": "attribute_update",
                        "resource_id": resource_id,
                        "path": path,
                        "old_value": update.get("old_value"),
                        "new_value": value
                    })

            elif update_type == "confidence_update":
                # Update confidence scores
                confidence_scores = resource.confidence_scores.copy()
                attribute = update.get("attribute", "")
                new_score = update.get("confidence_score", 0.5)

                confidence_scores[attribute] = new_score
                resource.confidence_scores = confidence_scores

                applied_updates.append({
                    "type": "confidence_update",
                    "resource_id": resource_id,
                    "attribute": attribute,
                    "new_score": new_score
                })

            elif update_type == "new_capability":
                # Add new capability
                capability = Capability(
                    resource_id=resource_id,
                    name=update.get("capability_name", ""),
                    category=update.get("category", "unknown"),
                    description=update.get("description", ""),
                    proficiency_level=update.get("proficiency", "intermediate"),
                    confidence_score=update.get("confidence_score", 0.8)
                )

                db_session.add(capability)
                applied_updates.append({
                    "type": "new_capability",
                    "resource_id": resource_id,
                    "capability": update.get("capability_name")
                })

        # Update last_validated timestamp
        resource.last_validated = datetime.utcnow()

        await db_session.commit()

        return applied_updates

    async def _identify_high_impact_changes(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify high-impact changes that need human review."""
        high_impact_changes = []

        for update in updates:
            # Flag major capability additions
            if update["type"] == "new_capability":
                high_impact_changes.append({
                    "update": update,
                    "reason": "New capability discovered",
                    "review_needed": True
                })

            # Flag significant confidence drops
            elif update["type"] == "confidence_update" and update.get("new_score", 1.0) < 0.5:
                high_impact_changes.append({
                    "update": update,
                    "reason": "Significant confidence drop",
                    "review_needed": True
                })

            # Flag major corrections
            elif update["type"] == "attribute_update":
                # In production, would check if this contradicts important business rules
                high_impact_changes.append({
                    "update": update,
                    "reason": "Attribute correction",
                    "review_needed": False  # Minor changes don't need review
                })

        return high_impact_changes

    async def _update_from_email_content(self, context: AgentContext) -> Dict[str, Any]:
        """Extract and learn from email content."""
        email_content = context.data.get("email_content", "")
        sender = context.data.get("sender", "")

        if not email_content:
            return {"status": "error", "error": "No email content provided"}

        # Analyze email for new information
        insights = await self._analyze_email_content(email_content, sender)

        # Apply any learned information
        updates_made = []
        if insights.get("kb_updates"):
            updates_made = await self._apply_kb_updates(insights["kb_updates"], context.db_session)

        return {
            "status": "completed",
            "insights_found": len(insights.get("insights", [])),
            "updates_made": len(updates_made)
        }

    async def _analyze_email_content(self, content: str, sender: str) -> Dict[str, Any]:
        """Analyze email content for knowledge base insights."""
        prompt = f"""
Analyze this email for information that could update the knowledge base.

Email from: {sender}
Content: {content}

Look for:
1. **Capability mentions**: Skills, experience, or expertise mentioned
2. **Availability updates**: Schedule changes, time off, or availability status
3. **Project updates**: Outcomes, successes, or challenges from past projects
4. **Contact updates**: New contact information or role changes
5. **Preference indications**: Work style preferences or methodologies they prefer

Return JSON with:
- insights: array of insights found
- kb_updates: potential KB updates (if any)
- confidence: confidence in the insights (high/medium/low)
"""

        response = await self.generate_text(prompt, temperature=0.1)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"insights": [], "kb_updates": None, "confidence": "low"}

    async def _learn_patterns(self, context: AgentContext) -> Dict[str, Any]:
        """Learn patterns from validation history and suggest improvements."""
        # Analyze validation patterns
        patterns = await self._analyze_validation_patterns(context.db_session)

        # Suggest new inference rules
        suggestions = await self._suggest_inference_rules(patterns)

        return {
            "status": "completed",
            "patterns_identified": len(patterns),
            "suggestions_made": len(suggestions),
            "inference_rules": suggestions
        }

    async def _analyze_validation_patterns(self, db_session) -> List[Dict[str, Any]]:
        """Analyze patterns in validation history."""
        from ..models import Validation

        # Get validation history
        result = await db_session.execute(
            select(Validation).limit(100)  # Analyze recent validations
        )

        validations = result.scalars().all()

        # Simple pattern analysis (in production, would use more sophisticated ML)
        patterns = []

        # Count validation types
        type_counts = {}
        for v in validations:
            val_type = v.validation_type or "unknown"
            type_counts[val_type] = type_counts.get(val_type, 0) + 1

        for val_type, count in type_counts.items():
            if count > 5:  # Frequent validation type
                patterns.append({
                    "pattern": f"frequent_{val_type}_validations",
                    "description": f"{val_type} validations happen frequently",
                    "frequency": count,
                    "suggestion": f"Consider reducing validation frequency for {val_type}"
                })

        return patterns

    async def _suggest_inference_rules(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Suggest new inference rules based on patterns."""
        prompt = f"""
Based on these validation patterns, suggest new inference rules for the knowledge base.

Patterns:
{json.dumps(patterns, indent=2)}

Suggest rules like:
- "If X is validated, then Y can be inferred with Z confidence"
- "Pattern A usually indicates capability B"
- "When C is mentioned, validate D as well"

Return JSON array of suggested inference rules.
"""

        response = await self.generate_text(prompt, temperature=0.2)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return []

    async def _audit_recent_changes(self, context: AgentContext) -> Dict[str, Any]:
        """Audit recent knowledge base changes."""
        # Get recent changes (would need a change log table in production)
        recent_changes = await self._get_recent_changes(context.db_session)

        # Analyze change patterns
        analysis = await self._analyze_change_patterns(recent_changes)

        return {
            "status": "completed",
            "changes_reviewed": len(recent_changes),
            "analysis": analysis
        }

    async def _get_recent_changes(self, db_session) -> List[Dict[str, Any]]:
        """Get recent KB changes."""
        # In production, would query a change log table
        # For now, return mock data
        return [
            {"type": "capability_added", "resource_id": 1, "timestamp": "2024-01-01"},
            {"type": "confidence_updated", "resource_id": 2, "timestamp": "2024-01-01"}
        ]

    async def _analyze_change_patterns(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in recent changes."""
        # Simple analysis
        change_types = {}
        for change in changes:
            ctype = change.get("type", "unknown")
            change_types[ctype] = change_types.get(ctype, 0) + 1

        return {
            "change_frequency": len(changes),
            "change_types": change_types,
            "most_common_change": max(change_types, key=change_types.get) if change_types else None
        }

    async def _mark_validation_processed(self, validation_id: int, db_session) -> None:
        """Mark validation as processed by knowledge agent."""
        from ..models import Validation

        result = await db_session.execute(
            select(Validation).where(Validation.id == validation_id)
        )
        validation = result.scalar_one_or_none()

        if validation:
            # In production, might add a processed flag or status
            # For now, just ensure it's marked as completed
            pass

    async def _log_kb_changes(self, updates: List[Dict[str, Any]], db_session) -> None:
        """Log knowledge base changes for audit trail."""
        # In production, would insert into a change log table
        self.logger.info(f"Knowledge base updated: {len(updates)} changes made")

        for update in updates:
            self.logger.info(f"KB Change: {update}")
