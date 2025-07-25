from typing import List, Dict

from domain.services.schedule_service import ScheduleService
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment
from domain.contexts.employee_management.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.contexts.workstation_management.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.contexts.assignment.repositories.interfaces.assignment_repository import AssignmentRepositoryInterface
from application.schedule_management.commands.generate_schedule_command import GenerateScheduleCommand


class GenerateScheduleHandler:
    def __init__(self,
                 employee_repository: EmployeeRepositoryInterface,
                 workstation_repository: WorkstationRepositoryInterface,
                 team_repository: TeamRepositoryInterface,
                 assignment_repository: AssignmentRepositoryInterface,
                 schedule_service: ScheduleService,
                 schedule_repository=None,
                 session=None,
                 aro_service=None,
                 aro_graph_service=None,
                 work_history_repository=None):
        self.employee_repository = employee_repository
        self.workstation_repository = workstation_repository
        self.team_repository = team_repository
        self.assignment_repository = assignment_repository
        self.schedule_service = schedule_service
        self.schedule_repository = schedule_repository
        self.session = session
        self.aro_service = aro_service
        self.aro_graph_service = aro_graph_service
        self.work_history_repository = work_history_repository

    def handle(self, command: GenerateScheduleCommand) -> List[WorkAssignment]:
        """Generate and SAVE assignments for a single team."""
        employees = self.employee_repository.get_by_team_id(command.team_id)
        workstations = self.workstation_repository.get_by_team_id(command.team_id)

        team = self.team_repository.get_by_id(command.team_id)
        if not team:
            raise ValueError(f"Team with ID {command.team_id} not found")

        work_history_data = None
        if self.work_history_repository:
            work_history_data = self._fetch_work_history_data(employees, command.start_date)

        assignments, schedule_metadata = self.schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=command.start_date,
            periods_per_day=command.periods_per_day,
            team_name=team.name,
            team_id=team.id,
            call_ins=command.call_ins,
            offline=command.offline,
            force_complete=command.force_complete
        )

        if self.schedule_repository and schedule_metadata:
            self._save_schedule(schedule_metadata)

        if self.work_history_repository and assignments:
            self._save_work_history(assignments, command.start_date)

        if assignments:
            self.assignment_repository.save_all(assignments)

        return assignments

    def _fetch_work_history_data(self, employees, start_date):
        """
        Fetch work history data for the given employees and date.

        Args:
            employees: List of employees to fetch work history for
            start_date: The date to fetch work history for

        Returns:
            Dictionary mapping employee IDs to their work history entries
        """
        work_history_data = {}
        if self.work_history_repository:
            # Get employee IDs
            employee_ids = [employee.id for employee in employees]

            # Fetch work history for these employees
            # This is a simplified example - actual implementation would depend on the repository interface
            entries = self.work_history_repository.get_by_employee_ids(employee_ids, start_date)

            # Organize by employee ID
            for entry in entries:
                if entry.employee_id not in work_history_data:
                    work_history_data[entry.employee_id] = []
                work_history_data[entry.employee_id].append(entry)

        return work_history_data

    def _save_schedule(self, schedule_metadata):
        """
        Save or update a schedule based on metadata.

        Args:
            schedule_metadata: Dictionary containing schedule metadata
        """
        if not self.schedule_repository:
            return

        schedule_id = schedule_metadata.get("id")
        if schedule_id:
            self.schedule_repository.update_status(
                schedule_id, 
                schedule_metadata.get("status", "completed"),
                schedule_metadata.get("error_message")
            )
        else:
            self.schedule_repository.create_schedule(
                team_id=schedule_metadata.get("team_id"),
                start_date=schedule_metadata.get("start_date"),
                periods_per_day=schedule_metadata.get("periods_per_day"),
                status=schedule_metadata.get("status", "completed"),
                error_message=schedule_metadata.get("error_message")
            )

    def _save_work_history(self, assignments, start_date):
        """
        Save work history entries for the given assignments.

        Args:
            assignments: List of work assignments
            start_date: The date of the assignments
        """
        if not self.work_history_repository or not assignments:
            return

        # Create work history entries
        from domain.contexts.employee_management.value_objects.work_history_entry import WorkHistoryEntry

        entries = []
        for assignment in assignments:
            entry = WorkHistoryEntry(
                employee_id=assignment.employee.id,
                workstation_id=assignment.workstation.id,
                worked_date=start_date,
                work_period=assignment.period.period
            )
            entries.append(entry)

        # Save entries
        for entry in entries:
            self.work_history_repository.add(entry)

    def generate_only(self, command: GenerateScheduleCommand) -> List[WorkAssignment]:
        """Generate assignments for a single team but DO NOT SAVE them."""
        # Get employees and workstations for the team
        employees = self.employee_repository.get_by_team_id(command.team_id)
        workstations = self.workstation_repository.get_by_team_id(command.team_id)

        # Get team name from team ID
        team = self.team_repository.get_by_id(command.team_id)
        if not team:
            raise ValueError(f"Team with ID {command.team_id} not found")

        # Get work history data if needed
        work_history_data = None
        if self.work_history_repository:
            work_history_data = self._fetch_work_history_data(employees, command.start_date)

        # Generate schedule
        assignments, _ = self.schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=command.start_date,
            periods_per_day=command.periods_per_day,
            team_name=team.name,
            team_id=team.id,
            call_ins=command.call_ins,
            offline=command.offline,
            force_complete=command.force_complete
        )

        return assignments

    def generate_with_prefetched_data(
        self, 
        command: GenerateScheduleCommand, 
        employees: List["Employee"], 
        workstations: List["Workstation"],
        prefetched_data: Dict = None
    ) -> List[WorkAssignment]:
        """
        Generate assignments using prefetched data.

        Args:
            command: The command containing schedule generation parameters
            employees: Prefetched employees for the team
            workstations: Prefetched workstations for the team
            prefetched_data: Additional prefetched data (teams, groups, ARO assignments, etc.)

        Returns:
            List of generated work assignments
        """
        # Get team name from team ID (use prefetched data if available)
        team = None
        if prefetched_data and 'teams_by_id' in prefetched_data and command.team_id in prefetched_data['teams_by_id']:
            team = prefetched_data['teams_by_id'][command.team_id]
        else:
            team = self.team_repository.get_by_id(command.team_id)

        if not team:
            raise ValueError(f"Team with ID {command.team_id} not found")

        # Get work history data if needed (use prefetched data if available)
        work_history_data = None
        if prefetched_data and 'work_history_data' in prefetched_data:
            work_history_data = prefetched_data['work_history_data']
        elif self.work_history_repository:
            work_history_data = self._fetch_work_history_data(employees, command.start_date)

        # Generate schedule
        assignments, schedule_metadata = self.schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=command.start_date,
            periods_per_day=command.periods_per_day,
            team_name=team.name,
            team_id=team.id,
            call_ins=command.call_ins,
            offline=command.offline,
            force_complete=command.force_complete,
            prefetched_data=prefetched_data
        )

        return assignments