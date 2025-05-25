import unittest
from datetime import date

from domain.entities.employee import Employee
from domain.value_objects.employee_availability import EmployeeAvailability, AvailabilityStatus
from domain.entities.team_member import TeamMember
from domain.value_objects.work_history_entry import WorkHistoryEntry
from domain.value_objects.workstation_assignment import WorkstationAssignment
from domain.events import QualificationAdded, QualificationRemoved, RoleAssigned, TeamRoleAssigned, WorkHistoryEntryAdded


class TestEmployee(unittest.TestCase):
    def setUp(self):
        """Set up a new employee for each test."""
        self.employee = Employee(
            id=1,
            name="John Doe",
            team_id=1,
            is_active=True
        )

    def test_initialization(self):
        """Test that an employee is properly initialized."""
        self.assertEqual(self.employee.id, 1)
        self.assertEqual(self.employee.name, "John Doe")
        self.assertEqual(self.employee.team_id, 1)
        self.assertTrue(self.employee.is_active)
        self.assertEqual(self.employee.roles, [])
        self.assertEqual(self.employee.qualifications, [])
        self.assertEqual(self.employee.available_periods, [])
        self.assertEqual(self.employee.work_history, [])
        self.assertEqual(self.employee.assigned_workstations, [])
        self.assertEqual(self.employee.team_memberships, [])
        self.assertEqual(self.employee.domain_events, [])

    def test_add_qualification(self):
        """Test adding a qualification to an employee."""
        # Add a qualification
        result = self.employee.add_qualification("Workstation1")
        self.assertTrue(result)
        self.assertEqual(self.employee.qualifications, ["Workstation1"])

        # Check that a domain event was raised
        events = self.employee.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], QualificationAdded)
        self.assertEqual(events[0].employee_id, 1)
        self.assertEqual(events[0].qualification, "Workstation1")

        # Try to add the same qualification again
        result = self.employee.add_qualification("Workstation1")
        self.assertFalse(result)  # Should return False for duplicate
        self.assertEqual(self.employee.qualifications, ["Workstation1"])  # Should still have only one

        # Clear events and add another qualification
        self.employee.clear_domain_events()
        result = self.employee.add_qualification("Workstation2")
        self.assertTrue(result)
        self.assertEqual(self.employee.qualifications, ["Workstation1", "Workstation2"])

        # Check that a new domain event was raised
        events = self.employee.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], QualificationAdded)
        self.assertEqual(events[0].qualification, "Workstation2")

        # Test invalid qualification
        with self.assertRaises(ValueError):
            self.employee.add_qualification("")
        with self.assertRaises(ValueError):
            self.employee.add_qualification(123)  # type: ignore

    def test_remove_qualification(self):
        """Test removing a qualification from an employee."""
        # Add qualifications
        self.employee.add_qualification("Workstation1")
        self.employee.add_qualification("Workstation2")
        self.employee.clear_domain_events()

        # Remove a qualification
        result = self.employee.remove_qualification("Workstation1")
        self.assertTrue(result)
        self.assertEqual(self.employee.qualifications, ["Workstation2"])

        # Check that a domain event was raised
        events = self.employee.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], QualificationRemoved)
        self.assertEqual(events[0].employee_id, 1)
        self.assertEqual(events[0].qualification, "Workstation1")

        # Try to remove a non-existent qualification
        result = self.employee.remove_qualification("NonExistent")
        self.assertFalse(result)
        self.assertEqual(self.employee.qualifications, ["Workstation2"])

        # Test invalid qualification
        with self.assertRaises(ValueError):
            self.employee.remove_qualification("")
        with self.assertRaises(ValueError):
            self.employee.remove_qualification(123)  # type: ignore

    def test_assign_role(self):
        """Test assigning a role to an employee."""
        # Assign a role
        result = self.employee.assign_role("Manager")
        self.assertTrue(result)
        self.assertEqual(self.employee.roles, ["Manager"])

        # Check that a domain event was raised
        events = self.employee.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], RoleAssigned)
        self.assertEqual(events[0].employee_id, 1)
        self.assertEqual(events[0].role, "Manager")

        # Try to assign the same role again
        result = self.employee.assign_role("Manager")
        self.assertFalse(result)
        self.assertEqual(self.employee.roles, ["Manager"])

        # Clear events and assign another role
        self.employee.clear_domain_events()
        result = self.employee.assign_role("Supervisor")
        self.assertTrue(result)
        self.assertEqual(self.employee.roles, ["Manager", "Supervisor"])

        # Check that a new domain event was raised
        events = self.employee.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], RoleAssigned)
        self.assertEqual(events[0].role, "Supervisor")

        # Test invalid role
        with self.assertRaises(ValueError):
            self.employee.assign_role("")
        with self.assertRaises(ValueError):
            self.employee.assign_role(123)  # type: ignore

    def test_add_team_role(self):
        """Test adding a team role to an employee."""
        # Create a team membership
        team_member = TeamMember(
            team_member_id=1,
            team_id=1,
            employee_id=1,
            roles=[]
        )
        self.employee._team_memberships.append(team_member)

        # Add a team role
        result = self.employee.add_team_role("TeamLead", 1)
        self.assertTrue(result)
        self.assertEqual(self.employee.get_team_roles(1), ["TeamLead"])

        # Check that a domain event was raised
        events = self.employee.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TeamRoleAssigned)
        self.assertEqual(events[0].employee_id, 1)
        self.assertEqual(events[0].team_id, 1)
        self.assertEqual(events[0].role, "TeamLead")

        # Try to add the same role again
        result = self.employee.add_team_role("TeamLead", 1)
        self.assertFalse(result)
        self.assertEqual(self.employee.get_team_roles(1), ["TeamLead"])

        # Try to add a role to a non-existent team
        result = self.employee.add_team_role("TeamLead", 999)
        self.assertFalse(result)

        # Test invalid role
        with self.assertRaises(ValueError):
            self.employee.add_team_role("", 1)
        with self.assertRaises(ValueError):
            self.employee.add_team_role(123, 1)  # type: ignore
        with self.assertRaises(ValueError):
            self.employee.add_team_role("TeamLead", "1")  # type: ignore

    def test_has_team_role(self):
        """Test checking if an employee has a team role."""
        # Create a team membership with roles
        team_member = TeamMember(
            team_member_id=1,
            team_id=1,
            employee_id=1,
            roles=["TeamLead", "Trainer"]
        )
        self.employee._team_memberships.append(team_member)

        # Check roles
        self.assertTrue(self.employee.has_team_role("TeamLead", 1))
        self.assertTrue(self.employee.has_team_role("Trainer", 1))
        self.assertFalse(self.employee.has_team_role("Manager", 1))
        self.assertFalse(self.employee.has_team_role("TeamLead", 2))  # Non-existent team

    def test_add_work_history_entry(self):
        """Test adding a work history entry."""
        # Add a work history entry
        today = date.today()
        result = self.employee.add_work_history_entry(101, today, 1)
        self.assertTrue(result)

        # Check the work history
        history = self.employee.work_history
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].employee_id, 1)
        self.assertEqual(history[0].workstation_id, 101)
        self.assertEqual(history[0].worked_date, today)
        self.assertEqual(history[0].work_period, 1)
        self.assertFalse(history[0].end_flag)

        # Check that a domain event was raised
        events = self.employee.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkHistoryEntryAdded)
        self.assertEqual(events[0].employee_id, 1)
        self.assertEqual(events[0].workstation_id, 101)
        self.assertEqual(events[0].worked_date, today)
        self.assertEqual(events[0].work_period, 1)

        # Test invalid parameters
        with self.assertRaises(ValueError):
            self.employee.add_work_history_entry(-1, today, 1)
        with self.assertRaises(ValueError):
            self.employee.add_work_history_entry(101, "today", 1)  # type: ignore
        with self.assertRaises(ValueError):
            self.employee.add_work_history_entry(101, today, 0)
        with self.assertRaises(ValueError):
            self.employee.add_work_history_entry(101, today, 6)

    def test_assign_workstation(self):
        """Test assigning a workstation to an employee."""
        # Assign a workstation
        result = self.employee.assign_workstation(101, "Workstation1")
        self.assertTrue(result)

        # Check the assigned workstations
        workstations = self.employee.assigned_workstations
        self.assertEqual(len(workstations), 1)
        self.assertEqual(workstations[0].employee_id, 1)
        self.assertEqual(workstations[0].workstation_id, 101)
        self.assertEqual(workstations[0].workstation_name, "Workstation1")

        # Try to assign the same workstation again
        result = self.employee.assign_workstation(101, "Workstation1")
        self.assertFalse(result)
        self.assertEqual(len(self.employee.assigned_workstations), 1)

        # Test invalid parameters
        with self.assertRaises(ValueError):
            self.employee.assign_workstation(-1, "Workstation1")
        with self.assertRaises(ValueError):
            self.employee.assign_workstation(101, "")
        with self.assertRaises(ValueError):
            self.employee.assign_workstation(101, 123)  # type: ignore

    def test_is_available_for_period(self):
        """Test checking if an employee is available for a period."""
        today = date.today()

        # By default, employees are available
        self.assertTrue(self.employee.is_available_for_period(today))
        self.assertTrue(self.employee.is_available_for_period(today, 1))

        # Add unavailability for a specific period
        self.employee._available_periods.append(
            EmployeeAvailability(
                employee_id=1,
                date=today,
                period=2,
                status=AvailabilityStatus.PARTIAL
            )
        )

        # Check availability
        self.assertTrue(self.employee.is_available_for_period(today))  # Still available for the day
        self.assertTrue(self.employee.is_available_for_period(today, 1))  # Available for period 1
        self.assertFalse(self.employee.is_available_for_period(today, 2))  # Unavailable for period 2

        # Add full day unavailability
        self.employee._available_periods.append(
            EmployeeAvailability(
                employee_id=1,
                date=today,
                status=AvailabilityStatus.CALL_IN
            )
        )

        # Check availability
        self.assertFalse(self.employee.is_available_for_period(today))  # Unavailable for the day
        self.assertFalse(self.employee.is_available_for_period(today, 1))  # Unavailable for all periods

    def test_can_work(self):
        """Test checking if an employee can work at a workstation."""
        # Create a mock workstation
        class MockWorkstation:
            def __init__(self, name):
                self.name = name
                self.is_heavy_job = False
                self.is_key_skill_job = False
                self.line_type = "Mainline"

            def is_heavy(self):
                return self.is_heavy_job

            def requires_key_skill(self):
                return self.is_key_skill_job

        # Employee is not qualified initially
        workstation = MockWorkstation("Workstation1")
        self.assertFalse(self.employee.can_work(workstation))

        # Add qualification
        self.employee.add_qualification("Workstation1")
        self.assertTrue(self.employee.can_work(workstation))

        # Test with a different workstation
        workstation2 = MockWorkstation("Workstation2")
        self.assertFalse(self.employee.can_work(workstation2))

    def test_can_handle_workstation_type(self):
        """Test checking if an employee can handle a workstation type."""
        # Create a mock workstation
        class MockWorkstation:
            def __init__(self, name, is_heavy=False, is_key_skill=False):
                self.name = name
                self.is_heavy_job = is_heavy
                self.is_key_skill_job = is_key_skill
                self.line_type = "Mainline"

            def is_heavy(self):
                return self.is_heavy_job

            def requires_key_skill(self):
                return self.is_key_skill_job

        # Regular workstation
        workstation = MockWorkstation("Workstation1")
        self.assertTrue(self.employee.can_handle_workstation_type(workstation))

        # Heavy workstation
        heavy_workstation = MockWorkstation("HeavyWorkstation", is_heavy=True)
        self.assertFalse(self.employee.can_handle_workstation_type(heavy_workstation))

        # Add heavy lifting certification
        self.employee.assign_role("heavy_lifting_certified")
        self.assertTrue(self.employee.can_handle_workstation_type(heavy_workstation))

        # Key skill workstation
        key_skill_workstation = MockWorkstation("KeySkillWorkstation", is_key_skill=True)
        self.assertFalse(self.employee.can_handle_workstation_type(key_skill_workstation))

        # Add key skill certification
        self.employee.assign_role("key_skill_certified")
        self.assertTrue(self.employee.can_handle_workstation_type(key_skill_workstation))

    def test_is_qualified_for_line(self):
        """Test checking if an employee is qualified for a line type."""
        # Not qualified initially
        self.assertFalse(self.employee.is_qualified_for_line("Mainline"))

        # Add qualification
        self.employee.add_qualification("Mainline_qualified")
        self.assertTrue(self.employee.is_qualified_for_line("Mainline"))

        # Test with a different line type
        self.assertFalse(self.employee.is_qualified_for_line("SubAssembly"))

    def test_can_substitute_for(self):
        """Test checking if an employee can substitute for a workstation."""
        # Create a mock workstation
        class MockWorkstation:
            def __init__(self, name, is_heavy=False, is_key_skill=False, line_type="Mainline"):
                self.name = name
                self.is_heavy_job = is_heavy
                self.is_key_skill_job = is_key_skill
                self.line_type = line_type

            def is_heavy(self):
                return self.is_heavy_job

            def requires_key_skill(self):
                return self.is_key_skill_job

        # Regular workstation
        workstation = MockWorkstation("Workstation1")

        # Not qualified initially
        self.assertFalse(self.employee.can_substitute_for(workstation))

        # Add workstation qualification
        self.employee.add_qualification("Workstation1")

        # Still not qualified for line type
        self.assertFalse(self.employee.can_substitute_for(workstation))

        # Add line type qualification
        self.employee.add_qualification("Mainline_qualified")
        self.assertTrue(self.employee.can_substitute_for(workstation))

        # Heavy workstation
        heavy_workstation = MockWorkstation("HeavyWorkstation", is_heavy=True)
        self.employee.add_qualification("HeavyWorkstation")

        # Not qualified for heavy workstation
        self.assertFalse(self.employee.can_substitute_for(heavy_workstation))

        # Add heavy lifting certification
        self.employee.assign_role("heavy_lifting_certified")
        self.assertTrue(self.employee.can_substitute_for(heavy_workstation))


if __name__ == "__main__":
    unittest.main()
