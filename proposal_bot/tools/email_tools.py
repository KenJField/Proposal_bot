"""Email tools using LangChain Gmail integration."""

from typing import Any

from langchain_google_community.gmail.toolkit import GmailToolkit


def create_gmail_tools() -> list[Any]:
    """
    Create Gmail tools for email communication using LangChain's Gmail toolkit.

    The toolkit provides these tools out of the box:
    - GmailCreateDraft: Create email drafts
    - GmailSendMessage: Send emails
    - GmailSearch: Search emails by query
    - GmailGetMessage: Get specific email messages
    - GmailGetThread: Get email thread conversations

    Returns:
        List of Gmail tools for agents to use.
    """
    # Initialize the Gmail toolkit
    # This will use credentials from credentials.json (or token.json if it exists)
    toolkit = GmailToolkit()

    # Get all Gmail tools from the toolkit
    # The toolkit handles authentication and provides ready-to-use tools
    gmail_tools = toolkit.get_tools()

    return gmail_tools
