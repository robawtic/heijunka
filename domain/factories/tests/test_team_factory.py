# domain/factories/tests/test_team_factory.py
import unittest
from unittest.mock import MagicMock, patch

from domain.factories.team_factory import TeamFactory
from domain.entities.team import Team
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.entities.team_member import TeamMember

class TestTeamFactory(unittest.TestCase):
    def test_create_team_basic(self):
        """Test basic team creation with TeamFactory."""
        team = TeamFactory.create_team(
            id=1,
            name="Test Team",
            description="A test team"
        )
        
        self.assertEqual(team.id, 1)
        self.assertEqual(team.name, "Test Team")
        self.assertEqual(team.description, "A test team")
        self.assertEqual(len(team.members), 0)
        self.assertEqual(len(team.workstations), 0)
        self.assertEqual(len(team.team_members), 0)
    
    def test_create_team_with_members(self):
        """Test team creation with members."""
        # Create mock employees
        employee1 = MagicMock(spec=Employee)
        employee1.id = 1
        employee1.name = "Employee 1"
        
        employee2 = MagicMock(spec=Employee)
        employee2.id = 2
        employee2.name = "Employee 2"
        
        # Create team with members
        team = TeamFactory.create_team_with_members(
            id=1,
            name="Test Team",
            description="A test team with members",
            members=[employee1, employee2]
        )
        
        self.assertEqual(team.id, 1)
        self.assertEqual(team.name, "Test Team")
        self.assertEqual(len(team.members), 2)
        self.assertEqual(team.members[0].id, 1)
        self.assertEqual(team.members[1].id, 2)
    
    def test_create_team_with_workstations(self):
        """Test team creation with workstations."""
        # Create mock workstations
        workstation1 = MagicMock(spec=Workstation)
        workstation1.id = 1
        workstation1.name = "Workstation 1"
        
        workstation2 = MagicMock(spec=Workstation)
        workstation2.id = 2
        workstation2.name = "Workstation 2"
        
        # Create team with workstations
        team = TeamFactory.create_team_with_workstations(
            id=1,
            name="Test Team",
            description="A test team with workstations",
            workstations=[workstation1, workstation2]
        )
        
        self.assertEqual(team.id, 1)
        self.assertEqual(team.name, "Test Team")
        self.assertEqual(len(team.workstations), 2)
        self.assertEqual(team.workstations[0].id, 1)
        self.assertEqual(team.workstations[1].id, 2)
    
    def test_create_from_model(self):
        """Test creating a team from a model."""
        # Create a mock model
        model = MagicMock()
        model.id = 1
        model.name = "Test Team"
        model.description = "A test team from model"
        
        # Mock members
        member1 = MagicMock()
        member1.id = 101
        member1.employee_id = 1
        member1.roles = [MagicMock(name="Team Leader")]
        
        member2 = MagicMock()
        member2.id = 102
        member2.employee_id = 2
        member2.roles = [MagicMock(name="Associate")]
        
        model.members = [member1, member2]
        
        # Mock workstations
        workstation1 = MagicMock()
        workstation1.id = 201
        workstation1.name = "Workstation 1"
        
        workstation2 = MagicMock()
        workstation2.id = 202
        workstation2.name = "Workstation 2"
        
        model.workstations = [workstation1, workstation2]
        
        # Mock the employee and workstation factories
        with patch('domain.factories.employee_factory.EmployeeFactory') as mock_employee_factory, \
             patch('domain.factories.workstation_factory.WorkstationFactory') as mock_workstation_factory:
            
            # Setup mock returns
            mock_employee1 = MagicMock(spec=Employee)
            mock_employee1.id = 1
            mock_employee2 = MagicMock(spec=Employee)
            mock_employee2.id = 2
            
            mock_workstation1 = MagicMock(spec=Workstation)
            mock_workstation1.id = 201
            mock_workstation2 = MagicMock(spec=Workstation)
            mock_workstation2.id = 202
            
            mock_employee_factory.create_from_model.side_effect = [mock_employee1, mock_employee2]
            mock_workstation_factory.create_from_model.side_effect = [mock_workstation1, mock_workstation2]
            
            # Create team from model
            team = TeamFactory.create_from_model(model)
            
            # Verify the team
            self.assertEqual(team.id, 1)
            self.assertEqual(team.name, "Test Team")
            self.assertEqual(team.description, "A test team from model")
            
            # Verify factory calls
            self.assertEqual(mock_employee_factory.create_from_model.call_count, 2)
            self.assertEqual(mock_workstation_factory.create_from_model.call_count, 2)

if __name__ == "__main__":
    unittest.main()