from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from domain.models.Base import Base
from domain.models.TeamModel import TeamModel
from domain.entities.team import Team

# Create engine
engine = create_engine('sqlite:///heijunka.db')
Session = sessionmaker(bind=engine)
session = Session()

# Check if the columns exist in the teams table
inspector = inspect(engine)
columns = inspector.get_columns('teams')
column_names = [column['name'] for column in columns]
print("Columns in teams table:", column_names)

# Create a test team
test_team = TeamModel(
    name="Test Team",
    description="A test team with description",
)
session.add(test_team)
session.commit()

# Retrieve the team and check if the fields are set correctly
team = session.query(TeamModel).filter_by(name="Test Team").first()
print(f"Team ID: {team.id}")
print(f"Team Name: {team.name}")
print(f"Team Description: {team.description}")
print(f"Team Created At: {team.created_at}")
print(f"Team Updated At: {team.updated_at}")

# Convert to domain entity and check if the fields are set correctly
domain_team = team.to_domain()
print(f"Domain Team ID: {domain_team.id}")
print(f"Domain Team Name: {domain_team.name}")
print(f"Domain Team Description: {domain_team.description}")

# Clean up
session.delete(team)
session.commit()
session.close()

print("Test completed successfully.")