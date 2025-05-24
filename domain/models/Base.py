# models/Base.py

from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

# Define naming conventions for automatic constraint/index names (optional but good practice)
NAMING_CONVENTIONS = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Assign metadata with naming conventions to support Alembic and consistency
metadata = MetaData(naming_convention=NAMING_CONVENTIONS)

# Declarative base for all models
Base = declarative_base(metadata=metadata)
