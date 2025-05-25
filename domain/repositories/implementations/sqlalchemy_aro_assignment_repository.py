from typing import List, Optional
from datetime import date
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from domain.value_objects.aro_assignment import AROAssignment
from domain.models.AROAssignmentModel import AROAssignmentModel
from domain.repositories.interfaces.aro_assignment_repository import AROAssignmentRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository

class SqlAlchemyAROAssignmentRepository(BaseSqlAlchemyRepository[AROAssignment, AROAssignmentModel], AROAssignmentRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, AROAssignmentModel, AROAssignment)
    
    def get_by_date(self, assignment_date: date) -> List[AROAssignment]:
        models = self._session.query(AROAssignmentModel).filter(
            AROAssignmentModel.assignment_date == assignment_date
        ).all()
        return [model.to_domain() for model in models]
    
    def get_by_employee_id(self, employee_id: int, assignment_date: Optional[date] = None) -> List[AROAssignment]:
        query = self._session.query(AROAssignmentModel).filter(
            AROAssignmentModel.employee_id == employee_id
        )
        if assignment_date:
            query = query.filter(AROAssignmentModel.assignment_date == assignment_date)
        models = query.all()
        return [model.to_domain() for model in models]
    
    def get_by_from_team_id(self, team_id: int, assignment_date: date) -> List[AROAssignment]:
        models = self._session.query(AROAssignmentModel).filter(
            and_(
                AROAssignmentModel.from_team_id == team_id,
                AROAssignmentModel.assignment_date == assignment_date
            )
        ).all()
        return [model.to_domain() for model in models]
    
    def get_by_to_team_id(self, team_id: int, assignment_date: date) -> List[AROAssignment]:
        models = self._session.query(AROAssignmentModel).filter(
            and_(
                AROAssignmentModel.to_team_id == team_id,
                AROAssignmentModel.assignment_date == assignment_date
            )
        ).all()
        return [model.to_domain() for model in models]
    
    def get_employees_leaving(self, team_id: int, assignment_date: date, period: Optional[int] = None) -> List[int]:
        query = self._session.query(AROAssignmentModel.employee_id).filter(
            and_(
                AROAssignmentModel.from_team_id == team_id,
                AROAssignmentModel.assignment_date == assignment_date
            )
        )
        if period is not None:
            query = query.filter(
                or_(
                    AROAssignmentModel.period == period,
                    AROAssignmentModel.period == None  # Full-day assignments
                )
            )
        return [employee_id for (employee_id,) in query.all()]
    
    def get_employees_joining(self, team_id: int, assignment_date: date, period: Optional[int] = None) -> List[int]:
        query = self._session.query(AROAssignmentModel.employee_id).filter(
            and_(
                AROAssignmentModel.to_team_id == team_id,
                AROAssignmentModel.assignment_date == assignment_date
            )
        )
        if period is not None:
            query = query.filter(
                or_(
                    AROAssignmentModel.period == period,
                    AROAssignmentModel.period == None  # Full-day assignments
                )
            )
        return [employee_id for (employee_id,) in query.all()]