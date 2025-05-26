# heijunka/main.py
import os
import sys
from dotenv import load_dotenv
from infrastructure.config.settings import settings
from presentation.cli.cli import main

def validate_environment():
    """Validate that all required environment variables are set and valid."""
    # Load environment variables
    load_dotenv()

    # Check if JWT_SECRET_KEY is set and not the default value
    if not settings.jwt_secret_key or settings.jwt_secret_key == "your-secure-secret-key-here":
        print("Error: JWT_SECRET_KEY is not set or is using the default value. Please set a secure secret key.", file=sys.stderr)
        sys.exit(1)

    # Check if we're in production and using a secure database
    if settings.environment == "production":
        # In production, database should not be SQLite
        if settings.database_url.startswith("sqlite"):
            print("Warning: Using SQLite in production is not recommended. Consider using a more robust database.", file=sys.stderr)

        # In production, ensure JWT secret is sufficiently complex
        if len(settings.jwt_secret_key) < 32:
            print("Warning: JWT_SECRET_KEY is too short for production use. It should be at least 32 characters.", file=sys.stderr)

    print(f"Environment: {settings.environment}")
    print(f"Database: {settings.database_url}")
    print("Environment configuration validated successfully.")

if __name__ == '__main__':
    validate_environment()
    main()
