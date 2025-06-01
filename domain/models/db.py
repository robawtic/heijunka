# models/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from infrastructure.config.settings import settings
import os
# Environment variables are already loaded in settings.py
# from dotenv import load_dotenv
# load_dotenv()

# Get database URL from settings with fallback
DATABASE_URL = settings.database_url

# Create the engine with appropriate configuration based on database type
if DATABASE_URL.startswith('postgresql'):
    # PostgreSQL-specific configuration
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_size=5,               # Default connection pool size
        max_overflow=10,           # Allow up to 10 connections beyond pool_size
        pool_timeout=30,           # Timeout for getting a connection from pool
        pool_recycle=1800,         # Recycle connections after 30 minutes
        connect_args={
            "connect_timeout": 10  # Connection timeout in seconds
        }
    )
else:
    # Default configuration for other database types (SQLite, etc.)
    engine = create_engine(DATABASE_URL, echo=False, future=True)

# Configure session factory
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Optional: scoped session for thread safety in apps or scripts
Session = scoped_session(SessionFactory)
