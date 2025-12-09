"""Resource tools for accessing company data from Google Sheets."""

import json
from typing import Any, Optional

from langchain.tools import tool

from proposal_bot.config import get_settings
from proposal_bot.schemas.resource import StaffMember, Vendor
from proposal_bot.services.google_sheets import GoogleSheetsService


def create_resource_tools() -> list[Any]:
    """
    Create tools for accessing resource data from Google Sheets.

    Returns:
        List of resource tools for agents to use.
    """
    settings = get_settings()
    sheets_service = GoogleSheetsService()

    @tool
    def search_staff_by_skills(search_criteria: str) -> list[dict[str, Any]]:
        """
        Search for staff members by skills and criteria.

        Args:
            search_criteria: JSON string containing:
                - skills: List of required skills
                - seniority_level: Optional seniority filter (junior/mid/senior/principal/director)
                - availability_threshold: Minimum availability required (0-1)

        Returns:
            List of matching staff members with their details
        """
        # Parse the JSON string input
        try:
            if isinstance(search_criteria, str):
                search_criteria = search_criteria.strip()
                search_criteria = json.loads(search_criteria)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {search_criteria[:200]}..."

        skills = search_criteria.get("skills", [])
        seniority_level = search_criteria.get("seniority_level")
        availability_threshold = search_criteria.get("availability_threshold", 0.2)

        # Read staff profiles from Google Sheets
        staff_data = sheets_service.read_sheet(
            spreadsheet_id=settings.staff_profiles_sheet_id,
            range_name="Staff!A2:Z1000",  # Adjust range as needed
        )

        matching_staff = []

        # Parse and filter staff data
        for row in staff_data:
            if not row or len(row) < 10:
                continue

            try:
                # Parse staff data (adjust column indices based on your sheet structure)
                staff = {
                    "id": row[0],
                    "name": row[1],
                    "title": row[2],
                    "department": row[3],
                    "seniority_level": row[4],
                    "skills": row[5].split(",") if len(row) > 5 and row[5] else [],
                    "methodologies": row[6].split(",") if len(row) > 6 and row[6] else [],
                    "hourly_rate": float(row[7]) if len(row) > 7 and row[7] else 0,
                    "current_utilization": float(row[8]) if len(row) > 8 and row[8] else 0,
                    "can_lead_projects": row[9].lower() == "true" if len(row) > 9 else False,
                }

                # Calculate availability
                staff["availability"] = 1.0 - staff["current_utilization"]

                # Filter by criteria
                if seniority_level and staff["seniority_level"] != seniority_level:
                    continue

                if staff["availability"] < availability_threshold:
                    continue

                # Check if staff has required skills
                staff_skills_lower = [s.strip().lower() for s in staff["skills"]]
                required_skills_lower = [s.strip().lower() for s in skills]

                matching_skills = [
                    skill for skill in required_skills_lower if skill in staff_skills_lower
                ]

                if matching_skills:
                    staff["matching_skills"] = matching_skills
                    staff["match_score"] = len(matching_skills) / len(required_skills_lower)
                    matching_staff.append(staff)

            except (IndexError, ValueError) as e:
                # Skip malformed rows
                continue

        # Sort by match score and availability
        matching_staff.sort(
            key=lambda x: (x.get("match_score", 0), x.get("availability", 0)),
            reverse=True,
        )

        return matching_staff

    @tool
    def search_vendors_by_service(search_criteria: str) -> list[dict[str, Any]]:
        """
        Search for vendors by service type and criteria.

        Args:
            search_criteria: JSON string containing:
                - services: List of required services
                - geographic_region: Optional geographic region filter
                - min_quality_rating: Minimum quality rating required (1-5)

        Returns:
            List of matching vendors with their details
        """
        # Parse the JSON string input
        try:
            if isinstance(search_criteria, str):
                search_criteria = search_criteria.strip()
                search_criteria = json.loads(search_criteria)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {search_criteria[:200]}..."

        services = search_criteria.get("services", [])
        geographic_region = search_criteria.get("geographic_region")
        min_quality_rating = search_criteria.get("min_quality_rating", 3.5)

        # Read vendor data from Google Sheets
        vendor_data = sheets_service.read_sheet(
            spreadsheet_id=settings.vendor_relationships_sheet_id,
            range_name="Vendors!A2:Z1000",
        )

        matching_vendors = []

        for row in vendor_data:
            if not row or len(row) < 8:
                continue

            try:
                vendor = {
                    "id": row[0],
                    "name": row[1],
                    "company_name": row[2],
                    "contact_email": row[3],
                    "services": row[4].split(",") if len(row) > 4 and row[4] else [],
                    "geographic_coverage": row[5].split(",") if len(row) > 5 and row[5] else [],
                    "pricing_model": row[6] if len(row) > 6 else "per_complete",
                    "base_rate": float(row[7]) if len(row) > 7 and row[7] else 0,
                    "quality_rating": float(row[8]) if len(row) > 8 and row[8] else 0,
                    "relationship_status": row[9] if len(row) > 9 else "approved",
                }

                # Filter by quality rating
                if vendor["quality_rating"] < min_quality_rating:
                    continue

                # Filter by geographic region if specified
                if geographic_region:
                    coverage_lower = [r.strip().lower() for r in vendor["geographic_coverage"]]
                    if geographic_region.lower() not in coverage_lower:
                        continue

                # Check if vendor provides required services
                vendor_services_lower = [s.strip().lower() for s in vendor["services"]]
                required_services_lower = [s.strip().lower() for s in services]

                matching_services = [
                    svc for svc in required_services_lower if svc in vendor_services_lower
                ]

                if matching_services:
                    vendor["matching_services"] = matching_services
                    vendor["match_score"] = len(matching_services) / len(required_services_lower)
                    matching_vendors.append(vendor)

            except (IndexError, ValueError):
                continue

        # Sort by match score and quality rating
        matching_vendors.sort(
            key=lambda x: (x.get("match_score", 0), x.get("quality_rating", 0)),
            reverse=True,
        )

        return matching_vendors

    @tool
    def get_staff_member(request_data: str) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a specific staff member.

        Args:
            request_data: JSON string containing:
                - staff_id: Staff member ID

        Returns:
            Staff member details or None if not found
        """
        # Parse the JSON string input
        try:
            if isinstance(request_data, str):
                request_data = request_data.strip()
                request_data = json.loads(request_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {request_data[:200]}..."

        staff_id = request_data.get("staff_id")

        staff_data = sheets_service.read_sheet(
            spreadsheet_id=settings.staff_profiles_sheet_id,
            range_name="Staff!A2:Z1000",
        )

        for row in staff_data:
            if row and row[0] == staff_id:
                try:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "title": row[2],
                        "department": row[3],
                        "seniority_level": row[4],
                        "skills": row[5].split(",") if len(row) > 5 and row[5] else [],
                        "methodologies": row[6].split(",") if len(row) > 6 and row[6] else [],
                        "hourly_rate": float(row[7]) if len(row) > 7 and row[7] else 0,
                        "internal_cost": float(row[8]) if len(row) > 8 and row[8] else 0,
                        "current_utilization": float(row[9]) if len(row) > 9 and row[9] else 0,
                        "can_lead_projects": row[10].lower() == "true" if len(row) > 10 else False,
                        "email": row[11] if len(row) > 11 else "",
                        "availability": 1.0 - float(row[9]) if len(row) > 9 and row[9] else 1.0,
                    }
                except (IndexError, ValueError):
                    return None

        return None

    @tool
    def get_vendor(request_data: str) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a specific vendor.

        Args:
            request_data: JSON string containing:
                - vendor_id: Vendor ID

        Returns:
            Vendor details or None if not found
        """
        # Parse the JSON string input
        try:
            if isinstance(request_data, str):
                request_data = request_data.strip()
                request_data = json.loads(request_data)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input: {str(e)} - Input: {request_data[:200]}..."

        vendor_id = request_data.get("vendor_id")

        vendor_data = sheets_service.read_sheet(
            spreadsheet_id=settings.vendor_relationships_sheet_id,
            range_name="Vendors!A2:Z1000",
        )

        for row in vendor_data:
            if row and row[0] == vendor_id:
                try:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "company_name": row[2],
                        "contact_person": row[3],
                        "contact_email": row[4],
                        "services": row[5].split(",") if len(row) > 5 and row[5] else [],
                        "specializations": row[6].split(",") if len(row) > 6 and row[6] else [],
                        "geographic_coverage": row[7].split(",") if len(row) > 7 and row[7] else [],
                        "pricing_model": row[8] if len(row) > 8 else "per_complete",
                        "base_rate": float(row[9]) if len(row) > 9 and row[9] else 0,
                        "quality_rating": float(row[10]) if len(row) > 10 and row[10] else 0,
                        "relationship_status": row[11] if len(row) > 11 else "approved",
                    }
                except (IndexError, ValueError):
                    return None

        return None

    @tool
    def get_pricing_by_service(request_data: str) -> Optional[dict[str, Any]]:
        """
        Get standard pricing information for a service type.

        Args:
            service_type: Type of service (e.g., "online_survey", "phone_interview")

        Returns:
            Pricing details or None if not found
        """
        pricing_data = sheets_service.read_sheet(
            spreadsheet_id=settings.pricing_sheet_id,
            range_name="Pricing!A2:Z1000",
        )

        for row in pricing_data:
            if row and len(row) >= 3:
                if row[0].lower().strip() == service_type.lower().strip():
                    try:
                        return {
                            "service_type": row[0],
                            "base_price": float(row[1]) if row[1] else 0,
                            "unit": row[2],
                            "markup_percentage": float(row[3]) if len(row) > 3 and row[3] else 30,
                            "volume_discounts": json.loads(row[4])
                            if len(row) > 4 and row[4]
                            else {},
                        }
                    except (ValueError, json.JSONDecodeError):
                        return None

        return None

    return [
        search_staff_by_skills,
        search_vendors_by_service,
        get_staff_member,
        get_vendor,
        get_pricing_by_service,
    ]
