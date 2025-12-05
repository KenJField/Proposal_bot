"""Email Agent for handling all email communication."""

import asyncio
import email
import imaplib
import json
import logging
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, List, Optional, Tuple

import redis
from imap_tools import MailBox, AND
from pydantic import BaseModel
from sqlalchemy import select

from ..core.agent import BaseAgent, AgentContext
from ..core.config import settings
from ..core.llm import Provider


class EmailMessage(BaseModel):
    """Structured email message."""
    subject: str
    body: str
    to_email: str
    to_name: Optional[str] = None
    from_email: str = settings.smtp_username
    from_name: str = "Proposal Bot"
    thread_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class EmailThread(BaseModel):
    """Email thread tracking."""
    thread_id: str
    subject: str
    participants: List[str]
    last_message_at: datetime
    status: str = "active"  # active, resolved, timeout
    awaiting_response: bool = False
    project_id: Optional[int] = None
    validation_id: Optional[int] = None
    timeout_at: Optional[datetime] = None


class EmailAgent(BaseAgent):
    """Agent for handling all email communication."""

    name = "email"
    description = "Handle all email communication with clients, team members, and vendors"
    default_provider = Provider.GEMINI
    default_model = "gemini-1.5-flash"

    def __init__(self, redis_client: Optional[redis.Redis] = None, **kwargs):
        super().__init__(**kwargs)
        self.redis = redis_client or redis.from_url(settings.redis_url)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute email agent tasks."""
        self.log_execution_start(context)

        action = context.data.get("action", "check_inbox")

        if action == "send_email":
            result = await self._send_email(context)
        elif action == "check_inbox":
            result = await self._check_inbox(context)
        elif action == "send_validation_request":
            result = await self._send_validation_request(context)
        elif action == "send_clarification":
            result = await self._send_clarification_request(context)
        elif action == "deliver_proposal":
            result = await self._deliver_proposal(context)
        else:
            result = {"status": "error", "error": f"Unknown action: {action}"}

        self.log_execution_end(context, result)
        return result

    async def _send_email(self, context: AgentContext) -> Dict[str, Any]:
        """Send a generic email."""
        email_data = context.data.get("email")
        if not email_data:
            return {"status": "error", "error": "No email data provided"}

        email_msg = EmailMessage(**email_data)

        # Check deduplication
        if await self._is_duplicate_email(email_msg):
            return {"status": "skipped", "reason": "Duplicate email within 48 hours"}

        # Generate thread ID if not provided
        if not email_msg.thread_id:
            email_msg.thread_id = str(uuid.uuid4())

        # Send email
        try:
            await self._send_email_via_smtp(email_msg)

            # Track thread
            await self._track_thread(email_msg)

            # Mark as sent for deduplication
            await self._mark_email_sent(email_msg)

            return {"status": "sent", "thread_id": email_msg.thread_id}

        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _send_validation_request(self, context: AgentContext) -> Dict[str, Any]:
        """Send validation request to team member."""
        validation_data = context.data.get("validation")
        if not validation_data:
            return {"status": "error", "error": "No validation data provided"}

        # Generate contextual email
        email_content = await self._generate_validation_email(validation_data)

        email_msg = EmailMessage(
            subject=email_content["subject"],
            body=email_content["body"],
            to_email=validation_data["recipient_email"],
            to_name=validation_data.get("recipient_name"),
            thread_id=validation_data.get("thread_id"),
            metadata={
                "type": "validation_request",
                "validation_id": validation_data.get("validation_id"),
                "project_id": context.project_id,
                "attribute_path": validation_data.get("attribute_path")
            }
        )

        return await self._send_email(context)

    async def _send_clarification_request(self, context: AgentContext) -> Dict[str, Any]:
        """Send clarification questions to client."""
        clarification_data = context.data.get("clarification")
        if not clarification_data:
            return {"status": "error", "error": "No clarification data provided"}

        # Generate contextual email
        email_content = await self._generate_clarification_email(clarification_data)

        email_msg = EmailMessage(
            subject=email_content["subject"],
            body=email_content["body"],
            to_email=clarification_data["client_email"],
            to_name=clarification_data.get("client_name"),
            metadata={
                "type": "clarification_request",
                "project_id": context.project_id,
                "questions": clarification_data.get("questions", [])
            }
        )

        return await self._send_email(context)

    async def _deliver_proposal(self, context: AgentContext) -> Dict[str, Any]:
        """Deliver final proposal to client."""
        proposal_data = context.data.get("proposal")
        if not proposal_data:
            return {"status": "error", "error": "No proposal data provided"}

        email_msg = EmailMessage(
            subject=f"Market Research Proposal: {proposal_data.get('project_title', 'Project')}",
            body=proposal_data.get("cover_letter", "Please find attached our proposal."),
            to_email=proposal_data["client_email"],
            to_name=proposal_data.get("client_name"),
            attachments=proposal_data.get("attachments", []),
            metadata={
                "type": "proposal_delivery",
                "project_id": context.project_id,
                "proposal_url": proposal_data.get("proposal_url")
            }
        )

        return await self._send_email(context)

    async def _check_inbox(self, context: AgentContext) -> Dict[str, Any]:
        """Check inbox for new messages and process responses."""
        try:
            messages = await self._fetch_new_emails()

            processed = []
            for msg in messages:
                result = await self._process_incoming_email(msg, context)
                processed.append(result)

            return {
                "status": "processed",
                "messages_processed": len(processed),
                "results": processed
            }

        except Exception as e:
            self.logger.error(f"Failed to check inbox: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _process_incoming_email(self, email_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Process an incoming email message."""
        # Extract thread information
        thread_id = self._extract_thread_id(email_data)

        if not thread_id:
            # Not a threaded message we care about
            return {"status": "ignored", "reason": "No thread ID"}

        # Get thread information
        thread = await self._get_thread(thread_id)
        if not thread:
            return {"status": "ignored", "reason": "Unknown thread"}

        # Parse email content
        parsed_content = await self._parse_email_content(email_data)

        # Route based on thread type
        if thread.metadata.get("type") == "validation_request":
            return await self._handle_validation_response(thread, parsed_content, context)
        elif thread.metadata.get("type") == "clarification_request":
            return await self._handle_clarification_response(thread, parsed_content, context)
        else:
            return {"status": "ignored", "reason": "Unknown thread type"}

    async def _handle_validation_response(self, thread: EmailThread, content: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Handle validation response from team member."""
        validation_id = thread.metadata.get("validation_id")

        # Update validation in database
        if context.db_session and validation_id:
            from ..models import Validation

            result = await context.db_session.execute(
                select(Validation).where(Validation.id == validation_id)
            )
            validation = result.scalar_one_or_none()

            if validation:
                validation.response = content
                validation.status = "responded"
                validation.response_received_at = datetime.utcnow()
                validation.validated_by = content.get("sender_email")

                await context.db_session.commit()

        # Mark thread as resolved
        await self._update_thread_status(thread.thread_id, "resolved")

        return {
            "status": "validation_updated",
            "validation_id": validation_id,
            "response": content
        }

    async def _handle_clarification_response(self, thread: EmailThread, content: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Handle clarification response from client."""
        project_id = thread.metadata.get("project_id")

        # Update project with client answers
        if context.db_session and project_id:
            from ..models import Project

            result = await context.db_session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()

            if project:
                # Merge answers into requirements
                requirements = project.requirements.copy()
                requirements["client_answers"] = content.get("answers", {})
                requirements["clarification_received_at"] = datetime.utcnow().isoformat()

                project.requirements = requirements
                await context.db_session.commit()

        # Mark thread as resolved
        await self._update_thread_status(thread.thread_id, "resolved")

        return {
            "status": "clarification_updated",
            "project_id": project_id,
            "answers": content
        }

    async def _generate_validation_email(self, validation_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate contextual validation request email."""
        prompt = f"""
Generate a professional email asking a team member to validate their capability for a market research project.

Context:
- Attribute to validate: {validation_data.get('attribute_path', 'Unknown')}
- Question: {validation_data.get('question', 'Unknown')}
- Project: {validation_data.get('project_title', 'Market Research Project')}
- Deadline: Within 72 hours

The email should be:
- Professional and concise
- Include specific question to answer
- Explain why validation is needed
- Provide clear response instructions

Return JSON with "subject" and "body" fields.
"""

        response = await self.generate_text(prompt, temperature=0.3)
        # Parse JSON response
        import json
        try:
            return json.loads(response)
        except:
            return {
                "subject": f"Validation Request: {validation_data.get('attribute_path', 'Capability')}",
                "body": f"Please validate: {validation_data.get('question', 'Unknown question')}"
            }

    async def _generate_clarification_email(self, clarification_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate clarification request email to client."""
        questions = clarification_data.get("questions", [])

        prompt = f"""
Generate a professional email asking a client for clarification on RFP requirements.

Questions to ask:
{chr(10).join(f"- {q}" for q in questions)}

Context:
- Client: {clarification_data.get('client_name', 'Valued Client')}
- Project: {clarification_data.get('project_title', 'Market Research Project')}

The email should be:
- Professional and client-appropriate
- Clear and specific questions
- Explain why clarification is needed
- Provide reasonable response timeline

Return JSON with "subject" and "body" fields.
"""

        response = await self.generate_text(prompt, temperature=0.3)
        # Parse JSON response
        import json
        try:
            return json.loads(response)
        except:
            return {
                "subject": f"Clarification Needed: {clarification_data.get('project_title', 'Project')}",
                "body": f"We need clarification on: {chr(10).join(questions)}"
            }

    async def _send_email_via_smtp(self, email_msg: EmailMessage) -> None:
        """Send email via SMTP."""
        msg = MIMEMultipart()
        msg['From'] = f"{email_msg.from_name} <{email_msg.from_email}>"
        msg['To'] = email_msg.to_email
        msg['Subject'] = email_msg.subject

        if email_msg.thread_id:
            msg['Message-ID'] = f"<{email_msg.thread_id}@{settings.smtp_server}>"
            if email_msg.metadata.get("parent_message_id"):
                msg['In-Reply-To'] = email_msg.metadata["parent_message_id"]
                msg['References'] = email_msg.metadata["parent_message_id"]

        # Add body
        msg.attach(MIMEText(email_msg.body, 'html'))

        # Add attachments
        for attachment in email_msg.attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment["filename"]}"')
            msg.attach(part)

        # Send via SMTP
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
        server.quit()

    async def _fetch_new_emails(self) -> List[Dict[str, Any]]:
        """Fetch new emails from IMAP."""
        messages = []

        try:
            with MailBox(settings.imap_server).login(
                settings.imap_username,
                settings.imap_password
            ) as mailbox:

                # Get unseen messages
                for msg in mailbox.fetch(AND(seen=False), mark_seen=False):
                    messages.append({
                        'uid': msg.uid,
                        'subject': msg.subject,
                        'from': msg.from_,
                        'to': msg.to,
                        'date': msg.date,
                        'text': msg.text,
                        'html': msg.html,
                        'headers': dict(msg.headers),
                        'attachments': [{'filename': att.filename, 'content': att.payload} for att in msg.attachments]
                    })

        except Exception as e:
            self.logger.error(f"Failed to fetch emails: {str(e)}")

        return messages

    async def _parse_email_content(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse email content using LLM."""
        content = email_data.get('text', '') or email_data.get('html', '')

        prompt = f"""
Parse this email response and extract structured information.

Email content:
{content}

Return JSON with:
- sender_email: email address
- answers: any answers provided (if clarification request)
- validation_response: yes/no/maybe with confidence (if validation request)
- additional_notes: any other relevant information
"""

        response = await self.generate_text(prompt, temperature=0.1)
        # Parse JSON response
        import json
        try:
            return json.loads(response)
        except:
            return {"raw_content": content}

    def _extract_thread_id(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract thread ID from email headers."""
        headers = email_data.get('headers', {})

        # Check Message-ID and References
        message_id = headers.get('Message-ID', '')
        references = headers.get('References', '')

        # Simple thread ID extraction - in production, use more sophisticated logic
        if message_id and '@' in message_id:
            return message_id.split('@')[0].strip('<>')

        return None

    async def _is_duplicate_email(self, email_msg: EmailMessage) -> bool:
        """Check if this email is a duplicate."""
        key = f"email_sent:{email_msg.to_email}:{hash(email_msg.subject + email_msg.body) % 10000}"
        return bool(self.redis.exists(key))

    async def _mark_email_sent(self, email_msg: EmailMessage) -> None:
        """Mark email as sent for deduplication."""
        key = f"email_sent:{email_msg.to_email}:{hash(email_msg.subject + email_msg.body) % 10000}"
        self.redis.setex(key, settings.email_deduplication_ttl, "1")

    async def _track_thread(self, email_msg: EmailMessage) -> None:
        """Track email thread in Redis."""
        if not email_msg.thread_id:
            return

        thread_key = f"thread:{email_msg.thread_id}"
        thread_data = {
            "thread_id": email_msg.thread_id,
            "subject": email_msg.subject,
            "participants": [email_msg.to_email],
            "last_message_at": datetime.utcnow().isoformat(),
            "status": "active",
            "awaiting_response": True,
            "metadata": email_msg.metadata
        }

        self.redis.set(thread_key, json.dumps(thread_data))

    async def _get_thread(self, thread_id: str) -> Optional[EmailThread]:
        """Get thread information from Redis."""
        thread_key = f"thread:{thread_id}"
        data = self.redis.get(thread_key)

        if data:
            import json
            thread_dict = json.loads(data)
            return EmailThread(**thread_dict)

        return None

    async def _update_thread_status(self, thread_id: str, status: str) -> None:
        """Update thread status."""
        thread = await self._get_thread(thread_id)
        if thread:
            thread.status = status
            thread.awaiting_response = False
            thread.last_message_at = datetime.utcnow()

            thread_key = f"thread:{thread_id}"
            self.redis.set(thread_key, thread.model_dump_json())
