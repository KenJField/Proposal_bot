"""
Initialize database with sample data for development.
Run: python init_db.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from models.database import engine, SessionLocal, Base
from models.orm import User, Capability, Resource
from services.llm_service import LLMService
from utils.auth import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with tables and sample data."""

    logger.info("Initializing database...")

    # Create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    llm_service = LLMService()

    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.email == "admin@example.com").first()
        if existing_admin:
            logger.info("Admin user already exists. Skipping initialization.")
            return

        # Create sample user
        logger.info("Creating admin user...")
        admin_user = User(
            email="admin@example.com",
            full_name="Admin User",
            role="admin",
            hashed_password=hash_password("admin123"),
            is_active=True,
        )
        db.add(admin_user)
        db.commit()

        # Add sample capabilities
        logger.info("Adding sample capabilities...")
        capabilities_data = [
            {
                "category": "methodology",
                "name": "Online Quantitative Surveys",
                "description": "Web-based survey methodology using validated sampling techniques for consumer research",
                "detailed_description": "Our online quantitative survey approach leverages advanced sampling methodologies and sophisticated survey programming to ensure high-quality data collection. We utilize multiple quality control measures including attention checks, timing validations, and bot detection. Our panel partnerships provide access to diverse, representative samples across demographics and geographies.",
                "typical_duration_weeks": 4,
                "typical_cost_range": {"min": 15000, "max": 50000, "currency": "USD"},
                "complexity_level": "moderate",
                "tags": ["quantitative", "online", "survey", "b2c", "sampling"],
            },
            {
                "category": "methodology",
                "name": "In-Depth Interviews (IDIs)",
                "description": "One-on-one qualitative interviews for deep insights into customer motivations and behaviors",
                "detailed_description": "Our IDI methodology combines structured and exploratory techniques to uncover rich insights. Sessions are conducted by experienced moderators, recorded, transcribed, and analyzed using advanced qualitative coding software. We employ probing techniques to explore underlying attitudes, motivations, and decision-making processes.",
                "typical_duration_weeks": 3,
                "typical_cost_range": {"min": 10000, "max": 30000, "currency": "USD"},
                "complexity_level": "simple",
                "tags": ["qualitative", "interviews", "depth", "exploratory", "b2b"],
            },
            {
                "category": "methodology",
                "name": "Focus Groups",
                "description": "Moderated group discussions to explore attitudes, perceptions, and group dynamics",
                "detailed_description": "We conduct focus groups in professional facilities with experienced moderators. Each session is video recorded and professionally transcribed. Our analysis includes thematic coding and comparative analysis across groups. We specialize in managing group dynamics to ensure all voices are heard and diverse perspectives are captured.",
                "typical_duration_weeks": 3,
                "typical_cost_range": {"min": 12000, "max": 35000, "currency": "USD"},
                "complexity_level": "moderate",
                "tags": ["qualitative", "focus groups", "moderated", "group dynamics", "b2c"],
            },
            {
                "category": "methodology",
                "name": "Customer Satisfaction Studies",
                "description": "Comprehensive measurement of customer satisfaction, loyalty, and experience metrics",
                "detailed_description": "Our customer satisfaction research combines quantitative and qualitative approaches to measure satisfaction, identify pain points, and provide actionable recommendations. We track key metrics including NPS, CSAT, and CES, and benchmark against industry standards. Our analysis identifies drivers of satisfaction and priorities for improvement.",
                "typical_duration_weeks": 6,
                "typical_cost_range": {"min": 25000, "max": 75000, "currency": "USD"},
                "complexity_level": "moderate",
                "tags": ["customer satisfaction", "NPS", "CSAT", "loyalty", "tracking"],
            },
            {
                "category": "industry_expertise",
                "name": "Financial Services Research",
                "description": "Specialized expertise in banking, insurance, and investment services research",
                "detailed_description": "Our team has deep experience conducting research in financial services including customer satisfaction studies, new product testing, brand health tracking, and customer journey mapping for banks, credit unions, insurance providers, and fintech companies. We understand the regulatory environment and unique challenges of financial services research.",
                "tags": ["financial services", "banking", "insurance", "fintech", "compliance"],
            },
            {
                "category": "industry_expertise",
                "name": "Healthcare & Pharma Research",
                "description": "Research expertise in healthcare, pharmaceuticals, and medical devices",
                "detailed_description": "We conduct research with healthcare professionals, patients, and caregivers across therapeutic areas. Our team understands HIPAA compliance, IRB requirements, and sensitive health topics. We have experience with physician research, patient journey studies, treatment satisfaction, and medical device usability testing.",
                "tags": ["healthcare", "pharma", "medical devices", "HIPAA", "patient research"],
            },
        ]

        for cap_data in capabilities_data:
            # Generate embedding
            logger.info(f"Generating embedding for: {cap_data['name']}")
            embedding_text = f"{cap_data['name']} {cap_data['description']}"
            embedding = await llm_service.generate_embedding(embedding_text)

            capability = Capability(
                category=cap_data["category"],
                name=cap_data["name"],
                description=cap_data["description"],
                detailed_description=cap_data.get("detailed_description"),
                typical_duration_weeks=cap_data.get("typical_duration_weeks"),
                typical_cost_range=cap_data.get("typical_cost_range"),
                complexity_level=cap_data.get("complexity_level"),
                tags=cap_data["tags"],
                embedding=embedding,
                is_active=True,
            )
            db.add(capability)

        logger.info("Committing capabilities...")
        db.commit()

        # Add sample resources
        logger.info("Adding sample resources...")
        resources_data = [
            {
                "type": "internal",
                "name": "Dr. Sarah Johnson",
                "title": "Senior Research Director",
                "bio": "15+ years of experience leading quantitative and qualitative research projects across industries. PhD in Marketing from Northwestern University. Specializes in customer experience research and advanced analytics.",
                "skills": ["quantitative", "qualitative", "survey design", "statistical analysis", "project management"],
                "expertise_areas": ["customer satisfaction", "brand research", "financial services", "b2c"],
                "hourly_rate": 200.00,
                "currency": "USD",
                "email": "sarah@researchsolutions.com",
            },
            {
                "type": "internal",
                "name": "Mike Chen",
                "title": "Senior Quantitative Analyst",
                "bio": "10 years of experience in survey design, advanced statistical analysis, and data visualization. Expert in SPSS, R, and Python. MS in Statistics from UC Berkeley. Specializes in complex sampling and multivariate analysis.",
                "skills": ["quantitative", "statistical analysis", "survey programming", "data visualization", "python", "r", "spss"],
                "expertise_areas": ["survey research", "predictive analytics", "segmentation", "sampling"],
                "hourly_rate": 175.00,
                "currency": "USD",
                "email": "mike@researchsolutions.com",
            },
            {
                "type": "internal",
                "name": "Jennifer Rodriguez",
                "title": "Qualitative Research Manager",
                "bio": "8 years of experience moderating focus groups and conducting in-depth interviews. Skilled in qualitative coding and thematic analysis using NVivo and Atlas.ti. Bilingual (English/Spanish).",
                "skills": ["qualitative", "moderation", "interviewing", "thematic analysis", "nvivo", "coding"],
                "expertise_areas": ["consumer insights", "healthcare", "retail", "hispanic market"],
                "hourly_rate": 165.00,
                "currency": "USD",
                "email": "jennifer@researchsolutions.com",
            },
            {
                "type": "internal",
                "name": "David Park",
                "title": "Project Manager",
                "bio": "12 years of experience managing complex research projects. Expert in client relations, timeline management, and budget oversight. Certified PMP. Strong background in healthcare and technology research.",
                "skills": ["project management", "client relations", "budgeting", "timeline management", "stakeholder management"],
                "expertise_areas": ["healthcare", "technology", "b2b", "multi-market studies"],
                "hourly_rate": 150.00,
                "currency": "USD",
                "email": "david@researchsolutions.com",
            },
            {
                "type": "external",
                "name": "Dr. Emily Watson",
                "title": "Healthcare Research Consultant",
                "bio": "20+ years of experience in healthcare research. Former VP of Research at major pharmaceutical company. PhD in Public Health. Specializes in patient research and healthcare professional studies.",
                "skills": ["healthcare research", "patient research", "physician research", "regulatory compliance", "IRB"],
                "expertise_areas": ["pharmaceuticals", "medical devices", "patient journey", "treatment satisfaction"],
                "hourly_rate": 250.00,
                "currency": "USD",
                "email": "emily.watson@consultant.com",
            },
        ]

        for res_data in resources_data:
            resource = Resource(
                type=res_data["type"],
                name=res_data["name"],
                title=res_data["title"],
                bio=res_data["bio"],
                skills=res_data["skills"],
                expertise_areas=res_data["expertise_areas"],
                hourly_rate=res_data["hourly_rate"],
                currency=res_data["currency"],
                email=res_data["email"],
                is_active=True,
            )
            db.add(resource)

        logger.info("Committing resources...")
        db.commit()

        logger.info("=" * 60)
        logger.info("✅ Database initialized successfully!")
        logger.info("=" * 60)
        logger.info("📧 Admin login: admin@example.com")
        logger.info("🔑 Password: admin123")
        logger.info("=" * 60)
        logger.info(f"Added {len(capabilities_data)} capabilities")
        logger.info(f"Added {len(resources_data)} resources")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(init_database())
