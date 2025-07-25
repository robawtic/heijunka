# domain/factories/tests/test_factories.py
import unittest
from datetime import date

from domain.factories.employee_factory import EmployeeFactory
from domain.factories.workstation_factory import WorkstationFactory
from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.employee_management.value_objects.employee_availability import EmployeeAvailability, AvailabilityStatus
from domain.contexts.employee_management.entities.team_member import TeamMember
from domain.contexts.assignment.value_objects.workstation_assignment import WorkstationAssignment


class TestFactories(unittest.TestCase):
    def test_employee_factory_basic(self):
        """Test basic employee creation with EmployeeFactory."""
        employee = EmployeeFactory.create_employee(
            id=1,
            name="John Doe",
            team_id=2,
            is_active=True,
            roles=["Associate", "Backup"],
            qualifications=["H010", "H080/H090"]
        )

        self.assertEqual(employee.id, 1)
        self.assertEqual(employee.name, "John Doe")
        self.assertEqual(employee.team_id, 2)
        self.assertTrue(employee.is_active)
        self.assertEqual(employee.roles, ["Associate", "Backup"])
        self.assertEqual(employee.qualifications, ["H010", "H080/H090"])

    def test_employee_factory_with_availability(self):
        """Test employee creation with availability."""
        today = date.today()
        availability = EmployeeAvailability(
            employee_id=1,
            date=today,
            status=AvailabilityStatus.CALL_IN,
            period=None
        )

        employee = EmployeeFactory.create_employee_with_availability(
            id=1,
            name="Jane Smith",
            team_id=2,
            availabilities=[availability]
        )

        self.assertEqual(employee.id, 1)
        self.assertEqual(employee.name, "Jane Smith")
        self.assertEqual(len(employee.available_periods), 1)
        self.assertEqual(employee.available_periods[0].date, today)
        self.assertEqual(employee.available_periods[0].status, AvailabilityStatus.CALL_IN)

    def test_workstation_factory_basic(self):
        """Test basic workstation creation with WorkstationFactory."""
        workstation = WorkstationFactory.create_workstation(
            id=1,
            name="H010",
            line_type="Sub-Assembly",
            is_loading_job=True,
            team_id=2
        )

        self.assertEqual(workstation.id, 1)
        self.assertEqual(workstation.name, "H010")
        self.assertEqual(workstation.line_type, "Sub-Assembly")
        self.assertTrue(workstation.is_loading_job)
        self.assertFalse(workstation.is_heavy_job)
        self.assertFalse(workstation.is_key_skill_job)
        self.assertEqual(workstation.team_id, 2)

    def test_workstation_factory_specialized(self):
        """Test specialized workstation creation methods."""
        # Test loading workstation
        loading_ws = WorkstationFactory.create_loading_workstation(
            id=2,
            name="H020",
            line_type="Sub-Assembly",
            team_id=2
        )
        self.assertTrue(loading_ws.is_loading_job)

        # Test heavy workstation
        heavy_ws = WorkstationFactory.create_heavy_workstation(
            id=3,
            name="H030",
            line_type="Sub-Assembly",
            team_id=2
        )
        self.assertTrue(heavy_ws.is_heavy_job)
        self.assertTrue(heavy_ws.is_loading_job)  # Heavy jobs are typically loading jobs

        # Test key skill workstation
        key_skill_ws = WorkstationFactory.create_key_skill_workstation(
            id=4,
            name="H040",
            line_type="Sub-Assembly",
            team_id=2
        )
        self.assertTrue(key_skill_ws.is_key_skill_job)


if __name__ == "__main__":
    unittest.main()
