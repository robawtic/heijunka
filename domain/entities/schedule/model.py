# heijunka/domain/entities/schedule/model.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, cast
from datetime import date
import logging

# Logger for this module
logger = logging.getLogger(__name__)

from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.entities.schedule.events import ScheduleValidationFailed
from domain.entities.schedule.assignment import create_and_add_assignment
from .events import (
    DomainEvent, ScheduleCreated, ScheduleUpdated, ScheduleStatusChanged
)

@dataclass
class Schedule:
    """
    Schedule aggregate root entity.

    Represents a work schedule for a team, containing assignments of employees to workstations.
    """
    # Instance attributes
    id: int
    team_id: int
    start_date: date
    periods_per_day: int
    status: str
    call_ins: List[str] = field(default_factory=list)
    offline: dict = field(default_factory=dict)
    force_complete: bool = False
    error_message: Optional[str] = None
    task_id: Optional[str] = None
    _assignments: List[WorkAssignment] = field(default_factory=list, repr=False)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)
    end_date: Optional[date] = None

    def __post_init__(self):
        """Initialize collections if they are None and validate the schedule."""
        if self._assignments is None:
            self._assignments = []
        if self._domain_events is None:
            self._domain_events = []
        if self.call_ins is None:
            self.call_ins = []
        if self.offline is None:
            self.offline = {}
        if self.end_date is None:
            self.end_date = self.start_date

        # Register creation event
        if self.id > 0 and isinstance(self.team_id, int) and self.team_id > 0:  # Only register if this is a real entity with valid team_id
            try:
                self.register_domain_event(ScheduleCreated(
                    schedule_id=self.id,
                    team_id=self.team_id,
                    start_date=self.start_date,
                    periods_per_day=self.periods_per_day
                ))
            except ValueError:
                # If there's an error creating the event (e.g., invalid start_date), don't register it
                pass

    @property
    def assignments(self) -> List[WorkAssignment]:
        """Get a copy of the assignments list to prevent direct modification."""
        return self._assignments.copy()

    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get a copy of the domain events list."""
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """Clear all domain events after they've been processed."""
        self._domain_events.clear()

    def register_domain_event(self, event: DomainEvent) -> None:
        """Register a domain event."""
        self._domain_events.append(event)

    def set_status(self, new_status: str) -> bool:
        """
        Set the status of the schedule.

        Args:
            new_status: The new status.

        Returns:
            True if the status was changed, False if it's the same.

        Raises:
            ValueError: If the new status is invalid.
        """
        if not isinstance(new_status, str) or not new_status:
            raise ValueError("Status must be a non-empty string")

        if self.status == new_status:
            return False

        old_status = self.status
        self.status = new_status

        self.register_domain_event(ScheduleStatusChanged(
            schedule_id=self.id,
            old_status=old_status,
            new_status=new_status
        ))

        return True

    def set_error_message(self, error_message: Optional[str]) -> bool:
        """
        Set the error message of the schedule.

        Args:
            error_message: The new error message, or None to clear it.

        Returns:
            True if the error message was changed, False if it's the same.
        """
        if self.error_message == error_message:
            return False

        self.error_message = error_message
        return True

    def set_task_id(self, task_id: Optional[str]) -> bool:
        """
        Set the task ID of the schedule.

        Args:
            task_id: The new task ID, or None to clear it.

        Returns:
            True if the task ID was changed, False if it's the same.
        """
        if self.task_id == task_id:
            return False

        self.task_id = task_id
        return True

    def update(self, status: Optional[str] = None, error_message: Optional[str] = None,
               task_id: Optional[str] = None) -> None:
        """
        Update multiple properties of the schedule at once.

        Args:
            status: The new status (if provided).
            error_message: The new error message (if provided).
            task_id: The new task ID (if provided).

        Raises:
            ValueError: If any of the provided values are invalid.
        """
        updated = False

        if status is not None:
            updated = self.set_status(status) or updated

        # Update error_message if:
        # 1. A new error_message is provided, or
        # 2. error_message is explicitly set to None and we currently have an error_message
        if (error_message is not None) or (error_message is None and self.error_message is not None):
            updated = self.set_error_message(error_message) or updated

        # Update task_id if:
        # 1. A new task_id is provided, or
        # 2. task_id is explicitly set to None and we currently have a task_id
        if (task_id is not None) or (task_id is None and self.task_id is not None):
            updated = self.set_task_id(task_id) or updated

        if updated:
            self.register_domain_event(ScheduleUpdated(schedule_id=self.id))

    def validate(self) -> bool:
        """
        Validates the schedule entity and its assignments.

        Checks:
        1. Basic schedule properties
        2. Assignment overlaps (same employee assigned to multiple workstations in the same period)
        3. Employee eligibility/qualification for assigned workstations
        4. Valid date ranges and periods for assignments

        Returns:
            True if validation passes, False otherwise

        Raises:
            ValueError: If validation fails and force_complete is False
        """
        from domain.entities.schedule.validation import validate
        return validate(self)

    def generate_assignments_ddd(
        self, 
        employees: List[Employee], 
        workstations: List[Workstation],
        prefetched_data: Optional[Dict] = None,
        cp_model_builder=None,
        work_history_data: Optional[Dict] = None
    ) -> bool:
        """
        Generate assignments for this schedule using constraint programming (DDD-compliant version).

        This method uses the CPModelBuilder service to generate assignments for each period.
        It follows Domain-Driven Design principles by not accepting repository dependencies.

        Args:
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries
            cp_model_builder: Optional CPModelBuilder service to use for generating assignments
            work_history_data: Optional dictionary containing work history data for employees

        Returns:
            True if assignments were successfully generated, False otherwise
        """
        from domain.services.cp_model_builder import CPModelBuilder

        # Clear existing assignments if any
        self._assignments = []

        # Create CP model builder if not provided
        if cp_model_builder is None:
            cp_model_builder = CPModelBuilder()

        # Get ARO data from prefetched_data if available
        aro_data = {}
        if prefetched_data and 'aro_assignments_by_employee' in prefetched_data:
            aro_data = prefetched_data['aro_assignments_by_employee']

        # Get team name if available from prefetched_data
        team_name = None
        if prefetched_data and 'teams_by_id' in prefetched_data and self.team_id in prefetched_data['teams_by_id']:
            team = prefetched_data['teams_by_id'][self.team_id]
            if hasattr(team, 'name'):
                team_name = team.name

        # Generate assignments for each period
        all_assignments = []
        for period in range(1, self.periods_per_day + 1):
            # Use the CP model builder to solve the model for this period
            period_assignments = cp_model_builder.solve_one_period(
                employees=employees,
                workstations=workstations,
                period=period,
                team_id=self.team_id,
                start_date=self.start_date,
                aro_data=aro_data,
                team_name=team_name,
                work_history_data=work_history_data
            )

            if period_assignments:
                all_assignments.extend(period_assignments)

                # Add assignments to schedule
                for assignment in period_assignments:
                    try:
                        # Create and add assignment to schedule
                        new_assignment = create_and_add_assignment(self, assignment.employee, assignment.workstation, assignment.period)
                    except ValueError as e:
                        # Log error but continue with other assignments
                        logger.warning(f"Team {self.team_id}: Error creating assignment: {str(e)}")
                        self.register_domain_event(ScheduleValidationFailed(
                            schedule_id=self.id,
                            validation_errors=[str(e)]
                        ))
            else:
                # If no solution found for any period, set error message and return False
                error_msg = f"No solution found for period {period}."
                self.set_error_message(error_msg)
                self.set_status("failed")
                logger.warning(f"Team {self.team_id}: {error_msg}")
                return False

        # Update schedule status
        if all_assignments:
            self.set_status("generated")
            logger.info(f"Team {self.team_id}: Generated {len(self._assignments)} assignments")
            return True
        else:
            self.set_status("failed")
            error_msg = "No assignments generated."
            self.set_error_message(error_msg)
            logger.warning(f"Team {self.team_id}: {error_msg}")
            return False

    def generate_assignments(
        self, 
        employees: List[Employee], 
        workstations: List[Workstation],
        rule_context: Optional[Any] = None, 
        session=None, 
        team_repository=None,
        aro_service=None, 
        aro_graph_service=None, 
        prefetched_data: Optional[Dict] = None,
        team_aro_repository=None,
        cp_model_builder=None,
        employee_history_repo=None
    ) -> bool:
        """
        Generate assignments for this schedule using constraint programming.

        @deprecated: Use generate_assignments_ddd instead and handle persistence in the application layer.

        This method uses the CPModelBuilder service to generate assignments for each period.

        Args:
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed
            rule_context: Optional pre-configured rule context (not used with CPModelBuilder)
            session: Database session for accessing work history data (not used with CPModelBuilder)
            team_repository: Optional repository for retrieving team information (not used with CPModelBuilder)
            aro_service: Optional ARO service for finding and assigning AROs (not used with CPModelBuilder)
            aro_graph_service: Optional ARO graph service for optimizing ARO assignments (not used with CPModelBuilder)
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries
            team_aro_repository: Optional repository for retrieving TeamAro relationships (not used with CPModelBuilder)
            cp_model_builder: Optional CPModelBuilder service to use for generating assignments
            employee_history_repo: Optional repository for employee work history (required for same-day repeat penalties)

        Returns:
            True if assignments were successfully generated, False otherwise
        """
        from domain.services.cp_model_builder import CPModelBuilder
        from domain.value_objects.work_history_entry import WorkHistoryEntry

        # Clear existing assignments if any
        self._assignments = []

        # Create CP model builder if not provided
        if cp_model_builder is None:
            cp_model_builder = CPModelBuilder()

        # Get ARO data from prefetched_data if available
        aro_data = {}
        if prefetched_data and 'aro_assignments_by_employee' in prefetched_data:
            aro_data = prefetched_data['aro_assignments_by_employee']

        # Get team name if available
        team_name = None
        if team_repository:
            try:
                team = team_repository.get(self.team_id)
                if team:
                    team_name = team.name
            except Exception as e:
                logger.warning(f"Could not get team name for team ID {self.team_id}: {str(e)}")

        # Generate assignments for each period
        all_assignments = []
        for period in range(1, self.periods_per_day + 1):
            # Use the CP model builder to solve the model for this period
            period_assignments = cp_model_builder.solve_one_period(
                employees=employees,
                workstations=workstations,
                period=period,
                team_id=self.team_id,
                start_date=self.start_date,
                aro_data=aro_data,
                team_name=team_name,
                employee_history_repo=employee_history_repo
            )

            if period_assignments:
                all_assignments.extend(period_assignments)

                # Add assignments to schedule
                for assignment in period_assignments:
                    try:
                        # Create and add assignment to schedule
                        new_assignment = create_and_add_assignment(self, assignment.employee, assignment.workstation, assignment.period)

                        # Update work history repository if provided
                        if employee_history_repo:
                            # Create a work history entry for this assignment
                            entry = WorkHistoryEntry(
                                employee_id=assignment.employee.id,
                                workstation_id=assignment.workstation.id,
                                worked_date=self.start_date,
                                work_period=assignment.period.period
                            )
                            # Add the entry to the repository
                            employee_history_repo.add(entry)
                    except ValueError as e:
                        # Log error but continue with other assignments
                        logger.warning(f"Team {self.team_id}: Error creating assignment: {str(e)}")
                        self.register_domain_event(ScheduleValidationFailed(
                            schedule_id=self.id,
                            validation_errors=[str(e)]
                        ))
            else:
                # If no solution found for any period, set error message and return False
                error_msg = f"No solution found for period {period}."
                self.set_error_message(error_msg)
                self.set_status("failed")
                logger.warning(f"Team {self.team_id}: {error_msg}")
                return False

        # Update schedule status
        if all_assignments:
            self.set_status("generated")
            logger.info(f"Team {self.team_id}: Generated {len(self._assignments)} assignments")
            return True
        else:
            self.set_status("failed")
            error_msg = "No assignments generated."
            self.set_error_message(error_msg)
            logger.warning(f"Team {self.team_id}: {error_msg}")
            return False
