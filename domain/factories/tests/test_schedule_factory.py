# domain/factories/tests/test_schedule_factory.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta

from domain.factories.schedule_factory import ScheduleFactory
from domain.entities.schedule import Schedule
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment

class TestScheduleFactory(unittest.TestCase):
    def test_create_schedule_basic(self):
        """Test basic schedule creation with ScheduleFactory."""
        today = date.today()
        schedule = ScheduleFactory.create_schedule(
            id=1,
            team_id=2,
            start_date=today,
            periods_per_day=4,
            status="pending"
        )
        
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.team_id, 2)
        self.assertEqual(schedule.start_date, today)
        self.assertEqual(schedule.periods_per_day, 4)
        self.assertEqual(schedule.status, "pending")
        self.assertEqual(len(schedule.assignments), 0)
        self.assertEqual(schedule.call_ins, [])
        self.assertEqual(schedule.offline, {})
        self.assertFalse(schedule.force_complete)
        self.assertIsNone(schedule.error_message)
        self.assertIsNone(schedule.task_id)
    
    def test_create_schedule_with_call_ins(self):
        """Test schedule creation with call-ins."""
        today = date.today()
        schedule = ScheduleFactory.create_schedule(
            id=1,
            team_id=2,
            start_date=today,
            periods_per_day=4,
            status="pending",
            call_ins=["Employee 1", "Employee 2"]
        )
        
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.team_id, 2)
        self.assertEqual(schedule.call_ins, ["Employee 1", "Employee 2"])
    
    def test_create_schedule_with_offline(self):
        """Test schedule creation with offline periods."""
        today = date.today()
        offline = {
            "Employee 1": [1, 2],
            "Employee 2": [3, 4]
        }
        schedule = ScheduleFactory.create_schedule(
            id=1,
            team_id=2,
            start_date=today,
            periods_per_day=4,
            status="pending",
            offline=offline
        )
        
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.team_id, 2)
        self.assertEqual(schedule.offline, offline)
    
    def test_create_daily_schedule(self):
        """Test creating a daily schedule."""
        today = date.today()
        schedule = ScheduleFactory.create_daily_schedule(
            id=1,
            team_id=2,
            start_date=today,
            periods_per_day=4,
            status="pending"
        )
        
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.team_id, 2)
        self.assertEqual(schedule.start_date, today)
        self.assertEqual(schedule.periods_per_day, 4)
        self.assertEqual(schedule.status, "pending")
    
    def test_create_schedule_with_assignments(self):
        """Test creating a schedule with assignments."""
        today = date.today()
        
        # Create mock assignments
        assignment1 = MagicMock(spec=WorkAssignment)
        assignment2 = MagicMock(spec=WorkAssignment)
        
        schedule = ScheduleFactory.create_schedule_with_assignments(
            id=1,
            team_id=2,
            start_date=today,
            periods_per_day=4,
            status="generated",
            assignments=[assignment1, assignment2]
        )
        
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.team_id, 2)
        self.assertEqual(schedule.status, "generated")
        self.assertEqual(len(schedule.assignments), 2)
    
    def test_create_from_model(self):
        """Test creating a schedule from a model."""
        today = date.today()
        
        # Create a mock model
        model = MagicMock()
        model.id = 1
        model.team_id = 2
        model.start_date = today
        model.periods_per_day = 4
        model.status = "generated"
        model.call_ins = ["Employee 1"]
        model.offline = {"Employee 2": [3, 4]}
        model.force_complete = False
        model.error_message = None
        model.task_id = "task-123"
        
        # Mock work history entries
        entry1 = MagicMock()
        entry1.employee = MagicMock()
        entry1.station = MagicMock()
        entry1.worked_date = today
        entry1.work_period = 1
        
        entry2 = MagicMock()
        entry2.employee = MagicMock()
        entry2.station = MagicMock()
        entry2.worked_date = today
        entry2.work_period = 2
        
        model.work_history_entries = [entry1, entry2]
        
        # Mock the factories
        with patch('domain.factories.employee_factory.EmployeeFactory') as mock_employee_factory, \
             patch('domain.factories.workstation_factory.WorkstationFactory') as mock_workstation_factory, \
             patch('domain.factories.assignment_factory.AssignmentFactory') as mock_assignment_factory:
            
            # Setup mock returns
            mock_employee = MagicMock()
            mock_workstation = MagicMock()
            mock_assignment = MagicMock(spec=WorkAssignment)
            
            mock_employee_factory.create_from_model.return_value = mock_employee
            mock_workstation_factory.create_from_model.return_value = mock_workstation
            mock_assignment_factory.create_assignment.return_value = mock_assignment
            
            # Create schedule from model
            schedule = ScheduleFactory.create_from_model(model)
            
            # Verify the schedule
            self.assertEqual(schedule.id, 1)
            self.assertEqual(schedule.team_id, 2)
            self.assertEqual(schedule.start_date, today)
            self.assertEqual(schedule.periods_per_day, 4)
            self.assertEqual(schedule.status, "generated")
            self.assertEqual(schedule.call_ins, ["Employee 1"])
            self.assertEqual(schedule.offline, {"Employee 2": [3, 4]})
            self.assertFalse(schedule.force_complete)
            self.assertIsNone(schedule.error_message)
            self.assertEqual(schedule.task_id, "task-123")
            
            # Verify factory calls
            self.assertEqual(mock_employee_factory.create_from_model.call_count, 2)
            self.assertEqual(mock_workstation_factory.create_from_model.call_count, 2)
            self.assertEqual(mock_assignment_factory.create_assignment.call_count, 2)
    
    def test_create_from_model_without_assignments(self):
        """Test creating a schedule from a model without including assignments."""
        today = date.today()
        
        # Create a mock model
        model = MagicMock()
        model.id = 1
        model.team_id = 2
        model.start_date = today
        model.periods_per_day = 4
        model.status = "pending"
        
        # Create schedule from model without assignments
        schedule = ScheduleFactory.create_from_model(model, include_assignments=False)
        
        # Verify the schedule
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.team_id, 2)
        self.assertEqual(len(schedule.assignments), 0)

if __name__ == "__main__":
    unittest.main()