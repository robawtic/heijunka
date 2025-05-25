from typing import List, Optional
from datetime import date

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.work_history_entry import WorkHistoryEntry
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.events.publisher import DomainEventPublisher
from domain.factories.employee_factory import EmployeeFactory
from domain.factories.workstation_factory import WorkstationFactory


class EmployeeService:
    """
    Service for managing employees, roles, qualifications, workstations, and work history.

    This service follows Domain-Driven Design principles by:
    1. Using the Employee entity's methods to modify state
    2. Ensuring domain events are published
    3. Using repositories for persistence
    """

    def __init__(self,
                 employee_repository: EmployeeRepositoryInterface,
                 work_history_repository: EmployeeWorkHistoryRepositoryInterface,
                 workstation_repository: Optional[WorkstationRepositoryInterface] = None,
                 event_publisher: Optional[DomainEventPublisher] = None):
        """
        Initialize the service with the necessary repositories and event publisher.

        Args:
            employee_repository: Repository for accessing and persisting employees
            work_history_repository: Repository for accessing and persisting work history
            workstation_repository: Repository for accessing and persisting workstations (optional)
            event_publisher: Publisher for domain events (optional)
        """
        self._employee_repository = employee_repository
        self._work_history_repository = work_history_repository
        self._workstation_repository = workstation_repository
        self._event_publisher = event_publisher or DomainEventPublisher()

    # --- Creation Methods ---
    def create_employee(self, name: str, team_id: int, is_active: bool = True, roles: List[str] = None) -> Employee:
        """
        Create a new employee with the given attributes.

        Args:
            name: The name of the employee
            team_id: The ID of the team the employee belongs to
            is_active: Whether the employee is active
            roles: A list of roles for the employee

        Returns:
            The newly created employee
        """
        employee = EmployeeFactory.create_employee(
            name=name,
            team_id=team_id,
            is_active=is_active,
            roles=roles
        )
        return self._employee_repository.add(employee)

    def create_workstation(self, name: str, line_type: str, team_id: int,
                           is_loading_job: bool = False, is_heavy_job: bool = False,
                           is_key_skill_job: bool = False) -> Workstation:
        """
        Create a new workstation with the given attributes.

        Args:
            name: The name of the workstation
            line_type: The type of line the workstation belongs to
            team_id: The ID of the team the workstation belongs to
            is_loading_job: Whether the workstation is a loading job
            is_heavy_job: Whether the workstation is a heavy job
            is_key_skill_job: Whether the workstation requires a key skill

        Returns:
            The newly created workstation
        """
        workstation = WorkstationFactory.create_workstation(
            name=name,
            line_type=line_type,
            team_id=team_id,
            is_loading_job=is_loading_job,
            is_heavy_job=is_heavy_job,
            is_key_skill_job=is_key_skill_job
        )
        if self._workstation_repository:
            return self._workstation_repository.add(workstation)
        return workstation

    # --- Role/Qualification Management ---
    def assign_role(self, employee: Employee, role_name: str) -> None:
        """
        Assign a role to an employee.

        Args:
            employee: The employee to assign the role to
            role_name: The name of the role to assign
        """
        if role_name not in employee.roles:
            employee.roles.append(role_name)
        self._employee_repository.update(employee)

    def remove_role(self, employee: Employee, role_name: str) -> None:
        """
        Remove a role from an employee.

        Args:
            employee: The employee to remove the role from
            role_name: The name of the role to remove
        """
        if role_name in employee.roles:
            employee.roles.remove(role_name)
        self._employee_repository.update(employee)

    def assign_qualification(self, employee: Employee, workstation_name: str) -> None:
        """
        Assign a qualification to an employee.

        Args:
            employee: The employee to assign the qualification to
            workstation_name: The name of the workstation to qualify the employee for
        """
        if workstation_name not in employee.qualifications:
            employee.qualifications.append(workstation_name)
        self._employee_repository.update(employee)

    def get_employee_history(self, employee_id: int, start_date: date, end_date: date) -> List[WorkHistoryEntry]:
        """
        Get work history for an employee in the given date range.

        Args:
            employee_id: The ID of the employee
            start_date: The start date of the range
            end_date: The end date of the range

        Returns:
            A list of work history entries for the employee in the given date range
        """
        return self._work_history_repository.get_by_employee_date_range(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date
        )

    def record_work_session(self, employee_id: int, workstation_id: int,
                            worked_date: date, work_period: int, end_flag: bool = False) -> bool:
        """
        Record a work session for an employee.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            worked_date: The date the work was performed
            work_period: The period of the day the work was performed
            end_flag: Whether this is the end of a work session

        Returns:
            True if the work session was recorded successfully, False otherwise
        """
        # Get the employee
        employee = self._employee_repository.get_by_id(employee_id)
        if not employee:
            return False

        # Create a work history entry
        work_history_entry = WorkHistoryEntry(
            employee_id=employee_id,
            workstation_id=workstation_id,
            worked_date=worked_date,
            work_period=work_period,
            end_flag=end_flag
        )

        # Add the work history entry to the employee
        employee.add_work_history_entry(workstation_id, worked_date, work_period)

        # Update the employee in the repository
        self._employee_repository.update(employee)

        # Add the work history entry to the repository
        self._work_history_repository.add(work_history_entry)

        # Publish domain events
        for event in employee.domain_events:
            self._event_publisher.publish(event)

        # Clear domain events after publishing
        employee.clear_domain_events()

        return True

    # --- Workstation Assignment (optional) ---
    def assign_workstation(self, employee: Employee, workstation: Workstation) -> bool:
        """
        Assign a workstation to an employee.

        Args:
            employee: The employee to assign the workstation to
            workstation: The workstation to assign

        Returns:
            True if the assignment was successful, False otherwise
        """
        if not employee.assign_workstation(workstation):
            return False
        # Optionally update in the repo if it supports assignment
        if hasattr(self._employee_repository, 'assign_workstation'):
            result = self._employee_repository.assign_workstation(employee.id, workstation.id)
            return result.get("status") == "success"
        self._employee_repository.update(employee)
        return True