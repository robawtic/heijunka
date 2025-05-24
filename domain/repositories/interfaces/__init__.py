# domain/repositories/interfaces/__init__.py
from domain.repositories.interfaces.base_repository import BaseRepository
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.group_repository import GroupRepositoryInterface
from domain.repositories.interfaces.department_repository import DepartmentRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.team_member_repository import TeamMemberRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.line_type_repository import LineTypeRepositoryInterface
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface
from domain.repositories.interfaces.employee_training_repository import EmployeeTrainingRepositoryInterface
from domain.repositories.interfaces.employee_workstation_repository import EmployeeWorkstationRepositoryInterface
from domain.repositories.interfaces.assignment_repository import AssignmentRepositoryInterface

__all__ = [
    'BaseRepository',
    'EmployeeRepositoryInterface',
    'GroupRepositoryInterface',
    'DepartmentRepositoryInterface',
    'TeamRepositoryInterface',
    'TeamMemberRepositoryInterface',
    'WorkstationRepositoryInterface',
    'LineTypeRepositoryInterface',
    'EmployeeWorkHistoryRepositoryInterface',
    'EmployeeTrainingRepositoryInterface',
    'EmployeeWorkstationRepositoryInterface',
    'AssignmentRepositoryInterface'
]
