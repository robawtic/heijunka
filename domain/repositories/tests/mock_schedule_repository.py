from typing import Optional, List
from datetime import date

from domain.contexts.scheduling.entities.model import Schedule
from domain.repositories.interfaces.schedule_repository_interface import ScheduleRepositoryInterface


class MockScheduleRepository(ScheduleRepositoryInterface):
    """
    Mock implementation of the schedule repository for testing.
    """

    def __init__(self):
        self.schedules = {}  # Dictionary of schedules by ID
        self.next_id = 1  # For auto-incrementing IDs

    def get_by_id(self, entity_id: int) -> Optional[Schedule]:
        """Retrieve a schedule by ID."""
        return self.schedules.get(entity_id)

    def list_all(self) -> List[Schedule]:
        """Retrieve all schedules."""
        return list(self.schedules.values())

    def add(self, entity: Schedule) -> Schedule:
        """Add a new schedule."""
        if entity.id <= 0:
            entity.id = self.next_id
            self.next_id += 1
        else:
            # Update next_id if the entity's id is greater than or equal to next_id
            if entity.id >= self.next_id:
                self.next_id = entity.id + 1
        self.schedules[entity.id] = entity
        return entity

    def update(self, entity: Schedule) -> Schedule:
        """Update an existing schedule."""
        self.schedules[entity.id] = entity
        return entity

    def delete(self, entity_id: int) -> bool:
        """Delete a schedule by ID."""
        if entity_id in self.schedules:
            del self.schedules[entity_id]
            return True
        return False

    def get_by_task_id(self, task_id: str) -> Optional[Schedule]:
        """Get a schedule by its task ID."""
        for schedule in self.schedules.values():
            if schedule.task_id == task_id:
                return schedule
        return None

    def get_by_team_id(self, team_id: int, start_date: Optional[date] = None,
                      end_date: Optional[date] = None, status: Optional[str] = None,
                      skip: int = 0, limit: int = 100) -> List[Schedule]:
        """Get all schedules for a specific team with filtering and pagination."""
        result = []

        for schedule in self.schedules.values():
            if schedule.team_id != team_id:
                continue

            if start_date and schedule.start_date < start_date:
                continue

            if end_date and schedule.start_date > end_date:
                continue

            if status and schedule.status != status:
                continue

            result.append(schedule)

        # Apply pagination
        return result[skip:skip+limit]

    def create_schedule(self, team_id: int, start_date: date, days: int, periods_per_day: int, 
                       call_ins: List[str] = None, offline: List[str] = None, 
                       force_complete: bool = False) -> Schedule:
        """Create a new schedule."""
        # Parse offline parameter to convert to the format expected by the Schedule entity
        offline_dict = {}
        if offline:
            for offline_str in offline:
                parts = offline_str.split(':')
                if len(parts) == 2:
                    emp_name, periods_str = parts
                    periods = [int(p) for p in periods_str.split(',')]
                    offline_dict[emp_name] = periods

        # Create a new Schedule entity
        schedule = Schedule(
            id=self.next_id,
            team_id=team_id,
            start_date=start_date,
            days=days,
            periods_per_day=periods_per_day,
            status="pending",
            call_ins=call_ins or [],
            offline=offline_dict,
            force_complete=force_complete
        )

        self.next_id += 1
        self.schedules[schedule.id] = schedule

        return schedule

    def update_status(self, schedule_id: int, status: str, error_message: Optional[str] = None) -> Optional[Schedule]:
        """Update the status of a schedule."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None

        schedule.status = status
        if error_message is not None:
            schedule.error_message = error_message

        return schedule

    def count(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
             end_date: Optional[date] = None, status: Optional[str] = None) -> int:
        """Count schedules with filtering."""
        count = 0

        for schedule in self.schedules.values():
            if team_id and schedule.team_id != team_id:
                continue

            if start_date and schedule.start_date < start_date:
                continue

            if end_date and schedule.start_date > end_date:
                continue

            if status and schedule.status != status:
                continue

            count += 1

        return count
