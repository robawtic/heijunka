from typing import List, Optional, Dict, Callable, Any
from datetime import date
import logging

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.assignment.aro_assignment import AROAssignment
from domain.repositories.interfaces.aro_assignment_repository import AROAssignmentRepositoryInterface
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.team_aro_repository import TeamAroRepositoryInterface
from domain.events import AROAssignmentCreated, AROAssignmentRemoved, AROAssignmentUpdated
from domain.events.publisher import DomainEventPublisher

# Logger for this module
logger = logging.getLogger(__name__)

class AROService:
    def __init__(self,
                 aro_repository: AROAssignmentRepositoryInterface,
                 employee_repository: EmployeeRepositoryInterface,
                 team_repository: TeamRepositoryInterface,
                 team_aro_repository: TeamAroRepositoryInterface,
                 event_publisher: DomainEventPublisher = None):
        self.aro_repository = aro_repository
        self.employee_repository = employee_repository
        self.team_repository = team_repository
        self.team_aro_repository = team_aro_repository
        self.event_publisher = event_publisher or DomainEventPublisher()
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

        # Create the ARO assignment through the aggregate
        aro_assignment = AROAssignment.create(
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

        # Publish domain events
        for event in aro_assignment.domain_events:
            self.event_publisher.publish(event)

            # Also trigger the legacy event handlers for backward compatibility
            if isinstance(event, AROAssignmentCreated):
                self._trigger_event('aro_assignment_created', event)
            elif isinstance(event, AROAssignmentRemoved):
                self._trigger_event('aro_assignment_removed', event)
            elif isinstance(event, AROAssignmentUpdated):
                self._trigger_event('aro_assignment_updated', event)

        # Clear domain events after publishing
        aro_assignment.clear_domain_events()

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

        # Mark the assignment for removal
        assignment.remove()

        # Remove the assignment
        success = self.aro_repository.delete(assignment_id)
        if not success:
            return {"status": "error", "message": "Failed to remove ARO assignment"}

        # Publish domain events
        for event in assignment.domain_events:
            self.event_publisher.publish(event)

            # Also trigger the legacy event handlers for backward compatibility
            if isinstance(event, AROAssignmentCreated):
                self._trigger_event('aro_assignment_created', event)
            elif isinstance(event, AROAssignmentRemoved):
                self._trigger_event('aro_assignment_removed', event)
            elif isinstance(event, AROAssignmentUpdated):
                self._trigger_event('aro_assignment_updated', event)

        # Clear domain events after publishing
        assignment.clear_domain_events()

        return {"status": "success", "message": "ARO assignment removed"}

    def get_aro_for_workstations(self, team_id: int, period: Optional[int] = None, assignment_date: Optional[date] = None, empty_workstations: Optional[List["Workstation"]] = None) -> Optional[AROAssignment]:
        """
        Find the best ARO candidate for a team that needs additional staffing for specific workstations.

        Args:
            team_id: The ID of the team that needs an ARO
            period: The period for which the ARO is needed
            assignment_date: The date for the assignment (defaults to today if not provided)
            empty_workstations: List of empty workstations that need to be filled

        Returns:
            An AROAssignment object if a suitable ARO is found, None otherwise
        """
        return self.get_aro(team_id, period, assignment_date, empty_workstations)

    def get_aro(self, team_id: int, period: Optional[int] = None, assignment_date: Optional[date] = None, empty_workstations: Optional[List["Workstation"]] = None) -> Optional[AROAssignment]:
        """
        Find the best ARO candidate for a team that needs additional staffing.

        Args:
            team_id: The ID of the team that needs an ARO
            period: The period for which the ARO is needed
            assignment_date: The date for the assignment (defaults to today if not provided)
            empty_workstations: Optional list of empty workstations that need to be filled.
                                If provided, AROs will be selected based on their qualifications for these workstations.

        Returns:
            An AROAssignment object if a suitable ARO is found, None otherwise
        """
        try:
            # Use today's date if not provided
            if assignment_date is None:
                assignment_date = date.today()

            # Dictionary to track qualified ARO candidates and their qualification scores
            qualified_candidates = {}

            # Get all active TeamAro relationships for the team that needs an ARO
            team_aros = self.team_aro_repository.get_by_team_id(team_id)
            active_team_aros = [aro for aro in team_aros if aro.is_active()]

            if not active_team_aros:
                logger.warning(f"No active ARO relationships found for team {team_id}")
                return None

            for team_aro in active_team_aros:
                # Get the employee
                employee = self.employee_repository.get(team_aro.employee_id)
                if not employee:
                    continue

                # Get the employee's home team
                from_team_id = employee.team_id

                # Skip if the employee is from the same team that needs an ARO
                if from_team_id == team_id:
                    continue

                # Check if employee is already assigned as ARO for this period
                assigned_ids = self.aro_repository.get_employees_leaving(from_team_id, assignment_date, period)

                # Skip if employee is already assigned as ARO
                if employee.id in assigned_ids:
                    continue

                # Check if employee is available for this period
                if not employee.is_available_for_period(assignment_date, period):
                    continue

                # If workstations are provided, check qualifications
                if empty_workstations:
                    # Count how many empty workstations this employee is qualified for
                    qualified_count = 0
                    for workstation in empty_workstations:
                        if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                            qualified_count += 1

                    # If employee is qualified for at least one workstation, add them as a candidate
                    if qualified_count > 0:
                        qualified_candidates[employee.id] = {
                            'employee': employee,
                            'from_team_id': from_team_id,
                            'qualified_count': qualified_count
                        }
                else:
                    # If no workstations provided, just add the employee as a candidate with a default score
                    qualified_candidates[employee.id] = {
                        'employee': employee,
                        'from_team_id': from_team_id,
                        'qualified_count': 1  # Default score
                    }

            # If we have qualified candidates, select the best one
            if qualified_candidates:
                # If workstations are provided, sort by qualification score
                if empty_workstations:
                    # Sort candidates by qualification score (descending)
                    sorted_candidates = sorted(
                        qualified_candidates.values(),
                        key=lambda x: x['qualified_count'],
                        reverse=True
                    )
                    best_candidate = sorted_candidates[0]
                else:
                    # If no workstations, just pick the first candidate
                    # In a real implementation, you might want to use other criteria here
                    best_candidate = next(iter(qualified_candidates.values()))

                # Create a temporary AROAssignment object to return
                # This doesn't persist to the database until assign_aro is called
                aro_candidate = AROAssignment(
                    id=None,  # No ID yet since it's not persisted
                    employee_id=best_candidate['employee'].id,
                    from_team_id=best_candidate['from_team_id'],
                    to_team_id=team_id,
                    assignment_date=assignment_date,
                    period=period
                )

                # Publish an event to notify the system about this ARO transfer
                if self.event_publisher:
                    self.event_publisher.publish(AROTransferRequested(
                        employee_id=aro_candidate.employee_id,
                        from_team_id=aro_candidate.from_team_id,
                        to_team_id=aro_candidate.to_team_id,
                        assignment_date=aro_candidate.assignment_date,
                        period=aro_candidate.period
                    ))

                return aro_candidate

            # No suitable ARO found
            logger.warning(f"No qualified ARO candidates found for team {team_id}, period {period}")
            return None

        except Exception as e:
            logger.error(f"Error finding ARO candidate: {str(e)}")
            return None

    def get_workstation_aro_mapping(self, team_id: int, period: Optional[int] = None, 
                               assignment_date: Optional[date] = None, 
                               empty_workstations: Optional[List["Workstation"]] = None) -> Dict[int, List[int]]:
        """
        Get a mapping of workstations to qualified AROs for a team.

        Args:
            team_id: The ID of the team that needs AROs
            period: The period for which AROs are needed
            assignment_date: The date for the assignment (defaults to today if not provided)
            empty_workstations: List of empty workstations that need to be filled

        Returns:
            A dictionary mapping workstation IDs to lists of qualified ARO employee IDs
        """
        try:
            # Use today's date if not provided
            if assignment_date is None:
                assignment_date = date.today()

            # If no empty workstations provided, return empty mapping
            if not empty_workstations:
                logger.warning(f"No empty workstations provided for team {team_id}, period {period}")
                return {}

            # Map of workstation to qualified AROs
            workstation_to_aros = {}

            # Get all active TeamAro relationships for the team that needs AROs
            team_aros = self.team_aro_repository.get_by_team_id(team_id)
            active_team_aros = [aro for aro in team_aros if aro.is_active()]

            if not active_team_aros:
                logger.warning(f"No active ARO relationships found for team {team_id}")
                return {}

            # For each active ARO relationship, check if the employee is available and qualified
            for team_aro in active_team_aros:
                # Get the employee
                employee = self.employee_repository.get(team_aro.employee_id)
                if not employee:
                    continue

                # Get the employee's home team
                from_team_id = employee.team_id

                # Skip if the employee is from the same team that needs AROs
                if from_team_id == team_id:
                    continue

                # Check if employee is already assigned as ARO for this period
                assigned_ids = self.aro_repository.get_employees_leaving(from_team_id, assignment_date, period)

                # Skip if employee is already assigned as ARO
                if employee.id in assigned_ids:
                    continue

                # Check if employee is available for this period
                if not employee.is_available_for_period(assignment_date, period):
                    continue

                # Check which workstations this ARO can handle
                for workstation in empty_workstations:
                    if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                        # Add this ARO to the workstation's list
                        if workstation.id not in workstation_to_aros:
                            workstation_to_aros[workstation.id] = []
                        workstation_to_aros[workstation.id].append(employee.id)

            return workstation_to_aros

        except Exception as e:
            logger.error(f"Error creating workstation-ARO mapping: {str(e)}")
            return {}

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
