"""
Configuration module for vulnctl.

Loads settings from environment variables / .env file.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Temporal settings
    temporal_host: str = Field(default="localhost", description="Temporal server host")
    temporal_port: int = Field(default=7233, description="Temporal server port")

    # cve-collector gRPC client settings
    collector_grpc_host: str = Field(
        default="localhost", description="cve-collector gRPC host"
    )
    collector_grpc_port: int = Field(
        default=50052, description="cve-collector gRPC port"
    )

    # cve-core gRPC client settings
    cve_core_grpc_host: str = Field(
        default="localhost", description="cve-core gRPC host"
    )
    cve_core_grpc_port: int = Field(default=50051, description="cve-core gRPC port")

    # Temporal: task queue where CVECollectorWorkflow is registered
    collector_task_queue: str = Field(
        default="cve-collector",
        description="Temporal task queue of the cve-collector worker",
    )

    # Auth settings
    api_key: str = Field(
        default="", description="API key for gRPC calls (env: API_KEY)"
    )

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
    def collector_grpc_address(self) -> str:
        """cve-collector gRPC address."""
        return f"{self.collector_grpc_host}:{self.collector_grpc_port}"

    @property
    def cve_core_grpc_address(self) -> str:
        """cve-core gRPC address."""
        return f"{self.cve_core_grpc_host}:{self.cve_core_grpc_port}"

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
