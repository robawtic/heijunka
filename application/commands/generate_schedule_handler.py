# heijunka/application/commands/generate_schedule_handler.py
from typing import List

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
                 session=None):
        self.employee_repository = employee_repository
        self.workstation_repository = workstation_repository
        self.team_repository = team_repository
        self.assignment_repository = assignment_repository
        self.schedule_service = schedule_service
        self.session = session

    def handle(self, command: GenerateScheduleCommand) -> List[WorkAssignment]:
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
            days=command.days,
            periods_per_day=command.periods_per_day,
            team_name=team.name,
            call_ins=command.call_ins,
            offline=command.offline,
            force_complete=command.force_complete,
            session=self.session
        )

        # Save assignments
        self.assignment_repository.save_all(assignments)

        return assignments
