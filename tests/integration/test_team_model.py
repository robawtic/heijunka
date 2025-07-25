import unittest
import uuid
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from domain.models.Base import Base
from domain.models.TeamModel import TeamModel
from domain.contexts.employee_management.entities.team import Team


class TestTeamModel(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        # Create engine
        self.engine = create_engine('sqlite:///heijunka.db')
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Generate unique team name to avoid conflicts
        self.test_team_name = f"Test Team {uuid.uuid4().hex[:8]}"

    def tearDown(self):
        """Clean up after test."""
        # Clean up any test teams
        test_teams = self.session.query(TeamModel).filter(
            TeamModel.name.like("Test Team %")
        ).all()
        for team in test_teams:
            self.session.delete(team)
        self.session.commit()
        self.session.close()

    def test_team_model_columns(self):
        """Test that the teams table has the expected columns."""
        inspector = inspect(self.engine)
        columns = inspector.get_columns('teams')
        column_names = [column['name'] for column in columns]

        # Check for essential columns
        self.assertIn('id', column_names)
        self.assertIn('name', column_names)
        self.assertIn('description', column_names)
        self.assertIn('created_at', column_names)
        self.assertIn('updated_at', column_names)

    def test_team_model_crud_operations(self):
        """Test CRUD operations on TeamModel."""
        # Create a test team
        test_team = TeamModel(
            name=self.test_team_name,
            description="A test team with description",
        )
        self.session.add(test_team)
        self.session.commit()

        # Retrieve the team and check if the fields are set correctly
        team = self.session.query(TeamModel).filter_by(name=self.test_team_name).first()
        self.assertIsNotNone(team)
        self.assertEqual(team.name, self.test_team_name)
        self.assertEqual(team.description, "A test team with description")
        self.assertIsNotNone(team.created_at)
        self.assertIsNotNone(team.updated_at)

        # Convert to domain entity and check if the fields are set correctly
        domain_team = team.to_domain()
        self.assertIsNotNone(domain_team)
        self.assertEqual(domain_team.name, self.test_team_name)
        self.assertEqual(domain_team.description, "A test team with description")


if __name__ == '__main__':
    unittest.main()
