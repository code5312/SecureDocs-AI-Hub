import json
from functools import lru_cache
from typing import Annotated, Any

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", enable_decoding=False)

    app_env: str = "development"
    app_name: str = "SecureDocs AI Hub"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"
    refresh_cookie_name: str = "securedocs_refresh_token"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "securedocs"
    postgres_user: str = "securedocs"
    postgres_password: str = "securedocs_password"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False
    minio_document_bucket: str = "documents-original"
    minio_preview_bucket: str = "documents-preview"
    minio_backup_bucket: str = "documents-backup"
    minio_database_backup_bucket: str = "database-backup"
    minio_connect_timeout_seconds: float = 2.0
    minio_read_timeout_seconds: float = 2.0

    document_max_upload_size_mb: int = 50
    document_allowed_extensions: str = "pdf,docx,pptx,xlsx,txt,md"
    document_download_url_expires_seconds: int = 300

    extraction_max_file_size_mb: int = 50
    extraction_max_pages: int = 500
    extraction_max_slides: int = 500
    extraction_max_sheets: int = 100
    extraction_max_rows_per_sheet: int = 100000
    extraction_max_characters: int = 2000000
    extraction_max_chunks: int = 5000
    extraction_chunk_size: int = 1200
    extraction_chunk_overlap: int = 200
    extraction_max_attempts: int = 3

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Accept CORS origins as a JSON array, comma-separated string, or list."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith(("[", "{")):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError("CORS_ORIGINS JSON value must be a valid string array") from exc
                if not isinstance(parsed, list) or not all(isinstance(origin, str) for origin in parsed):
                    raise ValueError("CORS_ORIGINS JSON value must be a string array")
                return [origin.strip() for origin in parsed if origin.strip()]
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        if isinstance(value, list) and all(isinstance(origin, str) for origin in value):
            return [origin.strip() for origin in value if origin.strip()]
        raise ValueError("CORS_ORIGINS must be a comma-separated string or string array")


    @model_validator(mode="after")
    def validate_extraction_limits(self) -> "Settings":
        """Validate extraction safety limits are bounded and consistent."""
        positive_values = {
            "document_max_upload_size_mb": self.document_max_upload_size_mb,
            "extraction_max_file_size_mb": self.extraction_max_file_size_mb,
            "extraction_max_pages": self.extraction_max_pages,
            "extraction_max_slides": self.extraction_max_slides,
            "extraction_max_sheets": self.extraction_max_sheets,
            "extraction_max_rows_per_sheet": self.extraction_max_rows_per_sheet,
            "extraction_max_characters": self.extraction_max_characters,
            "extraction_max_chunks": self.extraction_max_chunks,
            "extraction_chunk_size": self.extraction_chunk_size,
            "extraction_chunk_overlap": self.extraction_chunk_overlap,
            "extraction_max_attempts": self.extraction_max_attempts,
        }
        for name, value in positive_values.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.extraction_chunk_overlap >= self.extraction_chunk_size:
            raise ValueError("extraction_chunk_overlap must be smaller than extraction_chunk_size")
        if self.extraction_max_file_size_mb > self.document_max_upload_size_mb:
            raise ValueError("extraction_max_file_size_mb must not exceed document_max_upload_size_mb")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy database URL without exposing it through API responses."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def required_minio_buckets(self) -> tuple[str, ...]:
        """Return all buckets required for this foundation to be ready."""
        return (
            self.minio_document_bucket,
            self.minio_preview_bucket,
            self.minio_backup_bucket,
            self.minio_database_backup_bucket,
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached process-wide settings."""
    return Settings()
