from datetime import date
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.work_history_entry import WorkHistoryEntry

class AssignmentService:
    def __init__(self, employee_repository, rule_registry):
        self.employee_repository = employee_repository
        self.rule_registry = rule_registry

    def can_assign(self, employee: Employee, station: Workstation, assign_date: date, period: int) -> bool:
        """Check all rules to determine if this assignment is valid."""
        if not employee.can_work(station):
            return False

        if not self.employee_repository.is_available(employee.id, assign_date, period):
            return False

        # Check recent work history to avoid back-to-back heavy assignments
        recent = self.employee_repository.get_last_worked_date(employee.id, station.id)
        if recent and recent[0] == assign_date and recent[1] == period:
            return False  # Already worked this station in this period

        # Apply rule registry (DDD-style rule plugin)
        return self.rule_registry.evaluate_all(employee, station, assign_date, period)

    def create_assignment(self, employee: Employee, station: Workstation, assign_date: date, period: int):
        """Create a work history entry and return domain object (no commit yet)."""
        return WorkHistoryEntry(
            employee_id=employee.id,
            workstation_id=station.id,
            worked_date=assign_date,
            work_period=period,
            end_flag=False
        )

