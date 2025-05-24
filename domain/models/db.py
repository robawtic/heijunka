# models/db.py (or database.py)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# You can later inject this from a config/env variable
DATABASE_URL = "sqlite:///heijunka.db"

# Create the engine
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Configure session factory
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Optional: scoped session for thread safety in apps or scripts
Session = scoped_session(SessionFactory)
