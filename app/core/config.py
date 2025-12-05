"""Application configuration settings."""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(default="postgresql://localhost/proposal_bot", env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # LLM Providers
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")

    # Email
    smtp_server: str = Field(default="smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")

    imap_server: str = Field(default="imap.gmail.com", env="IMAP_SERVER")
    imap_port: int = Field(default=993, env="IMAP_PORT")
    imap_username: str = Field(default="", env="IMAP_USERNAME")
    imap_password: str = Field(default="", env="IMAP_PASSWORD")

    # Notion
    notion_token: str = Field(default="", env="NOTION_TOKEN")
    notion_database_ids: dict = Field(default_factory=dict, env="NOTION_DATABASE_IDS")

    # Google Search
    google_search_api_key: str = Field(default="", env="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: str = Field(default="", env="GOOGLE_SEARCH_ENGINE_ID")

    # Application
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Timeouts and intervals
    email_check_interval: int = Field(default=60, env="EMAIL_CHECK_INTERVAL")  # seconds
    validation_timeout: int = Field(default=72 * 3600, env="VALIDATION_TIMEOUT")  # 72 hours
    clarification_timeout: int = Field(default=72 * 3600, env="CLARIFICATION_TIMEOUT")  # 72 hours
    project_lead_timeout: int = Field(default=48 * 3600, env="PROJECT_LEAD_TIMEOUT")  # 48 hours

    # Processing timeouts
    rfp_analysis_timeout: int = Field(default=3600, env="RFP_ANALYSIS_TIMEOUT")  # 1 hour
    planning_timeout: int = Field(default=7200, env="PLANNING_TIMEOUT")  # 2 hours
    proposal_generation_timeout: int = Field(default=3600, env="PROPOSAL_GENERATION_TIMEOUT")  # 1 hour

    # Concurrency
    max_concurrent_validations: int = Field(default=10, env="MAX_CONCURRENT_VALIDATIONS")
    lock_ttl: int = Field(default=300, env="LOCK_TTL")  # 5 minutes

    # Email deduplication
    email_deduplication_ttl: int = Field(default=48 * 3600, env="EMAIL_DEDUPLICATION_TTL")  # 48 hours

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
