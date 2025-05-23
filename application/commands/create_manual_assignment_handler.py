from domain.repositories.interfaces.assignment_repository import AssignmentRepositoryInterface
from application.commands.create_manual_assignment_command import CreateManualAssignmentCommand

class CreateManualAssignmentHandler:
    def __init__(self, assignment_repository: AssignmentRepositoryInterface):
        self.assignment_repository = assignment_repository

    def handle(self, command: CreateManualAssignmentCommand) -> bool:
        return self.assignment_repository.create_temporary_assignment(
            employee_id=command.employee_id,
            workstation_id=command.workstation_id,
            date=command.assignment_date,
            period=command.period,
            schedule_id=command.schedule_id
        )