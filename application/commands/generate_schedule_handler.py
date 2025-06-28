from typing import List, Dict

from domain.services.schedule_service import ScheduleService
from domain.value_objects.work_assignment import WorkAssignment
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.assignment_repository import AssignmentRepositoryInterface
from application.commands.generate_schedule_command import GenerateScheduleCommand


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
        """Generate and SAVE assignments for a single team (original behavior)."""
        # Get employees and workstations for the team
        employees = self.employee_repository.get_by_team_id(command.team_id)
        workstations = self.workstation_repository.get_by_team_id(command.team_id)

        # Get team name from team ID
        team = self.team_repository.get_by_id(command.team_id)
        if not team:
            raise ValueError(f"Team with ID {command.team_id} not found")

        # Generate schedule
        assignments = self.schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=command.start_date,
            periods_per_day=command.periods_per_day,
            team_name=team.name,
            call_ins=command.call_ins,
            offline=command.offline,
            force_complete=command.force_complete,
            session=self.session,
            team_repository=self.team_repository,
            schedule_repository=self.schedule_repository,
            aro_service=self.aro_service,
            aro_graph_service=self.aro_graph_service,
            employee_history_repo=self.work_history_repository
        )

        # Save assignments
        self.assignment_repository.save_all(assignments)

        return assignments

    def generate_only(self, command: GenerateScheduleCommand) -> List[WorkAssignment]:
        """Generate assignments for a single team, but DO NOT SAVE them."""
        # Get employees and workstations for the team
        employees = self.employee_repository.get_by_team_id(command.team_id)
        workstations = self.workstation_repository.get_by_team_id(command.team_id)

        # Get team name from team ID
        team = self.team_repository.get_by_id(command.team_id)
        if not team:
            raise ValueError(f"Team with ID {command.team_id} not found")

        # Generate schedule
        assignments = self.schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=command.start_date,
            periods_per_day=command.periods_per_day,
            team_name=team.name,
            call_ins=command.call_ins,
            offline=command.offline,
            force_complete=command.force_complete,
            session=self.session,
            team_repository=self.team_repository,
            schedule_repository=self.schedule_repository,
            aro_service=self.aro_service,
            aro_graph_service=self.aro_graph_service,
            employee_history_repo=self.work_history_repository
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

        # Generate schedule
        assignments = self.schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=command.start_date,
            periods_per_day=command.periods_per_day,
            team_name=team.name,
            call_ins=command.call_ins,
            offline=command.offline,
            force_complete=command.force_complete,
            session=self.session,
            team_repository=self.team_repository,
            schedule_repository=self.schedule_repository,
            aro_service=self.aro_service,
            aro_graph_service=self.aro_graph_service,
            prefetched_data=prefetched_data,
            employee_history_repo=self.work_history_repository
        )

        return assignments
