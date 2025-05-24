import unittest
from datetime import date

from domain.entities.schedule import Schedule
from domain.repositories.tests.mock_schedule_repository import MockScheduleRepository


class TestScheduleRepository(unittest.TestCase):
    def setUp(self):
        """Set up a new mock repository for each test."""
        self.repo = MockScheduleRepository()

        # Add some test schedules
        self.schedule1 = Schedule(
            id=1,
            team_id=1,
            start_date=date(2023, 1, 1),
            days=5,
            periods_per_day=4,
            status="completed",
            call_ins=["John Doe"],
            offline={"Jane Smith": [1, 2]},
            force_complete=False
        )
        self.schedule2 = Schedule(
            id=2,
            team_id=1,
            start_date=date(2023, 1, 8),
            days=5,
            periods_per_day=4,
            status="pending",
            call_ins=[],
            offline={},
            force_complete=False
        )
        self.schedule3 = Schedule(
            id=3,
            team_id=2,
            start_date=date(2023, 1, 15),
            days=5,
            periods_per_day=4,
            status="failed",
            call_ins=[],
            offline={},
            force_complete=True,
            error_message="No solution found"
        )

        self.repo.add(self.schedule1)
        self.repo.add(self.schedule2)
        self.repo.add(self.schedule3)

    def test_get_by_id(self):
        """Test retrieving a schedule by ID."""
        schedule = self.repo.get_by_id(1)
        self.assertEqual(schedule.team_id, 1)
        self.assertEqual(schedule.start_date, date(2023, 1, 1))

        # Test non-existent schedule
        self.assertIsNone(self.repo.get_by_id(999))

    def test_list_all(self):
        """Test retrieving all schedules."""
        schedules = self.repo.list_all()
        self.assertEqual(len(schedules), 3)

    def test_add(self):
        """Test adding a new schedule."""
        new_schedule = Schedule(
            id=4,
            team_id=2,
            start_date=date(2023, 1, 22),
            days=5,
            periods_per_day=4,
            status="pending",
            call_ins=[],
            offline={},
            force_complete=False
        )
        self.repo.add(new_schedule)

        # Verify the schedule was added
        self.assertEqual(len(self.repo.list_all()), 4)
        self.assertEqual(self.repo.get_by_id(4).start_date, date(2023, 1, 22))

    def test_update(self):
        """Test updating an existing schedule."""
        # Update schedule1's status
        self.schedule1.status = "failed"
        self.repo.update(self.schedule1)

        # Verify the update
        self.assertEqual(self.repo.get_by_id(1).status, "failed")

    def test_delete(self):
        """Test deleting a schedule."""
        self.assertTrue(self.repo.delete(1))
        self.assertIsNone(self.repo.get_by_id(1))
        self.assertEqual(len(self.repo.list_all()), 2)

        # Test deleting non-existent schedule
        self.assertFalse(self.repo.delete(999))

    def test_get_by_task_id(self):
        """Test retrieving a schedule by task ID."""
        # Set a task ID for schedule1
        self.schedule1.task_id = "task123"
        self.repo.update(self.schedule1)

        # Retrieve by task ID
        schedule = self.repo.get_by_task_id("task123")
        self.assertEqual(schedule.id, 1)

        # Test non-existent task ID
        self.assertIsNone(self.repo.get_by_task_id("nonexistent"))

    def test_get_by_team_id(self):
        """Test retrieving schedules by team ID with filtering and pagination."""
        # Get all schedules for team 1
        team1_schedules = self.repo.get_by_team_id(1)
        self.assertEqual(len(team1_schedules), 2)

        # Get schedules for team 1 with start date filter
        filtered_schedules = self.repo.get_by_team_id(1, start_date=date(2023, 1, 5))
        self.assertEqual(len(filtered_schedules), 1)
        self.assertEqual(filtered_schedules[0].id, 2)

        # Get schedules for team 1 with status filter
        status_schedules = self.repo.get_by_team_id(1, status="completed")
        self.assertEqual(len(status_schedules), 1)
        self.assertEqual(status_schedules[0].id, 1)

        # Test pagination
        paginated_schedules = self.repo.get_by_team_id(1, skip=1, limit=1)
        self.assertEqual(len(paginated_schedules), 1)
        self.assertEqual(paginated_schedules[0].id, 2)

    def test_create_schedule(self):
        """Test creating a new schedule."""
        schedule = self.repo.create_schedule(
            team_id=3,
            start_date=date(2023, 1, 29),
            days=5,
            periods_per_day=4,
            call_ins=["Bob Johnson"],
            offline=["Alice Brown:1,2"],
            force_complete=True
        )

        # Verify the schedule was created
        self.assertEqual(schedule.team_id, 3)
        self.assertEqual(schedule.start_date, date(2023, 1, 29))
        self.assertEqual(schedule.days, 5)
        self.assertEqual(schedule.periods_per_day, 4)
        self.assertEqual(schedule.call_ins, ["Bob Johnson"])
        self.assertEqual(schedule.offline, {"Alice Brown": [1, 2]})
        self.assertTrue(schedule.force_complete)
        self.assertEqual(schedule.status, "pending")

        # Verify it was added to the repository
        self.assertEqual(len(self.repo.list_all()), 4)

    def test_update_status(self):
        """Test updating the status of a schedule."""
        # Update schedule2's status
        updated_schedule = self.repo.update_status(2, "completed", "Success")
        self.assertEqual(updated_schedule.status, "completed")
        self.assertEqual(updated_schedule.error_message, "Success")

        # Verify the update in the repository
        self.assertEqual(self.repo.get_by_id(2).status, "completed")
        self.assertEqual(self.repo.get_by_id(2).error_message, "Success")

        # Test updating non-existent schedule
        self.assertIsNone(self.repo.update_status(999, "completed"))

    def test_count(self):
        """Test counting schedules with filtering."""
        # Count all schedules
        self.assertEqual(self.repo.count(), 3)

        # Count schedules for team 1
        self.assertEqual(self.repo.count(team_id=1), 2)

        # Count schedules with start date filter
        self.assertEqual(self.repo.count(start_date=date(2023, 1, 5)), 2)

        # Count schedules with status filter
        self.assertEqual(self.repo.count(status="completed"), 1)

        # Count schedules with multiple filters
        self.assertEqual(self.repo.count(team_id=1, status="pending"), 1)


if __name__ == '__main__':
    unittest.main()
