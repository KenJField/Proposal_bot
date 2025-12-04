"""
Service for extracting requirements from RFP documents.
"""

import logging
from typing import Optional
import pypdf
import docx

from .llm_service import LLMService
from .prompts import REQUIREMENT_EXTRACTION_SYSTEM, get_extraction_prompt
from models.schemas import ExtractedRequirements

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for extracting structured requirements from RFPs."""

    def __init__(self):
        """Initialize the extraction service."""
        self.llm_service = LLMService()

    async def extract_from_text(self, text: str) -> ExtractedRequirements:
        """
        Extract requirements from plain text RFP.

        Args:
            text: Raw RFP text

        Returns:
            Extracted requirements
        """
        logger.info("Extracting requirements from text")

        prompt = get_extraction_prompt(text)

        response = await self.llm_service.generate_completion(
            prompt=prompt,
            system_prompt=REQUIREMENT_EXTRACTION_SYSTEM,
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=4000,
            response_format="json",
        )

        # Parse JSON response
        extracted_data = await self.llm_service.parse_json_response(response)

        # Validate and create ExtractedRequirements object
        requirements = ExtractedRequirements(**extracted_data)

        logger.info(
            f"Extraction completed with confidence: {requirements.extraction_confidence if hasattr(requirements, 'extraction_confidence') else 'N/A'}"
        )

        return requirements

    async def extract_from_pdf(self, pdf_path: str) -> ExtractedRequirements:
        """
        Extract requirements from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted requirements
        """
        logger.info(f"Extracting text from PDF: {pdf_path}")

        try:
            # Read PDF and extract text
            with open(pdf_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""

                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"

            if not text.strip():
                raise ValueError("No text could be extracted from PDF")

            logger.info(f"Extracted {len(text)} characters from PDF")

            # Extract requirements from text
            return await self.extract_from_text(text)

        except Exception as e:
            logger.error(f"Error extracting from PDF: {e}")
            raise

    async def extract_from_docx(self, docx_path: str) -> ExtractedRequirements:
        """
        Extract requirements from DOCX file.

        Args:
            docx_path: Path to DOCX file

        Returns:
            Extracted requirements
        """
        logger.info(f"Extracting text from DOCX: {docx_path}")

        try:
            # Read DOCX and extract text
            doc = docx.Document(docx_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            if not text.strip():
                raise ValueError("No text could be extracted from DOCX")

            logger.info(f"Extracted {len(text)} characters from DOCX")

            # Extract requirements from text
            return await self.extract_from_text(text)

        except Exception as e:
            logger.error(f"Error extracting from DOCX: {e}")
            raise

    async def extract_from_file(
        self, file_path: str, file_type: str
    ) -> ExtractedRequirements:
        """
        Extract requirements from file based on file type.

        Args:
            file_path: Path to file
            file_type: Type of file ('pdf', 'docx', 'txt')

        Returns:
            Extracted requirements
        """
        file_type = file_type.lower()

        if file_type == "pdf":
            return await self.extract_from_pdf(file_path)
        elif file_type in ["docx", "doc"]:
            return await self.extract_from_docx(file_path)
        elif file_type == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return await self.extract_from_text(text)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
