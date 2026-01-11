"""
Vault configuration management.

Loads configuration from environment variables or .env file.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VaultConfig(BaseSettings):
    """
    Vault configuration settings.

    Can be loaded from:
    1. Environment variables (VAULT_SUPABASE_URL, VAULT_SUPABASE_KEY, etc.)
    2. .env file in project root
    3. Direct instantiation with kwargs

    Example:
        ```python
        # From environment
        config = VaultConfig()

        # Direct instantiation
        config = VaultConfig(
            supabase_url="https://xxx.supabase.co",
            supabase_key="your-key"
        )
        ```
    """

    model_config = SettingsConfigDict(
        env_prefix="VAULT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase connection
    supabase_url: str = Field(
        ...,
        description="Supabase project URL (e.g., https://xxx.supabase.co)",
    )

    supabase_key: str = Field(
        ...,
        description="Supabase service role key (for admin operations)",
    )

    # Optional: Anon key for client-side operations
    supabase_anon_key: Optional[str] = Field(
        default=None,
        description="Supabase anon key (for client operations)",
    )

    # Database schema
    db_schema: str = Field(
        default="public",
        description="PostgreSQL schema where vault tables live",
        alias="schema",
    )

    # JWT settings
    jwt_secret: Optional[str] = Field(
        default=None,
        description="JWT secret for token validation (usually from Supabase)",
    )

    # Feature flags
    auto_migrate: bool = Field(
        default=False,
        description="Automatically run migrations on client initialization",
    )

    enable_audit_log: bool = Field(
        default=True,
        description="Enable audit logging for all operations",
    )

    # Email settings (for invitations)
    from_email: Optional[str] = Field(
        default=None,
        description="From email address for invitations (uses Supabase default if not set)",
    )

    # Debug
    debug: bool = Field(
        default=False,
        description="Enable debug logging",
    )

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Ensure Supabase URL is valid."""
        if not v.startswith("https://"):
            raise ValueError("supabase_url must start with https://")
        if not v.endswith(".supabase.co") and not v.endswith(".supabase.in"):
            # Allow custom domains but warn
            pass
        return v.rstrip("/")

    @field_validator("supabase_key")
    @classmethod
    def validate_supabase_key(cls, v: str) -> str:
        """Ensure Supabase key is not empty."""
        if not v or len(v) < 10:
            raise ValueError("supabase_key appears invalid (too short)")
        return v


def load_config(**kwargs) -> VaultConfig:
    """
    Load Vault configuration.

    Priority order:
    1. Keyword arguments
    2. Environment variables (VAULT_*)
    3. .env file

    Args:
        **kwargs: Override configuration values

    Returns:
        VaultConfig instance

    Raises:
        ValidationError: If required fields are missing or invalid

    Example:
        ```python
        # Load from environment
        config = load_config()

        # Override specific values
        config = load_config(debug=True)
        ```
    """
    return VaultConfig(**kwargs)
