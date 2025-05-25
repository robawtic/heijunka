from sqlalchemy.orm import Session
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
from domain.repositories.implementations.sqlalchemy_employee_work_history_repository import SqlAlchemyEmployeeWorkHistoryRepository
from domain.repositories.implementations.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
from domain.services.schedule_service import ScheduleService
from domain.models.db import Session as DBSession

def get_db():
    """Dependency for getting a database session."""
    db = DBSession()
    try:
        yield db
    finally:
        db.close()

def get_repositories(db: Session):
    """Get all repositories with the given database session."""
    return {
        "employee_repository": SqlAlchemyEmployeeRepository(db),
        "workstation_repository": SqlAlchemyWorkstationRepository(db),
        "team_repository": SqlAlchemyTeamRepository(db),
        "assignment_repository": SqlAlchemyAssignmentRepository(db),
        "work_history_repository": SqlAlchemyEmployeeWorkHistoryRepository(db),
        "schedule_repository": SqlAlchemyScheduleRepository(db),
        "aro_assignment_repository": SqlAlchemyAROAssignmentRepository(db)
    }

def get_schedule_service():
    """Get the schedule service."""
    return ScheduleService()
