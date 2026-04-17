"""
Configuration module for vulnctl.

Loads settings from environment variables / .env file.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # cve-core REST client settings (used by cve last)
    cve_core_http_host: str = Field(
        default="localhost", description="cve-core REST host"
    )
    cve_core_http_port: int = Field(default=8080, description="cve-core REST port")

    # Application settings
    service_name: str = Field(default="vulnctl", description="Service name")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Runtime environment")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cve_core_http_base_url(self) -> str:
        """cve-core REST base URL."""
        return f"http://{self.cve_core_http_host}:{self.cve_core_http_port}"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if v.lower() not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v.lower()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
