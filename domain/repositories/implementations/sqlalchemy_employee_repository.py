from contextlib import contextmanager
from typing import Optional, List, Dict, Tuple, Generator, Any
from datetime import date
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.employee import Employee
from domain.models import EmployeeWorkstationModel, EmployeeWorkHistoryModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.RoleModel import RoleModel
from domain.models.TeamModel import TeamModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyEmployeeRepository(BaseSqlAlchemyRepository[Employee, EmployeeModel], EmployeeRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, EmployeeModel, Employee)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        try:
            yield self._session
            self._session.commit()
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Database operation failed: {str(e)}")
        except Exception as e:
            self._session.rollback()
            raise

    def get_by_team_id(self, team_id: int) -> List[Employee]:
        """Retrieve all employees for a specific team and return as domain entities."""
        employee_models = self._session.query(EmployeeModel).filter(
            EmployeeModel.team_id == team_id
        ).all()
        return [model.to_domain() for model in employee_models]

    def is_available(self, employee_id: int, date_obj: date, period: Optional[int] = None) -> bool:
        """Check if employee is available on the given date and period."""
        employee = self._session.query(EmployeeModel).get(employee_id)
        if not employee:
            return False

        for av in employee.availability:
            if av.date != date_obj:
                continue
            if av.is_call_in or av.is_aro:
                return False
            if av.is_partial and period is not None and av.period == period:
                return False
        return True

    def assign_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """Assign a role to an employee within a team."""
        employee = self._session.query(EmployeeModel).get(employee_id)
        team = self._session.query(TeamModel).get(team_id)

        if not employee or not team:
            return {"status": "error", "message": "Employee or team not found"}

        for team_member in employee.teams:
            if team_member.team == team:
                role = self._session.query(RoleModel).filter_by(role_name=role_name).first()
                if not role:
                    return {"status": "error", "message": f"RoleModel '{role_name}' not found"}

                if role in team_member.roles:
                    return {"status": "exists", "message": f"Already has role '{role_name}'"}

                team_member.roles.append(role)
                self._session.commit()
                return {"status": "success", "message": f"RoleModel '{role_name}' assigned"}

        return {"status": "error", "message": "Employee not in team"}

    def remove_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """Remove a role from an employee within a team."""
        employee = self._session.query(EmployeeModel).get(employee_id)
        team = self._session.query(TeamModel).get(team_id)

        if not employee or not team:
            return {"status": "error", "message": "Employee or team not found"}

        for team_member in employee.teams:
            if team_member.team == team:
                for role in team_member.roles:
                    if role.name == role_name:
                        team_member.roles.remove(role)
                        self._session.commit()
                        return {"status": "success", "message": f"Removed role '{role_name}'"}

        return {"status": "error", "message": f"RoleModel '{role_name}' not found"}

    def assign_workstation(self, employee_id: int, workstation_id: int) -> Dict[str, str]:
        try:
            # Verify employee and workstation exist
            employee = self._session.query(EmployeeModel).get(employee_id)
            workstation = self._session.query(WorkstationModel).get(workstation_id)

            if not employee or not workstation:
                return {"status": "error", "message": "Employee or workstation not found"}

            existing = self._session.query(EmployeeWorkstationModel).filter_by(
                employee_id=employee_id,
                station_id=workstation_id
            ).first()

            if existing:
                return {"status": "exists", "message": f"Already assigned to {workstation.name}"}

            new_assignment = EmployeeWorkstationModel(
                employee_id=employee_id,
                station_id=workstation_id
            )
            self._session.add(new_assignment)
            self._session.commit()

            return {"status": "success", "message": f"Assigned to {workstation.name}"}

        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Database error while assigning workstation: {str(e)}")

    def get_work_history(self, employee_id: int, workstation_id: int) -> list:
        """Get employee's work history for a specific workstation."""
        return self._session.query(EmployeeWorkHistoryModel).filter(
            EmployeeWorkHistoryModel.employee_id == employee_id,
            EmployeeWorkHistoryModel.station_id == workstation_id
        ).all()

    def add_work_history(self, employee_id: int, workstation_id: int,
                         worked_date: date, work_period: int, end_flag: bool = False) -> bool:
        """Add a work history entry."""
        try:
            self._session.add(EmployeeWorkHistoryModel(
                employee_id=employee_id,
                station_id=workstation_id,
                worked_date=worked_date,
                work_period=work_period,
                end_flag=end_flag
            ))
            self._session.commit()
            return True
        except SQLAlchemyError:
            self._session.rollback()
            return False

    def get_last_worked_date(self, employee_id: int,
                             workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """Get the last date an employee worked at a specific workstation."""
        entry = self._session.query(EmployeeWorkHistoryModel).filter(
            and_(
                EmployeeWorkHistoryModel.employee_id == employee_id,
                EmployeeWorkHistoryModel.station_id == workstation_id
            )
        ).order_by(
            EmployeeWorkHistoryModel.worked_date.desc(),
            EmployeeWorkHistoryModel.work_period.desc()
        ).first()

        if entry:
            return entry.worked_date, entry.work_period
        return None, None

    def _to_domain(self, model: EmployeeModel) -> Employee:
        """Convert a SQLAlchemy model to a domain entity using factory."""
        from domain.factories.employee_factory import EmployeeFactory
        return EmployeeFactory.create_from_model(model)

    def _to_model(self, entity: Employee) -> EmployeeModel:
        """Convert a domain entity to a SQLAlchemy model."""
        model = EmployeeModel(
            id=entity.id,
            name=entity.name,
            team_id=entity.team_id,
            is_active=entity.is_active
        )
        return model

    def _update_model(self, model: EmployeeModel, entity: Employee) -> None:
        """Update a SQLAlchemy model with values from a domain entity."""
        model.name = entity.name
        model.team_id = entity.team_id
        model.is_active = entity.is_active
        # Roles and qualifications would need to be updated through their respective relationships

    def get_by_name(self, name: str) -> Optional[Employee]:
        """Get an employee by name."""
        employee_model = self._session.query(EmployeeModel).filter(EmployeeModel.name == name).first()
        if not employee_model:
            return None
        return employee_model.to_domain()
