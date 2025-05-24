# heijunka/domain/entities/tests/test_schedule.py
import unittest
from datetime import date

from domain.entities.schedule import Schedule
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.events import (
    ScheduleCreated, ScheduleUpdated, ScheduleStatusChanged, 
    AssignmentAdded, AssignmentRemoved
)


class TestSchedule(unittest.TestCase):
    def setUp(self):
        """Set up a new schedule for each test."""
        self.today = date.today()
        self.schedule = Schedule(
            id=1,
            team_id=1,
            start_date=self.today,
            days=1,
            periods_per_day=4,
            status="pending"
        )
        # Clear the creation event
        self.schedule.clear_domain_events()
        
        # Create test employees and workstations
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
        """Test that a schedule is properly initialized."""
        schedule = Schedule(
            id=2,
            team_id=1,
            start_date=self.today,
            days=2,
            periods_per_day=4,
            status="pending",
            call_ins=["John Doe"],
            offline={"Jane Smith": [1, 2]},
            force_complete=True
        )
        
        # Check properties
        self.assertEqual(schedule.id, 2)
        self.assertEqual(schedule.team_id, 1)
        self.assertEqual(schedule.start_date, self.today)
        self.assertEqual(schedule.days, 2)
        self.assertEqual(schedule.periods_per_day, 4)
        self.assertEqual(schedule.status, "pending")
        self.assertEqual(schedule.call_ins, ["John Doe"])
        self.assertEqual(schedule.offline, {"Jane Smith": [1, 2]})
        self.assertTrue(schedule.force_complete)
        self.assertEqual(schedule.assignments, [])
        
        # Check that a creation event was raised
        events = schedule.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], ScheduleCreated)
        self.assertEqual(events[0].schedule_id, 2)
        self.assertEqual(events[0].team_id, 1)
        self.assertEqual(events[0].start_date, self.today)
        self.assertEqual(events[0].days, 2)
        self.assertEqual(events[0].periods_per_day, 4)

    def test_add_assignment(self):
        """Test adding an assignment to the schedule."""
        # Create a period and assignment
        period = SchedulePeriod(date=self.today, period=1)
        assignment = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation1,
            period=period
        )
        
        # Add the assignment
        result = self.schedule.add_assignment(assignment)
        self.assertTrue(result)
        self.assertEqual(len(self.schedule.assignments), 1)
        self.assertEqual(self.schedule.assignments[0].employee.id, 1)
        self.assertEqual(self.schedule.assignments[0].workstation.id, 1)
        self.assertEqual(self.schedule.assignments[0].period.date, self.today)
        self.assertEqual(self.schedule.assignments[0].period.period, 1)
        
        # Check that a domain event was raised
        events = self.schedule.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], AssignmentAdded)
        self.assertEqual(events[0].schedule_id, 1)
        self.assertEqual(events[0].employee_id, 1)
        self.assertEqual(events[0].workstation_id, 1)
        self.assertEqual(events[0].period.date, self.today)
        self.assertEqual(events[0].period.period, 1)
        
        # Try to add the same assignment again
        self.schedule.clear_domain_events()
        result = self.schedule.add_assignment(assignment)
        self.assertFalse(result)  # Should return False for duplicate
        self.assertEqual(len(self.schedule.assignments), 1)  # Should still have only one assignment
        self.assertEqual(len(self.schedule.domain_events), 0)  # No event should be raised
        
        # Add a different assignment
        period2 = SchedulePeriod(date=self.today, period=2)
        assignment2 = WorkAssignment(
            employee=self.employee2,
            workstation=self.workstation2,
            period=period2
        )
        
        result = self.schedule.add_assignment(assignment2)
        self.assertTrue(result)
        self.assertEqual(len(self.schedule.assignments), 2)
        
        # Check that a domain event was raised
        events = self.schedule.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], AssignmentAdded)
        self.assertEqual(events[0].employee_id, 2)
        self.assertEqual(events[0].workstation_id, 2)
        
        # Test invalid assignment
        with self.assertRaises(ValueError):
            self.schedule.add_assignment("not an assignment")

    def test_remove_assignment(self):
        """Test removing an assignment from the schedule."""
        # Add assignments
        period1 = SchedulePeriod(date=self.today, period=1)
        assignment1 = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation1,
            period=period1
        )
        
        period2 = SchedulePeriod(date=self.today, period=2)
        assignment2 = WorkAssignment(
            employee=self.employee2,
            workstation=self.workstation2,
            period=period2
        )
        
        self.schedule.add_assignment(assignment1)
        self.schedule.add_assignment(assignment2)
        self.schedule.clear_domain_events()
        
        # Remove an assignment
        result = self.schedule.remove_assignment(1, 1, period1)
        self.assertTrue(result)
        self.assertEqual(len(self.schedule.assignments), 1)
        self.assertEqual(self.schedule.assignments[0].employee.id, 2)
        
        # Check that a domain event was raised
        events = self.schedule.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], AssignmentRemoved)
        self.assertEqual(events[0].schedule_id, 1)
        self.assertEqual(events[0].employee_id, 1)
        self.assertEqual(events[0].workstation_id, 1)
        self.assertEqual(events[0].period.date, self.today)
        self.assertEqual(events[0].period.period, 1)
        
        # Try to remove a non-existent assignment
        self.schedule.clear_domain_events()
        result = self.schedule.remove_assignment(999, 999, period1)
        self.assertFalse(result)
        self.assertEqual(len(self.schedule.assignments), 1)
        self.assertEqual(len(self.schedule.domain_events), 0)  # No event should be raised

    def test_get_assignments_for_date(self):
        """Test getting assignments for a specific date."""
        # Add assignments for today
        period1 = SchedulePeriod(date=self.today, period=1)
        assignment1 = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation1,
            period=period1
        )
        
        period2 = SchedulePeriod(date=self.today, period=2)
        assignment2 = WorkAssignment(
            employee=self.employee2,
            workstation=self.workstation2,
            period=period2
        )
        
        self.schedule.add_assignment(assignment1)
        self.schedule.add_assignment(assignment2)
        
        # Add an assignment for tomorrow
        tomorrow = date.fromordinal(self.today.toordinal() + 1)
        period3 = SchedulePeriod(date=tomorrow, period=1)
        assignment3 = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation1,
            period=period3
        )
        
        self.schedule.add_assignment(assignment3)
        
        # Get assignments for today
        assignments = self.schedule.get_assignments_for_date(self.today)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0].period.date, self.today)
        self.assertEqual(assignments[1].period.date, self.today)
        
        # Get assignments for tomorrow
        assignments = self.schedule.get_assignments_for_date(tomorrow)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].period.date, tomorrow)
        
        # Get assignments for a date with no assignments
        yesterday = date.fromordinal(self.today.toordinal() - 1)
        assignments = self.schedule.get_assignments_for_date(yesterday)
        self.assertEqual(len(assignments), 0)

    def test_get_assignments_for_employee(self):
        """Test getting assignments for a specific employee."""
        # Add assignments for employee1
        period1 = SchedulePeriod(date=self.today, period=1)
        assignment1 = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation1,
            period=period1
        )
        
        period2 = SchedulePeriod(date=self.today, period=2)
        assignment2 = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation2,
            period=period2
        )
        
        self.schedule.add_assignment(assignment1)
        self.schedule.add_assignment(assignment2)
        
        # Add an assignment for employee2
        period3 = SchedulePeriod(date=self.today, period=3)
        assignment3 = WorkAssignment(
            employee=self.employee2,
            workstation=self.workstation1,
            period=period3
        )
        
        self.schedule.add_assignment(assignment3)
        
        # Get assignments for employee1
        assignments = self.schedule.get_assignments_for_employee(1)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0].employee.id, 1)
        self.assertEqual(assignments[1].employee.id, 1)
        
        # Get assignments for employee2
        assignments = self.schedule.get_assignments_for_employee(2)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].employee.id, 2)
        
        # Get assignments for a non-existent employee
        assignments = self.schedule.get_assignments_for_employee(999)
        self.assertEqual(len(assignments), 0)

    def test_get_assignments_for_workstation(self):
        """Test getting assignments for a specific workstation."""
        # Add assignments for workstation1
        period1 = SchedulePeriod(date=self.today, period=1)
        assignment1 = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation1,
            period=period1
        )
        
        period2 = SchedulePeriod(date=self.today, period=2)
        assignment2 = WorkAssignment(
            employee=self.employee2,
            workstation=self.workstation1,
            period=period2
        )
        
        self.schedule.add_assignment(assignment1)
        self.schedule.add_assignment(assignment2)
        
        # Add an assignment for workstation2
        period3 = SchedulePeriod(date=self.today, period=3)
        assignment3 = WorkAssignment(
            employee=self.employee1,
            workstation=self.workstation2,
            period=period3
        )
        
        self.schedule.add_assignment(assignment3)
        
        # Get assignments for workstation1
        assignments = self.schedule.get_assignments_for_workstation(1)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0].workstation.id, 1)
        self.assertEqual(assignments[1].workstation.id, 1)
        
        # Get assignments for workstation2
        assignments = self.schedule.get_assignments_for_workstation(2)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].workstation.id, 2)
        
        # Get assignments for a non-existent workstation
        assignments = self.schedule.get_assignments_for_workstation(999)
        self.assertEqual(len(assignments), 0)

    def test_set_status(self):
        """Test setting the status of the schedule."""
        # Set the status
        result = self.schedule.set_status("completed")
        self.assertTrue(result)
        self.assertEqual(self.schedule.status, "completed")
        
        # Check that a domain event was raised
        events = self.schedule.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], ScheduleStatusChanged)
        self.assertEqual(events[0].schedule_id, 1)
        self.assertEqual(events[0].old_status, "pending")
        self.assertEqual(events[0].new_status, "completed")
        
        # Try to set the same status again
        self.schedule.clear_domain_events()
        result = self.schedule.set_status("completed")
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.schedule.domain_events), 0)  # No event should be raised
        
        # Test invalid status
        with self.assertRaises(ValueError):
            self.schedule.set_status("")
        with self.assertRaises(ValueError):
            self.schedule.set_status(None)

    def test_set_error_message(self):
        """Test setting the error message of the schedule."""
        # Set the error message
        result = self.schedule.set_error_message("An error occurred")
        self.assertTrue(result)
        self.assertEqual(self.schedule.error_message, "An error occurred")
        
        # Try to set the same error message again
        result = self.schedule.set_error_message("An error occurred")
        self.assertFalse(result)  # Should return False for no change
        
        # Set a different error message
        result = self.schedule.set_error_message("A different error")
        self.assertTrue(result)
        self.assertEqual(self.schedule.error_message, "A different error")
        
        # Clear the error message
        result = self.schedule.set_error_message(None)
        self.assertTrue(result)
        self.assertIsNone(self.schedule.error_message)

    def test_update(self):
        """Test updating multiple properties of the schedule at once."""
        # Update multiple properties
        self.schedule.update(
            status="completed",
            error_message="No errors",
            task_id="task123"
        )
        
        # Check that properties were updated
        self.assertEqual(self.schedule.status, "completed")
        self.assertEqual(self.schedule.error_message, "No errors")
        self.assertEqual(self.schedule.task_id, "task123")
        
        # Check that domain events were raised
        events = self.schedule.domain_events
        # Should be at least 2 events: status change and update
        self.assertGreaterEqual(len(events), 2)
        
        # Verify we have the ScheduleStatusChanged event
        status_events = [e for e in events if isinstance(e, ScheduleStatusChanged)]
        self.assertEqual(len(status_events), 1)
        
        # Verify we have the ScheduleUpdated event
        update_events = [e for e in events if isinstance(e, ScheduleUpdated)]
        self.assertEqual(len(update_events), 1)
        
        # Update with no changes
        self.schedule.clear_domain_events()
        self.schedule.update(
            status="completed",
            error_message="No errors",
            task_id="task123"
        )
        
        # No events should be raised
        self.assertEqual(len(self.schedule.domain_events), 0)
        
        # Update with some changes
        self.schedule.update(
            status="failed",
            error_message="An error occurred"
        )
        
        # Check that properties were updated
        self.assertEqual(self.schedule.status, "failed")
        self.assertEqual(self.schedule.error_message, "An error occurred")
        
        # Check that domain events were raised
        events = self.schedule.domain_events
        # Should be at least 2 events: status change and update
        self.assertGreaterEqual(len(events), 2)

    def test_validate(self):
        """Test validating the schedule entity."""
        # Valid schedule
        self.schedule.validate()  # Should not raise an exception
        
        # Test invalid team_id
        schedule = Schedule(
            id=1,
            team_id=0,  # Invalid
            start_date=self.today,
            days=1,
            periods_per_day=4,
            status="pending"
        )
        with self.assertRaises(ValueError):
            schedule.validate()
        
        # Test invalid start_date
        schedule = Schedule(
            id=1,
            team_id=1,
            start_date="2023-01-01",  # Invalid
            days=1,
            periods_per_day=4,
            status="pending"
        )
        with self.assertRaises(ValueError):
            schedule.validate()
        
        # Test invalid days
        schedule = Schedule(
            id=1,
            team_id=1,
            start_date=self.today,
            days=0,  # Invalid
            periods_per_day=4,
            status="pending"
        )
        with self.assertRaises(ValueError):
            schedule.validate()
        
        # Test invalid periods_per_day
        schedule = Schedule(
            id=1,
            team_id=1,
            start_date=self.today,
            days=1,
            periods_per_day=0,  # Invalid
            status="pending"
        )
        with self.assertRaises(ValueError):
            schedule.validate()
        
        # Test invalid status
        schedule = Schedule(
            id=1,
            team_id=1,
            start_date=self.today,
            days=1,
            periods_per_day=4,
            status=""  # Invalid
        )
        with self.assertRaises(ValueError):
            schedule.validate()


if __name__ == "__main__":
    unittest.main()