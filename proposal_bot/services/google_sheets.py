"""Google Sheets service for accessing company data."""

from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from proposal_bot.config import get_settings


class GoogleSheetsService:
    """Service for interacting with Google Sheets API."""

    def __init__(self) -> None:
        """Initialize Google Sheets service."""
        self.settings = get_settings()
        self._service: Optional[Any] = None

    def _get_service(self) -> Any:
        """Get or create Google Sheets API service."""
        if self._service is not None:
            return self._service

        # Create credentials from settings
        creds = Credentials(
            token=None,
            refresh_token=self.settings.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
        )

        # Refresh the token if needed
        if not creds.valid:
            creds.refresh(Request())

        # Build the service
        self._service = build("sheets", "v4", credentials=creds)
        return self._service

    def read_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
    ) -> list[list[Any]]:
        """
        Read data from a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to read (e.g., "Sheet1!A1:D10")

        Returns:
            List of rows, where each row is a list of cell values
        """
        service = self._get_service()

        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheet_id=spreadsheet_id, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        return values

    def write_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
    ) -> dict[str, Any]:
        """
        Write data to a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to write
            values: List of rows to write

        Returns:
            API response dictionary
        """
        service = self._get_service()

        body = {"values": values}

        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheet_id=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )

        return result

    def append_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
    ) -> dict[str, Any]:
        """
        Append data to a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to append to
            values: List of rows to append

        Returns:
            API response dictionary
        """
        service = self._get_service()

        body = {"values": values}

        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheet_id=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )

        return result
