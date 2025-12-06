"""Email Agent for handling all email communication."""

import asyncio
import email
import imaplib
import json
import logging
import os
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..core.redis_client import get_redis_client

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.redis = get_redis_client()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize Jinja2 template environment
        template_dir = Path(__file__).parent / "templates"
        template_dir.mkdir(exist_ok=True)

        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

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
        """Generate validation request email using template."""
        try:
            template = self.template_env.get_template('validation_request.html')

            # Prepare template variables
            template_vars = {
                'recipient_name': validation_data.get('recipient_name', ''),
                'question': validation_data.get('question', ''),
                'project_title': validation_data.get('project_title', 'Market Research Project'),
                'urgency': validation_data.get('priority', 'medium'),
                'deadline_hours': validation_data.get('deadline_hours', 72)
            }

            # Render HTML body
            html_body = template.render(**template_vars)

            # Generate subject
            subject = f"Capability Validation Request - {validation_data.get('project_title', 'Market Research Project')}"

            return {
                "subject": subject,
                "body": html_body
            }

        except Exception as e:
            self.logger.error(f"Template rendering failed: {e}")
            # Fallback to simple text
            return {
                "subject": f"Validation Request: {validation_data.get('attribute_path', 'Capability')}",
                "body": f"Please validate: {validation_data.get('question', 'Unknown question')}"
            }

    async def _generate_clarification_email(self, clarification_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate clarification request email using template."""
        try:
            template = self.template_env.get_template('clarification_request.html')

            # Prepare template variables
            template_vars = {
                'client_name': clarification_data.get('client_name', 'Valued Client'),
                'questions': clarification_data.get('questions', []),
                'project_title': clarification_data.get('project_title', 'Market Research Project'),
                'urgency': clarification_data.get('urgency', 'normal'),
                'deadline_hours': clarification_data.get('deadline_hours', 72),
                'company_name': 'Market Research Solutions',  # Could be configurable
                'reply_email': settings.smtp_username,
                'phone': '(555) 123-4567'  # Could be configurable
            }

            # Render HTML body
            html_body = template.render(**template_vars)

            # Generate subject
            subject = f"Clarification Request - {clarification_data.get('project_title', 'Market Research Proposal')}"

            return {
                "subject": subject,
                "body": html_body
            }

        except Exception as e:
            self.logger.error(f"Template rendering failed: {e}")
            # Fallback to simple text
            questions = clarification_data.get("questions", [])
            return {
                "subject": f"Clarification Needed: {clarification_data.get('project_title', 'Project')}",
                "body": f"We need clarification on: {chr(10).join(str(q) for q in questions)}"
            }

    async def _send_email_via_smtp(self, email_msg: EmailMessage) -> None:
        """Send email via SMTP with retry logic and proper error handling."""
        import asyncio

        msg = MIMEMultipart()
        msg['From'] = f"{email_msg.from_name} <{email_msg.from_email}>"
        msg['To'] = email_msg.to_email
        msg['Subject'] = email_msg.subject

        if email_msg.thread_id:
            msg['Message-ID'] = f"<{email_msg.thread_id}@{settings.smtp_server}>"
            if email_msg.metadata.get("parent_message_id"):
                msg['In-Reply-To'] = email_msg.metadata["parent_message_id"]
                msg['References'] = email_msg.metadata["parent_message_id"]

        # Add body - check if it's HTML or plain text
        if '<html' in email_msg.body.lower() or '<body' in email_msg.body.lower():
            msg.attach(MIMEText(email_msg.body, 'html'))
        else:
            msg.attach(MIMEText(email_msg.body, 'plain'))

        # Add attachments
        for attachment in email_msg.attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment["filename"]}"')
            msg.attach(part)

        # Send via SMTP with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use asyncio.to_thread for synchronous SMTP operations
                await asyncio.to_thread(self._smtp_send_sync, msg)
                self.logger.info(f"Email sent successfully to {email_msg.to_email}")
                return

            except Exception as e:
                self.logger.warning(f"SMTP attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to send email after {max_retries} attempts: {e}")

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

    def _smtp_send_sync(self, msg) -> None:
        """Synchronous SMTP sending (called via asyncio.to_thread)."""
        try:
            server = smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30)
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
            server.quit()
        except smtplib.SMTPException as e:
            raise Exception(f"SMTP error: {e}")
        except Exception as e:
            raise Exception(f"Connection error: {e}")

    async def _fetch_new_emails(self) -> List[Dict[str, Any]]:
        """Fetch new emails from IMAP with proper error handling."""
        import asyncio

        messages = []

        try:
            # Use asyncio.to_thread for synchronous IMAP operations
            raw_messages = await asyncio.to_thread(self._imap_fetch_sync)

            # Process and format messages
            for msg_data in raw_messages:
                try:
                    processed_msg = await self._process_raw_email(msg_data)
                    if processed_msg:
                        messages.append(processed_msg)
                except Exception as e:
                    self.logger.error(f"Failed to process email {msg_data.get('uid')}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to fetch emails: {str(e)}")
            # Don't return empty list - log the error but don't fail silently
            raise Exception(f"IMAP fetch failed: {e}")

        return messages

    def _imap_fetch_sync(self) -> List[Dict[str, Any]]:
        """Synchronous IMAP fetching (called via asyncio.to_thread)."""
        messages = []

        try:
            with MailBox(settings.imap_server).login(
                settings.imap_username,
                settings.imap_password
            ) as mailbox:

                # Get unseen messages from INBOX
                criteria = AND(seen=False)
                for msg in mailbox.fetch(criteria, mark_seen=False):
                    messages.append({
                        'uid': msg.uid,
                        'subject': msg.subject or "",
                        'from': msg.from_ or "",
                        'to': msg.to or [],
                        'date': msg.date,
                        'text': msg.text or "",
                        'html': msg.html or "",
                        'headers': dict(msg.headers) if msg.headers else {},
                        'attachments': [{
                            'filename': att.filename,
                            'content': att.payload,
                            'content_type': att.content_type
                        } for att in msg.attachments] if msg.attachments else []
                    })

        except Exception as e:
            raise Exception(f"IMAP connection error: {e}")

        return messages

    async def _process_raw_email(self, msg_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and validate raw email data."""
        # Extract thread information from headers
        headers = msg_data.get('headers', {})
        message_id = headers.get('Message-ID', '')
        references = headers.get('References', '')

        # Only process emails that might be relevant (contain thread info or specific keywords)
        thread_id = self._extract_thread_id_from_headers(headers)

        if not thread_id and not self._is_relevant_email(msg_data):
            return None

        # Mark as processed to avoid reprocessing
        await self._mark_email_processed(msg_data['uid'])

        return {
            'uid': msg_data['uid'],
            'subject': msg_data['subject'],
            'sender': msg_data['from'],
            'recipients': msg_data['to'],
            'date': msg_data['date'],
            'text_body': msg_data['text'],
            'html_body': msg_data['html'],
            'headers': headers,
            'attachments': msg_data['attachments'],
            'thread_id': thread_id,
            'processed_at': datetime.utcnow().isoformat()
        }

    def _extract_thread_id_from_headers(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract thread ID from email headers."""
        # Check Message-ID and References for our thread IDs
        message_id = headers.get('Message-ID', '')
        references = headers.get('References', '')

        # Look for our generated thread IDs in the format <thread_id@server>
        if '@' in message_id:
            potential_id = message_id.split('@')[0].strip('<>')
            if len(potential_id) == 36:  # UUID length
                return potential_id

        # Check references header
        if references:
            for ref in references.split():
                ref = ref.strip('<>')
                if '@' in ref and len(ref.split('@')[0]) == 36:
                    return ref.split('@')[0]

        return None

    def _is_relevant_email(self, msg_data: Dict[str, Any]) -> bool:
        """Check if email is relevant for processing."""
        subject = msg_data.get('subject', '').lower()
        text_body = msg_data.get('text', '').lower()

        # Keywords that indicate relevant emails
        relevant_keywords = [
            'validation', 'confirm', 'availability', 'capability',
            'proposal', 'rfp', 'research', 'methodology',
            'yes', 'no', 'available', 'unavailable'
        ]

        return any(keyword in subject or keyword in text_body for keyword in relevant_keywords)

    async def _mark_email_processed(self, uid: str) -> None:
        """Mark email as processed to avoid duplicate processing."""
        key = f"processed_email:{uid}"
        await self.redis.setex(key, 86400, "1")  # Keep for 24 hours

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
        exists = await self.redis.exists(key)
        return bool(exists)

    async def _mark_email_sent(self, email_msg: EmailMessage) -> None:
        """Mark email as sent for deduplication."""
        key = f"email_sent:{email_msg.to_email}:{hash(email_msg.subject + email_msg.body) % 10000}"
        await self.redis.setex(key, settings.email_deduplication_ttl, "1")

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

        await self.redis.set(thread_key, json.dumps(thread_data))

    async def _get_thread(self, thread_id: str) -> Optional[EmailThread]:
        """Get thread information from Redis."""
        thread_key = f"thread:{thread_id}"
        data = await self.redis.get(thread_key)

        if data:
            thread_dict = json.loads(data.decode())
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
            await self.redis.set(thread_key, thread.model_dump_json())
