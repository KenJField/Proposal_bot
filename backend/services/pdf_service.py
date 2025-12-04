"""
Service for generating PDF proposals from proposal content.
"""

import logging
from typing import Optional
from datetime import datetime
import os
from jinja2 import Template
from weasyprint import HTML
import tempfile

from models.schemas import ProposalContent

logger = logging.getLogger(__name__)


# HTML template for proposal
PROPOSAL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ client_name }} - Research Proposal</title>
    <style>
        @page {
            size: Letter;
            margin: 1in;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }

        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            font-size: 11pt;
        }

        h1 {
            color: #1a5490;
            font-size: 24pt;
            margin-bottom: 0.5em;
            border-bottom: 3px solid #1a5490;
            padding-bottom: 0.3em;
        }

        h2 {
            color: #1a5490;
            font-size: 18pt;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            border-bottom: 1px solid #ccc;
            padding-bottom: 0.2em;
        }

        h3 {
            color: #2c6aa0;
            font-size: 14pt;
            margin-top: 1em;
            margin-bottom: 0.3em;
        }

        .cover-page {
            text-align: center;
            padding-top: 3in;
            page-break-after: always;
        }

        .cover-title {
            font-size: 32pt;
            font-weight: bold;
            color: #1a5490;
            margin-bottom: 0.5em;
        }

        .cover-subtitle {
            font-size: 18pt;
            color: #666;
            margin-bottom: 2em;
        }

        .cover-info {
            font-size: 12pt;
            color: #666;
            margin-top: 3em;
        }

        .section {
            margin-bottom: 2em;
            page-break-inside: avoid;
        }

        .phase {
            background-color: #f8f9fa;
            border-left: 4px solid #1a5490;
            padding: 1em;
            margin: 1em 0;
            page-break-inside: avoid;
        }

        .phase-title {
            font-weight: bold;
            color: #1a5490;
            margin-bottom: 0.5em;
        }

        .team-member {
            background-color: #f8f9fa;
            padding: 1em;
            margin: 0.5em 0;
            border-radius: 5px;
            page-break-inside: avoid;
        }

        .team-name {
            font-weight: bold;
            color: #1a5490;
            font-size: 12pt;
        }

        .team-role {
            color: #666;
            font-style: italic;
            margin-bottom: 0.5em;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }

        th {
            background-color: #1a5490;
            color: white;
            padding: 0.5em;
            text-align: left;
        }

        td {
            padding: 0.5em;
            border-bottom: 1px solid #ddd;
        }

        .pricing-total {
            font-weight: bold;
            font-size: 12pt;
            text-align: right;
            margin-top: 1em;
        }

        ul {
            margin: 0.5em 0;
            padding-left: 1.5em;
        }

        li {
            margin: 0.3em 0;
        }

        .highlight {
            background-color: #fff9e6;
            padding: 1em;
            border-left: 4px solid #ffc107;
            margin: 1em 0;
        }
    </style>
</head>
<body>
    <!-- Cover Page -->
    <div class="cover-page">
        <div class="cover-title">Research Proposal</div>
        <div class="cover-subtitle">{{ client_name }}</div>
        <div class="cover-subtitle">{{ project_title }}</div>
        <div class="cover-info">
            <p><strong>Prepared by:</strong> Research Solutions Group</p>
            <p><strong>Date:</strong> {{ date }}</p>
        </div>
    </div>

    <!-- Executive Summary -->
    <div class="section">
        <h1>Executive Summary</h1>
        <p>{{ executive_summary }}</p>
    </div>

    <!-- Understanding of Needs -->
    <div class="section">
        <h1>Understanding of Your Needs</h1>
        <p>{{ understanding_of_needs }}</p>
    </div>

    <!-- Proposed Methodology -->
    <div class="section">
        <h1>Proposed Methodology</h1>

        <h2>Overview</h2>
        <p>{{ methodology.overview }}</p>

        <h2>Detailed Approach</h2>
        <p>{{ methodology.approach }}</p>

        <h2>Project Phases</h2>
        {% for phase in methodology.phases %}
        <div class="phase">
            <div class="phase-title">{{ phase.name }} ({{ phase.duration_weeks }} weeks)</div>
            <p>{{ phase.description }}</p>
            <p><strong>Deliverables:</strong></p>
            <ul>
                {% for deliverable in phase.deliverables %}
                <li>{{ deliverable }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endfor %}
    </div>

    <!-- Timeline -->
    <div class="section">
        <h1>Project Timeline</h1>
        <p><strong>Total Duration:</strong> {{ timeline.total_duration_weeks }} weeks</p>

        {% if timeline.milestones %}
        <h2>Key Milestones</h2>
        <ul>
            {% for milestone in timeline.milestones %}
            <li><strong>{{ milestone.date }}:</strong> {{ milestone.milestone }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>

    <!-- Project Team -->
    <div class="section">
        <h1>Project Team</h1>
        {% for member in team %}
        <div class="team-member">
            <div class="team-name">{{ member.name }}</div>
            <div class="team-role">{{ member.role }} - {{ member.hours_allocated }} hours</div>
            <p>{{ member.bio }}</p>
        </div>
        {% endfor %}
    </div>

    <!-- Pricing -->
    <div class="section">
        <h1>Investment</h1>
        <table>
            <thead>
                <tr>
                    <th>Description</th>
                    <th style="text-align: center;">Quantity</th>
                    <th style="text-align: right;">Unit Cost</th>
                    <th style="text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {% for item in pricing.line_items %}
                <tr>
                    <td>{{ item.description }}</td>
                    <td style="text-align: center;">{{ item.quantity }}</td>
                    <td style="text-align: right;">${{ "%.2f"|format(item.unit_cost) }}</td>
                    <td style="text-align: right;">${{ "%.2f"|format(item.total) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="pricing-total">
            <p>Subtotal: ${{ "%.2f"|format(pricing.subtotal) }}</p>
            {% if pricing.tax > 0 %}
            <p>Tax: ${{ "%.2f"|format(pricing.tax) }}</p>
            {% endif %}
            <p style="font-size: 14pt; color: #1a5490;">Total Investment: ${{ "%.2f"|format(pricing.total) }} {{ pricing.currency }}</p>
        </div>
    </div>

    <!-- Why Choose Us -->
    <div class="section">
        <h1>Why Choose Us</h1>
        <div class="highlight">
            <p>{{ why_us }}</p>
        </div>
    </div>
</body>
</html>
"""


class PDFService:
    """Service for generating PDF proposals."""

    def __init__(self):
        """Initialize PDF service."""
        self.template = Template(PROPOSAL_TEMPLATE)

    def generate_pdf(
        self,
        proposal: ProposalContent,
        client_name: str = "Valued Client",
        project_title: str = "Research Project",
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate PDF from proposal content.

        Args:
            proposal: Proposal content
            client_name: Client name for cover page
            project_title: Project title for cover page
            output_path: Optional output path. If None, creates temp file.

        Returns:
            Path to generated PDF file
        """
        logger.info(f"Generating PDF for {client_name}")

        try:
            # Prepare template data
            template_data = {
                "client_name": client_name,
                "project_title": project_title,
                "date": datetime.now().strftime("%B %d, %Y"),
                "executive_summary": proposal.executive_summary,
                "understanding_of_needs": proposal.understanding_of_needs,
                "methodology": {
                    "overview": proposal.proposed_methodology.overview,
                    "approach": proposal.proposed_methodology.approach,
                    "phases": [
                        {
                            "name": phase.name,
                            "duration_weeks": phase.duration_weeks,
                            "description": phase.description,
                            "deliverables": phase.deliverables,
                        }
                        for phase in proposal.proposed_methodology.phases
                    ],
                },
                "timeline": {
                    "total_duration_weeks": proposal.timeline.total_duration_weeks,
                    "milestones": proposal.timeline.milestones,
                },
                "team": [
                    {
                        "name": member.name,
                        "role": member.role,
                        "bio": member.bio,
                        "hours_allocated": member.hours_allocated,
                    }
                    for member in proposal.team
                ],
                "pricing": {
                    "line_items": [
                        {
                            "description": item.description,
                            "quantity": item.quantity,
                            "unit_cost": item.unit_cost,
                            "total": item.total,
                        }
                        for item in proposal.pricing.line_items
                    ],
                    "subtotal": proposal.pricing.subtotal,
                    "tax": proposal.pricing.tax,
                    "total": proposal.pricing.total,
                    "currency": proposal.pricing.currency,
                },
                "why_us": proposal.why_us,
            }

            # Render HTML
            html_content = self.template.render(**template_data)

            # Generate PDF
            if output_path is None:
                # Create temporary file
                fd, output_path = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)

            HTML(string=html_content).write_pdf(output_path)

            logger.info(f"PDF generated successfully: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise
