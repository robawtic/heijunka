"""
Database initialization script for Heijunka.

This script initializes the PostgreSQL database, sets up RBAC roles,
and applies the initial schema using Alembic migrations.

Usage:
    python -m infrastructure.database.init_db
"""

import os
import sys
import logging
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_database_if_not_exists(admin_url: str, database_name: str) -> bool:
    """
    Create the database if it doesn't exist.
    
    Args:
        admin_url: Database URL with admin credentials (without specific database)
        database_name: Name of the database to create
        
    Returns:
        True if database was created or already exists, False otherwise
    """
    engine = create_engine(admin_url)
    
    try:
        # Connect to the default database to create our application database
        with engine.connect() as connection:
            # Check if database exists
            result = connection.execute(text(
                f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'"
            ))
            exists = result.scalar() is not None
            
            if not exists:
                # Create database - need to run outside of transaction
                connection.execute(text("COMMIT"))
                connection.execute(text(f"CREATE DATABASE {database_name}"))
                logger.info(f"Created database: {database_name}")
                return True
            else:
                logger.info(f"Database {database_name} already exists")
                return True
                
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        return False
    finally:
        engine.dispose()


def setup_database():
    """
    Set up the database, create roles, and apply migrations.
    """
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    if not database_url.startswith("postgresql"):
        logger.error("This script is only for PostgreSQL databases")
        return False
    
    # Extract database name and connection info
    try:
        # Parse the database URL to get components
        # Format: postgresql+psycopg://user:password@host:port/dbname
        parts = database_url.split("://")[1].split("/")
        connection_info = parts[0]  # user:password@host:port
        database_name = parts[1]    # dbname
        
        # Create admin URL (connects to 'postgres' database)
        admin_url = f"postgresql+psycopg://{connection_info}/postgres"
        
        logger.info(f"Setting up database: {database_name}")
        
        # Step 1: Create database if it doesn't exist
        if not create_database_if_not_exists(admin_url, database_name):
            return False
        
        # Step 2: Set up RBAC roles
        from infrastructure.database.rbac import setup_database_roles
        from domain.models.db import engine
        
        logger.info("Setting up database roles...")
        setup_database_roles(engine, database_name)
        
        # Step 3: Apply Alembic migrations
        logger.info("Applying database migrations...")
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the Heijunka database")
    parser.add_argument("--force", action="store_true", help="Force initialization even if database exists")
    args = parser.parse_args()
    
    if setup_database():
        logger.info("Database initialization completed successfully")
        sys.exit(0)
    else:
        logger.error("Database initialization failed")
        sys.exit(1)