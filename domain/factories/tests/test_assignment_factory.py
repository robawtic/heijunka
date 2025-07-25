# domain/factories/tests/test_assignment_factory.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import date

from domain.factories.assignment_factory import AssignmentFactory
from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment

class TestAssignmentFactory(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create mock employee
        self.employee = MagicMock(spec=Employee)
        self.employee.id = 1
        self.employee.name = "Test Employee"
        self.employee.can_work.return_value = True
        self.employee.is_available_for_period.return_value = True
        
        # Create mock workstation
        self.workstation = MagicMock(spec=Workstation)
        self.workstation.id = 2
        self.workstation.name = "Test Workstation"
        
        # Create schedule period
        self.today = date.today()
        self.period = SchedulePeriod(date=self.today, period=1)
    
    def test_create_assignment_basic(self):
        """Test basic assignment creation with AssignmentFactory."""
        assignment = AssignmentFactory.create_assignment(
            employee=self.employee,
            workstation=self.workstation,
            period=self.period
        )
        
        self.assertIsInstance(assignment, WorkAssignment)
        self.assertEqual(assignment.employee, self.employee)
        self.assertEqual(assignment.workstation, self.workstation)
        self.assertEqual(assignment.period, self.period)
        
        # Verify validation calls
        self.employee.can_work.assert_called_once_with(self.workstation)
        self.employee.is_available_for_period.assert_called_once_with(self.today, 1)
    
    def test_create_assignment_validation_failure(self):
        """Test assignment creation with validation failures."""
        # Employee cannot work at workstation
        self.employee.can_work.return_value = False
        
        with self.assertRaises(ValueError) as context:
            AssignmentFactory.create_assignment(
                employee=self.employee,
                workstation=self.workstation,
                period=self.period
            )
        
        self.assertIn("cannot work at", str(context.exception))
        
        # Reset can_work
        self.employee.can_work.return_value = True
        
        # Employee not available for period
        self.employee.is_available_for_period.return_value = False
        
        with self.assertRaises(ValueError) as context:
            AssignmentFactory.create_assignment(
                employee=self.employee,
                workstation=self.workstation,
                period=self.period
            )
        
        self.assertIn("not available on", str(context.exception))
    
    def test_create_assignment_for_date(self):
        """Test creating an assignment for a specific date and period number."""
        assignment = AssignmentFactory.create_assignment_for_date(
            employee=self.employee,
            workstation=self.workstation,
            assignment_date=self.today,
            period_number=2
        )
        
        self.assertIsInstance(assignment, WorkAssignment)
        self.assertEqual(assignment.employee, self.employee)
        self.assertEqual(assignment.workstation, self.workstation)
        self.assertEqual(assignment.period.date, self.today)
        self.assertEqual(assignment.period.period, 2)
    
    def test_create_assignment_if_qualified(self):
        """Test creating an assignment only if the employee is qualified."""
        # Employee is qualified
        assignment = AssignmentFactory.create_assignment_if_qualified(
            employee=self.employee,
            workstation=self.workstation,
            period=self.period
        )
        
        self.assertIsInstance(assignment, WorkAssignment)
        
        # Employee is not qualified
        self.employee.can_work.return_value = False
        
        assignment = AssignmentFactory.create_assignment_if_qualified(
            employee=self.employee,
            workstation=self.workstation,
            period=self.period
        )
        
        self.assertIsNone(assignment)

if __name__ == "__main__":
    unittest.main()