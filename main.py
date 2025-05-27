# heijunka/main.py
import os
import sys
from dotenv import load_dotenv
from infrastructure.config.settings import settings
from presentation.cli.cli import main
from sqlalchemy.engine.url import make_url
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("main")

def get_masked_db_url(db_url):
    """Return a database URL with sensitive information masked."""
    try:
        url = make_url(db_url)
        # Create a masked version that hides the password
        masked_url = f"{url.drivername}://{url.username}:****@{url.host}/{url.database}"
        return masked_url
    except Exception:
        # If parsing fails, return a generic message
        return "Database connection configured"

def validate_environment():
    """Validate that all required environment variables are set and valid."""
    logger.info("Starting environment validation", event_type="environment", identifier="validation_start")

    # Load environment variables
    logger.debug("Loading environment variables", event_type="environment", identifier="load_env")
    load_dotenv()

    # Check if JWT_SECRET_KEY is set and not the default value
    logger.debug("Checking JWT_SECRET_KEY", event_type="environment", identifier="jwt_check")
    if not settings.jwt_secret_key or settings.jwt_secret_key == "your-secure-secret-key-here":
        error_msg = "Error: JWT_SECRET_KEY is not set or is using the default value. Please set a secure secret key."
        logger.error(error_msg, event_type="environment", identifier="jwt_error")
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    # Check if we're in production and using a secure database
    if settings.environment == "production":
        logger.debug("Performing production environment checks", event_type="environment", identifier="production_checks")

        # In production, database should not be SQLite
        if settings.database_url.startswith("sqlite"):
            warning_msg = "Warning: Using SQLite in production is not recommended. Consider using a more robust database."
            logger.warning(warning_msg, event_type="environment", identifier="sqlite_warning")
            print(warning_msg, file=sys.stderr)

        # In production, ensure JWT secret is sufficiently complex
        if len(settings.jwt_secret_key) < 32:
            warning_msg = "Warning: JWT_SECRET_KEY is too short for production use. It should be at least 32 characters."
            logger.warning(warning_msg, event_type="environment", identifier="jwt_length_warning")
            print(warning_msg, file=sys.stderr)

    logger.info(f"Environment: {settings.environment}", event_type="environment", identifier="env_info")
    masked_db_url = get_masked_db_url(settings.database_url)
    logger.info(f"Database: {masked_db_url}", event_type="environment", identifier="db_info")
    logger.info("Environment configuration validated successfully.", event_type="environment", identifier="validation_success")

    print(f"Environment: {settings.environment}")
    print(f"Database: {masked_db_url}")
    print("Environment configuration validated successfully.")

if __name__ == '__main__':
    logger.info("Starting Heijunka application", event_type="application", identifier="startup")
    try:
        validate_environment()
        logger.info("Launching CLI interface", event_type="application", identifier="cli_start")
        main()
    except Exception as e:
        error_msg = f"Unexpected error in main application: {e}"
        logger.error(error_msg, event_type="application", identifier="error", extra={"exception": str(e)})
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    finally:
        logger.info("Heijunka application shutdown", event_type="application", identifier="shutdown")
