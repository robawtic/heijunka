import unittest
from datetime import date

from domain.entities.team import Team
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.entities.team_member import TeamMember
from domain.events import TeamMemberAdded, TeamMemberRemoved, WorkstationAddedToTeam, WorkstationRemovedFromTeam


class TestTeam(unittest.TestCase):
    def setUp(self):
        """Set up a new team for each test."""
        self.team = Team(
            id=1,
            name="Test Team",
            description="A test team"
        )
        
        # Create some test employees
        self.employee1 = Employee(
            id=1,
            name="John Doe",
            team_id=1,
            is_active=True
        )
        
        self.employee2 = Employee(
            id=2,
            name="Jane Smith",
            team_id=1,
            is_active=True
        )
        
        # Create some test workstations
        self.workstation1 = Workstation(
            id=1,
            name="Workstation 1",
            line_type="Mainline"
        )
        
        self.workstation2 = Workstation(
            id=2,
            name="Workstation 2",
            line_type="Mainline"
        )

    def test_initialization(self):
        """Test that a team is properly initialized."""
        self.assertEqual(self.team.id, 1)
        self.assertEqual(self.team.name, "Test Team")
        self.assertEqual(self.team.description, "A test team")
        self.assertEqual(self.team.members, [])
        self.assertEqual(self.team.workstations, [])
        self.assertEqual(self.team.team_members, [])
        self.assertEqual(self.team.domain_events, [])

    def test_create_class_method(self):
        """Test the create class method."""
        team = Team.create(name="New Team", description="A new team")
        self.assertEqual(team.id, 0)  # ID should be 0 until persisted
        self.assertEqual(team.name, "New Team")
        self.assertEqual(team.description, "A new team")
        self.assertEqual(team.members, [])
        self.assertEqual(team.workstations, [])

    def test_add_member(self):
        """Test adding a member to the team."""
        # Add a member
        result = self.team.add_member(self.employee1)
        self.assertTrue(result)
        self.assertEqual(len(self.team.members), 1)
        self.assertEqual(self.team.members[0].id, 1)
        
        # Check that a domain event was raised
        events = self.team.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TeamMemberAdded)
        self.assertEqual(events[0].team_id, 1)
        self.assertEqual(events[0].employee_id, 1)
        
        # Try to add the same member again
        result = self.team.add_member(self.employee1)
        self.assertFalse(result)  # Should return False for duplicate
        self.assertEqual(len(self.team.members), 1)  # Should still have only one member
        
        # Clear events and add another member
        self.team.clear_domain_events()
        result = self.team.add_member(self.employee2)
        self.assertTrue(result)
        self.assertEqual(len(self.team.members), 2)
        
        # Check that a new domain event was raised
        events = self.team.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TeamMemberAdded)
        self.assertEqual(events[0].employee_id, 2)

    def test_remove_member(self):
        """Test removing a member from the team."""
        # Add members
        self.team.add_member(self.employee1)
        self.team.add_member(self.employee2)
        self.team.clear_domain_events()
        
        # Remove a member
        result = self.team.remove_member(1)
        self.assertTrue(result)
        self.assertEqual(len(self.team.members), 1)
        self.assertEqual(self.team.members[0].id, 2)
        
        # Check that a domain event was raised
        events = self.team.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TeamMemberRemoved)
        self.assertEqual(events[0].team_id, 1)
        self.assertEqual(events[0].employee_id, 1)
        
        # Try to remove a non-existent member
        result = self.team.remove_member(999)
        self.assertFalse(result)
        self.assertEqual(len(self.team.members), 1)

    def test_add_workstation(self):
        """Test adding a workstation to the team."""
        # Add a workstation
        result = self.team.add_workstation(self.workstation1)
        self.assertTrue(result)
        self.assertEqual(len(self.team.workstations), 1)
        self.assertEqual(self.team.workstations[0].id, 1)
        self.assertEqual(self.team.workstations[0].team_id, 1)  # Should update the workstation's team_id
        
        # Check that a domain event was raised
        events = self.team.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationAddedToTeam)
        self.assertEqual(events[0].team_id, 1)
        self.assertEqual(events[0].workstation_id, 1)
        
        # Try to add the same workstation again
        result = self.team.add_workstation(self.workstation1)
        self.assertFalse(result)  # Should return False for duplicate
        self.assertEqual(len(self.team.workstations), 1)  # Should still have only one workstation
        
        # Clear events and add another workstation
        self.team.clear_domain_events()
        result = self.team.add_workstation(self.workstation2)
        self.assertTrue(result)
        self.assertEqual(len(self.team.workstations), 2)
        
        # Check that a new domain event was raised
        events = self.team.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationAddedToTeam)
        self.assertEqual(events[0].workstation_id, 2)

    def test_remove_workstation(self):
        """Test removing a workstation from the team."""
        # Add workstations
        self.team.add_workstation(self.workstation1)
        self.team.add_workstation(self.workstation2)
        self.team.clear_domain_events()
        
        # Remove a workstation
        result = self.team.remove_workstation(1)
        self.assertTrue(result)
        self.assertEqual(len(self.team.workstations), 1)
        self.assertEqual(self.team.workstations[0].id, 2)
        
        # Check that a domain event was raised
        events = self.team.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationRemovedFromTeam)
        self.assertEqual(events[0].team_id, 1)
        self.assertEqual(events[0].workstation_id, 1)
        
        # Try to remove a non-existent workstation
        result = self.team.remove_workstation(999)
        self.assertFalse(result)
        self.assertEqual(len(self.team.workstations), 1)

    def test_get_member_by_id(self):
        """Test getting a member by ID."""
        # Add members
        self.team.add_member(self.employee1)
        self.team.add_member(self.employee2)
        
        # Get a member by ID
        member = self.team.get_member_by_id(1)
        self.assertIsNotNone(member)
        self.assertEqual(member.id, 1)
        self.assertEqual(member.name, "John Doe")
        
        # Try to get a non-existent member
        member = self.team.get_member_by_id(999)
        self.assertIsNone(member)

    def test_get_workstation_by_id(self):
        """Test getting a workstation by ID."""
        # Add workstations
        self.team.add_workstation(self.workstation1)
        self.team.add_workstation(self.workstation2)
        
        # Get a workstation by ID
        workstation = self.team.get_workstation_by_id(1)
        self.assertIsNotNone(workstation)
        self.assertEqual(workstation.id, 1)
        self.assertEqual(workstation.name, "Workstation 1")
        
        # Try to get a non-existent workstation
        workstation = self.team.get_workstation_by_id(999)
        self.assertIsNone(workstation)

    def test_get_team_member_by_employee_id(self):
        """Test getting a TeamMember entity by employee ID."""
        # Add members
        self.team.add_member(self.employee1)
        self.team.add_member(self.employee2)
        
        # Get a TeamMember by employee ID
        team_member = self.team.get_team_member_by_employee_id(1)
        self.assertIsNotNone(team_member)
        self.assertEqual(team_member.employee_id, 1)
        self.assertEqual(team_member.team_id, 1)
        
        # Try to get a non-existent TeamMember
        team_member = self.team.get_team_member_by_employee_id(999)
        self.assertIsNone(team_member)

    def test_assign_role_to_member(self):
        """Test assigning a role to a team member."""
        # Add a member
        self.team.add_member(self.employee1)
        
        # Assign a role
        result = self.team.assign_role_to_member(1, "Team Lead")
        self.assertTrue(result)
        
        # Check that the role was assigned
        team_member = self.team.get_team_member_by_employee_id(1)
        self.assertIn("Team Lead", team_member.roles)
        
        # Try to assign the same role again
        result = self.team.assign_role_to_member(1, "Team Lead")
        self.assertFalse(result)  # Should return False for duplicate
        
        # Try to assign a role to a non-existent member
        result = self.team.assign_role_to_member(999, "Team Lead")
        self.assertFalse(result)

    def test_remove_role_from_member(self):
        """Test removing a role from a team member."""
        # Add a member and assign a role
        self.team.add_member(self.employee1)
        self.team.assign_role_to_member(1, "Team Lead")
        
        # Remove the role
        result = self.team.remove_role_from_member(1, "Team Lead")
        self.assertTrue(result)
        
        # Check that the role was removed
        team_member = self.team.get_team_member_by_employee_id(1)
        self.assertNotIn("Team Lead", team_member.roles)
        
        # Try to remove a non-existent role
        result = self.team.remove_role_from_member(1, "Non-existent Role")
        self.assertFalse(result)
        
        # Try to remove a role from a non-existent member
        result = self.team.remove_role_from_member(999, "Team Lead")
        self.assertFalse(result)

    def test_validate(self):
        """Test validating the team entity."""
        # Valid team
        self.team.validate()  # Should not raise an exception
        
        # Invalid team name (empty)
        team = Team(id=2, name="", description="Invalid team")
        with self.assertRaises(ValueError):
            team.validate()
        
        # Invalid team name (too long)
        team = Team(id=3, name="x" * 101, description="Invalid team")
        with self.assertRaises(ValueError):
            team.validate()


if __name__ == "__main__":
    unittest.main()