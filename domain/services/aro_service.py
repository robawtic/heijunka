from typing import List, Optional, Dict, Callable, Any
from datetime import date

from domain.entities.employee import Employee
from domain.value_objects.aro_assignment import AROAssignment
from domain.repositories.interfaces.aro_assignment_repository import AROAssignmentRepositoryInterface
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.events import AROAssignmentCreated, AROAssignmentRemoved, AROAssignmentUpdated

class AROService:
    def __init__(self, 
                 aro_repository: AROAssignmentRepositoryInterface,
                 employee_repository: EmployeeRepositoryInterface,
                 team_repository: TeamRepositoryInterface):
        self.aro_repository = aro_repository
        self.employee_repository = employee_repository
        self.team_repository = team_repository
        self._event_handlers = {
            'aro_assignment_created': [],
            'aro_assignment_removed': [],
            'aro_assignment_updated': []
        }

    def register_event_handler(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """
        Register an event handler for a specific event type.

        Args:
            event_type: The type of event to handle ('aro_assignment_created', 'aro_assignment_removed', 'aro_assignment_updated')
            handler: The handler function to call when the event occurs
        """
        if event_type not in self._event_handlers:
            raise ValueError(f"Unknown event type: {event_type}")
        self._event_handlers[event_type].append(handler)

    def _trigger_event(self, event_type: str, event: Any) -> None:
        """
        Trigger all handlers for a specific event type.

        Args:
            event_type: The type of event that occurred
            event: The event object
        """
        if event_type not in self._event_handlers:
            return

        for handler in self._event_handlers[event_type]:
            handler(event)

    def assign_aro(self, employee_id: int, to_team_id: int, 
                  assignment_date: date, period: Optional[int] = None) -> Dict[str, str]:
        """
        Assign an employee as an ARO to another team.

        Args:
            employee_id: The ID of the employee to assign
            to_team_id: The ID of the team to assign the employee to
            assignment_date: The date of the assignment
            period: Optional period of the day for the assignment

        Returns:
            A dictionary with status and message
        """
        # Get the employee
        employee = self.employee_repository.get(employee_id)
        if not employee:
            return {"status": "error", "message": "Employee not found"}

        # Get the destination team
        to_team = self.team_repository.get(to_team_id)
        if not to_team:
            return {"status": "error", "message": "Destination team not found"}

        # Check if employee is already assigned as ARO for this date/period
        existing_assignments = self.aro_repository.get_by_employee_id(employee_id, assignment_date)
        for assignment in existing_assignments:
            if assignment.period == period:
                return {"status": "error", "message": "Employee already assigned as ARO for this date/period"}

        # Create the ARO assignment
        aro_assignment = AROAssignment(
            employee_id=employee_id,
            from_team_id=employee.team_id,
            to_team_id=to_team_id,
            assignment_date=assignment_date,
            period=period
        )

        # Save the assignment
        saved_assignment = self.aro_repository.add(aro_assignment)

        # Mark the employee as unavailable in their primary team
        employee.assign_as_aro(to_team_id, assignment_date, period)
        self.employee_repository.update(employee)

        # Create and trigger the event
        event = AROAssignmentCreated(
            employee_id=employee_id,
            from_team_id=employee.team_id,
            to_team_id=to_team_id,
            assignment_date=assignment_date,
            period=period
        )
        self._trigger_event('aro_assignment_created', event)

        return {"status": "success", "message": "Employee assigned as ARO"}

    def find_aro_assignment(self, employee_id: int, assignment_date: date, period: Optional[int] = None) -> Optional[AROAssignment]:
        """
        Find an ARO assignment by employee, date, and period.

        Args:
            employee_id: The ID of the employee
            assignment_date: The date of the assignment
            period: Optional period of the day

        Returns:
            The ARO assignment if found, None otherwise
        """
        assignments = self.aro_repository.get_by_employee_id(employee_id, assignment_date)
        for assignment in assignments:
            if assignment.period == period:
                return assignment
        return None

    def remove_aro_assignment(self, assignment_id: int) -> Dict[str, str]:
        """
        Remove an ARO assignment.

        Args:
            assignment_id: The ID of the ARO assignment to remove

        Returns:
            A dictionary with status and message
        """
        # Get the assignment
        assignment = self.aro_repository.get_by_id(assignment_id)
        if not assignment:
            return {"status": "error", "message": "ARO assignment not found"}

        # Get the employee
        employee = self.employee_repository.get(assignment.employee_id)
        if not employee:
            return {"status": "error", "message": "Employee not found"}

        # Remove the assignment
        success = self.aro_repository.delete(assignment_id)
        if not success:
            return {"status": "error", "message": "Failed to remove ARO assignment"}

        # Create and trigger the event
        event = AROAssignmentRemoved(
            employee_id=assignment.employee_id,
            from_team_id=assignment.from_team_id,
            to_team_id=assignment.to_team_id,
            assignment_date=assignment.assignment_date,
            period=assignment.period
        )
        self._trigger_event('aro_assignment_removed', event)

        return {"status": "success", "message": "ARO assignment removed"}

    def get_employees_for_team_and_period(self, team_id: int, assignment_date: date, period: Optional[int] = None) -> List[Employee]:
        """
        Get all employees available for a team on a specific date and period,
        including AROs assigned to the team and excluding those assigned elsewhere.

        Args:
            team_id: The ID of the team
            assignment_date: The date to check
            period: Optional period of the day to check

        Returns:
            List of available employees
        """
        # Get the team's base roster
        team_employees = self.employee_repository.get_by_team_id(team_id)

        # Get employees leaving as AROs
        aro_out_ids = self.aro_repository.get_employees_leaving(team_id, assignment_date, period)

        # Get employees joining as AROs
        aro_in_ids = self.aro_repository.get_employees_joining(team_id, assignment_date, period)

        # Filter out employees leaving as AROs
        available_employees = [e for e in team_employees if e.id not in aro_out_ids]

        # Add employees joining as AROs
        for aro_id in aro_in_ids:
            aro_employee = self.employee_repository.get(aro_id)
            if aro_employee:
                available_employees.append(aro_employee)

        return available_employees
