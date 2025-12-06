"""Configuration settings for the Proposal Bot system."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic Configuration
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude models")

    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(
        default=True, description="Enable LangSmith tracing for monitoring"
    )
    langchain_api_key: Optional[str] = Field(
        default=None, description="LangSmith API key for deployment"
    )
    langchain_project: str = Field(
        default="proposal-bot", description="LangSmith project name"
    )

    # Google Workspace Configuration
    google_client_id: str = Field(..., description="Google OAuth client ID")
    google_client_secret: str = Field(..., description="Google OAuth client secret")
    google_refresh_token: str = Field(..., description="Google OAuth refresh token")

    # Google Sheets IDs
    staff_profiles_sheet_id: str = Field(..., description="Google Sheet ID for staff profiles")
    pricing_sheet_id: str = Field(..., description="Google Sheet ID for pricing data")
    vendor_relationships_sheet_id: str = Field(
        ..., description="Google Sheet ID for vendor relationships"
    )
    capabilities_sheet_id: str = Field(
        ..., description="Google Sheet ID for company capabilities"
    )

    # Gmail Configuration
    gmail_user_email: str = Field(
        ..., description="Gmail address for sending/receiving emails"
    )
    gmail_client_id: str = Field(..., description="Gmail OAuth client ID")
    gmail_client_secret: str = Field(..., description="Gmail OAuth client secret")
    gmail_access_token: str = Field(..., description="Gmail OAuth access token")
    gmail_refresh_token: str = Field(..., description="Gmail OAuth refresh token")

    # Database Configuration
    database_url: str = Field(
        default="postgresql://localhost:5432/proposal_bot",
        description="PostgreSQL database URL with pgvector support",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis URL for caching and coordination"
    )

    # Application Settings
    environment: str = Field(default="development", description="Environment: development/production")
    log_level: str = Field(default="INFO", description="Logging level")
    max_concurrent_validations: int = Field(
        default=10, description="Maximum concurrent validation emails"
    )
    validation_timeout_hours: int = Field(
        default=72, description="Hours to wait for validation responses"
    )
    project_lead_response_timeout_hours: int = Field(
        default=48, description="Hours to wait for project lead responses"
    )

    # Authentication Configuration
    jwt_secret_key: Optional[str] = Field(
        default=None, description="JWT secret key for token signing"
    )
    admin_username: str = Field(
        default="admin", description="Admin username for agent server access"
    )
    admin_password_hash: str = Field(
        ..., description="Hashed admin password for agent server access"
    )

    # Audit Logging Configuration
    audit_logging_enabled: bool = Field(
        default=True, description="Enable comprehensive audit logging"
    )

    # Deployment Configuration
    deployment_environment: str = Field(
        default="development", description="Deployment environment for LangSmith"
    )
    version: str = Field(default="1.0.0", description="Application version")

    # Monitoring (Optional)
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")

    # LLM Configuration
    default_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Default Anthropic model"
    )
    fast_model: str = Field(
        default="claude-3-5-haiku-20241022", description="Fast model for simple tasks"
    )
    temperature: float = Field(default=0.7, description="LLM temperature for generation")
    max_tokens: int = Field(default=4096, description="Maximum tokens for LLM responses")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
