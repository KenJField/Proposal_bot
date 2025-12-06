"""Email tools using LangChain Gmail integration."""

from typing import Any

from langchain.tools import tool
from langchain_google_community.gmail.create_draft import GmailCreateDraft
from langchain_google_community.gmail.get_message import GmailGetMessage
from langchain_google_community.gmail.get_thread import GmailGetThread
from langchain_google_community.gmail.search import GmailSearch
from langchain_google_community.gmail.send_message import GmailSendMessage
from langchain_google_community.gmail.toolkit import GmailToolkit


def create_gmail_tools() -> list[Any]:
    """
    Create Gmail tools for email communication.

    Returns:
        List of Gmail tools for agents to use.
    """
    # Initialize the Gmail toolkit
    # This will use the Google credentials configured in settings
    toolkit = GmailToolkit()

    # Get the standard Gmail tools
    gmail_tools = toolkit.get_tools()

    # Add custom email tools specific to our use case
    @tool
    def send_validation_email(
        recipient: str,
        subject: str,
        body: str,
        project_id: str,
        resource_id: str,
    ) -> dict[str, Any]:
        """
        Send a validation email to a resource manager.

        Args:
            recipient: Email address of the recipient
            subject: Email subject line
            body: Email body content (can include HTML)
            project_id: Associated project ID
            resource_id: Resource being validated

        Returns:
            Dictionary with email metadata including message_id and thread_id
        """
        # Use GmailSendMessage from the toolkit
        send_tool = GmailSendMessage()

        # Format the email with tracking metadata
        full_body = f"{body}\n\n---\nProject ID: {project_id}\nResource ID: {resource_id}"

        result = send_tool.run(
            {
                "to": [recipient],
                "subject": subject,
                "message": full_body,
            }
        )

        return {
            "status": "sent",
            "recipient": recipient,
            "subject": subject,
            "project_id": project_id,
            "resource_id": resource_id,
            "result": result,
        }

    @tool
    def send_clarification_email(
        recipient: str,
        subject: str,
        questions: list[str],
        brief_id: str,
    ) -> dict[str, Any]:
        """
        Send a clarification email to a sales representative.

        Args:
            recipient: Email address of the sales rep
            subject: Email subject line
            questions: List of clarification questions
            brief_id: Associated brief ID

        Returns:
            Dictionary with email metadata
        """
        send_tool = GmailSendMessage()

        # Format questions as a numbered list
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])

        body = f"""
Dear Sales Representative,

We're reviewing the brief for the following project and need some clarifications to prepare an accurate proposal.

Please provide answers to the following questions:

{questions_text}

Please respond at your earliest convenience so we can move forward with the proposal.

Best regards,
Proposal Bot

---
Brief ID: {brief_id}
        """.strip()

        result = send_tool.run(
            {
                "to": [recipient],
                "subject": subject,
                "message": body,
            }
        )

        return {
            "status": "sent",
            "recipient": recipient,
            "subject": subject,
            "brief_id": brief_id,
            "questions_count": len(questions),
            "result": result,
        }

    @tool
    def send_lead_validation_email(
        recipient: str,
        project_lead_name: str,
        project_summary: str,
        design_questions: list[str],
        project_id: str,
    ) -> dict[str, Any]:
        """
        Send project design validation email to proposed project lead.

        Args:
            recipient: Email address of the project lead
            project_lead_name: Name of the project lead
            project_summary: Summary of the project
            design_questions: List of design questions for validation
            project_id: Associated project ID

        Returns:
            Dictionary with email metadata
        """
        send_tool = GmailSendMessage()

        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(design_questions)])

        body = f"""
Dear {project_lead_name},

You have been identified as the ideal project lead for the following research project:

{project_summary}

Before finalizing the proposal, we'd like your input on the following design decisions:

{questions_text}

Your expertise will help ensure we deliver the best possible proposal to the client.

Please review and respond with your feedback at your earliest convenience.

Best regards,
Proposal Bot

---
Project ID: {project_id}
        """.strip()

        result = send_tool.run(
            {
                "to": [recipient],
                "subject": f"Project Design Review Request - {project_id}",
                "message": body,
            }
        )

        return {
            "status": "sent",
            "recipient": recipient,
            "project_lead": project_lead_name,
            "project_id": project_id,
            "questions_count": len(design_questions),
            "result": result,
        }

    @tool
    def search_emails_by_project(
        project_id: str,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Search for all emails related to a specific project.

        Args:
            project_id: Project ID to search for
            max_results: Maximum number of results to return

        Returns:
            List of email message summaries
        """
        search_tool = GmailSearch()

        # Search for emails containing the project ID
        query = f"Project ID: {project_id}"

        results = search_tool.run(
            {
                "query": query,
                "max_results": max_results,
            }
        )

        return results

    @tool
    def get_email_thread(thread_id: str) -> dict[str, Any]:
        """
        Get all messages in an email thread.

        Args:
            thread_id: Gmail thread ID

        Returns:
            Dictionary containing thread messages
        """
        thread_tool = GmailGetThread()
        return thread_tool.run({"thread_id": thread_id})

    # Combine standard Gmail tools with our custom tools
    all_tools = gmail_tools + [
        send_validation_email,
        send_clarification_email,
        send_lead_validation_email,
        search_emails_by_project,
        get_email_thread,
    ]

    return all_tools
