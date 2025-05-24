from sqlalchemy import create_engine
from domain.models.Base import Base
from domain.models.TeamModel import TeamModel

# Import all models to ensure they're registered with the Base metadata
import domain.models

# Create engine
engine = create_engine('sqlite:///heijunka.db')

# Update the schema
Base.metadata.create_all(engine)

print("Schema updated successfully.")