"""
Database Role-Based Access Control (RBAC) setup for PostgreSQL.

This module provides functions to set up RBAC in PostgreSQL databases,
creating roles with appropriate permissions for different access levels.
"""

import os
import subprocess
from typing import Optional, List, Dict
import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Role definitions with their permissions
ROLES = {
    "heijunka_admin": {
        "description": "Full administrative access to the database",
        "permissions": ["ALL PRIVILEGES ON DATABASE {database} TO {role}"]
    },
    "heijunka_writer": {
        "description": "Can read, insert, update, and delete data",
        "permissions": [
            "SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}",
            "USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"
        ]
    },
    "heijunka_reader": {
        "description": "Read-only access to data",
        "permissions": ["SELECT ON ALL TABLES IN SCHEMA public TO {role}"]
    }
}

# Default privileges to set for future objects
DEFAULT_PRIVILEGES = {
    "heijunka_writer": [
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {role}"
    ],
    "heijunka_reader": [
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {role}"
    ]
}


def setup_database_roles(engine: Engine, database_name: str) -> None:
    """
    Set up database roles and permissions for PostgreSQL.
    
    Args:
        engine: SQLAlchemy engine connected to the PostgreSQL database
        database_name: Name of the database to set up roles for
    """
    if not engine.url.drivername.startswith('postgresql'):
        logger.warning("RBAC setup is only supported for PostgreSQL databases")
        return
    
    try:
        with engine.connect() as connection:
            # Create roles if they don't exist
            for role_name, role_config in ROLES.items():
                connection.execute(
                    text(f"DO $$ BEGIN CREATE ROLE {role_name} WITH LOGIN PASSWORD 'change_me_in_production'; EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'Role {role_name} already exists'; END $$;")
                )
                connection.commit()
                
                logger.info(f"Created role {role_name} or confirmed it exists")
                
                # Grant permissions to the role
                for permission in role_config["permissions"]:
                    formatted_permission = permission.format(database=database_name, role=role_name)
                    connection.execute(text(f"GRANT {formatted_permission};"))
                    connection.commit()
                    logger.info(f"Granted permission: {formatted_permission}")
            
            # Set default privileges for future objects
            for role_name, privileges in DEFAULT_PRIVILEGES.items():
                for privilege in privileges:
                    formatted_privilege = privilege.format(role=role_name)
                    connection.execute(text(formatted_privilege))
                    connection.commit()
                    logger.info(f"Set default privilege: {formatted_privilege}")
                    
            logger.info("Database RBAC setup completed successfully")
    
    except Exception as e:
        logger.error(f"Error setting up database roles: {str(e)}")
        raise


def get_database_name_from_url(database_url: str) -> Optional[str]:
    """
    Extract the database name from a database URL.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        The database name or None if it couldn't be extracted
    """
    if not database_url.startswith('postgresql'):
        return None
    
    try:
        # Extract database name from URL (last part after the last slash)
        return database_url.split('/')[-1]
    except Exception:
        return None


if __name__ == "__main__":
    """
    When run as a script, set up database roles for the database specified in DATABASE_URL.
    """
    from domain.models.db import engine, DATABASE_URL
    
    database_name = get_database_name_from_url(DATABASE_URL)
    if database_name:
        print(f"Setting up RBAC for database: {database_name}")
        setup_database_roles(engine, database_name)
    else:
        print("Could not determine database name from DATABASE_URL")