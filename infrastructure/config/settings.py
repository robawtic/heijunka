from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with fallbacks to default values.

    Environment variables take precedence over values defined in the .env file.
    """
    # API settings
    app_name: str = "Heijunka API"
    version: str = "1.0.0"
    debug: bool = Field(False, env="DEBUG")

    # Security settings
    jwt_secret_key: str = Field(default=os.environ.get("JWT_SECRET_KEY", "default-secret-key"), env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = Field(30, env="JWT_EXPIRATION_MINUTES")

    # CSRF and session settings
    secret_key: str = Field(default="your-secret-key-for-sessions", env="SECRET_KEY")
    csrf_secret: str = Field(default="your-csrf-secret-key", env="CSRF_SECRET")
    cookie_secure: bool = Field(default=True, env="COOKIE_SECURE")
    session_max_age: int = Field(default=14400, env="SESSION_MAX_AGE")  # 4 hours

    # CORS settings
    allowed_origins: str = Field("", env="ALLOWED_ORIGINS")

    @property
    def allowed_origins_list(self) -> List[str]:
        """
        Parse allowed_origins from comma-separated string to list.
        This is used to convert the comma-separated ALLOWED_ORIGINS env var to a list.
        """
        if not self.allowed_origins:
            return []
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    # Database settings
    database_url: str = Field(default=os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:Brownie12-@localhost/heijunka"), env="DATABASE_URL")
    # Scheduler settings
    periods: int = Field(4, env="PERIODS")
    max_solve_time: int = Field(60, env="MAX_SOLVE_TIME")
    lookback: int = Field(3, env="LOOKBACK")

    # Logging settings
    log_level: str = Field("WARNING", env="LOG_LEVEL") # DEBUG, WARNING, ERROR, CRITICAL
    redaction_level: str = Field("none", env="REDACTION_LEVEL")  # Options: "none", "low", "high"
    include_redacted_metadata: bool = Field(False, env="LOG_INCLUDE_REDACTED_METADATA")
    log_dir: str = Field("logs", env="LOG_DIR")
    max_log_size_mb: int = Field(10, env="MAX_LOG_SIZE_MB")
    log_backup_count: int = Field(10, env="LOG_BACKUP_COUNT")
    enable_audit_log: bool = Field(True, env="ENABLE_AUDIT_LOG")

    # Environment settings
    environment: str = Field("development", env="ENVIRONMENT")

    # Cache settings
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    cache_ttl_seconds: int = Field(300, env="CACHE_TTL_SECONDS")  # 5 minutes default

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

        # Use case-sensitive environment variables to match .env file
        case_sensitive = True

        # Allow environment variables to be read
        extra = "ignore"

# Create a global settings instance
settings = Settings()
