from contextlib import contextmanager
from typing import List, Optional, Generator, Dict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from domain.entities.team import Team
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.models import TeamMemberModel
from domain.models.TeamModel import TeamModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyTeamRepository(BaseSqlAlchemyRepository[Team, TeamModel], TeamRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, TeamModel, Team)

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

    def get_by_name(self, name: str) -> Optional[Team]:
        """Retrieve a team by its name."""
        team_model = self._session.query(TeamModel).filter(
            TeamModel.name == name
        ).first()
        if team_model is None:
            return None
        return self._to_domain(team_model)

    def add_member(self, team_id: int, employee: Employee) -> bool:
        """Add an employee to a team."""
        team = self._session.query(TeamModel).get(team_id)
        employee_model = self._session.query(EmployeeModel).get(employee.id)

        if not team or not employee_model:
            return False

        # Check if the employee is already a member of the team
        for member in team.members:
            if member.id == employee.id:
                return True  # Already a member

        # Add the employee to the team
        team_member = TeamMemberModel(team_id=team_id, employee_id=employee.id)
        self._session.add(team_member)
        self._session.commit()
        return True

    def remove_member(self, team_id: int, employee_id: int) -> bool:
        """Remove an employee from a team."""
        team_member = self._session.query(TeamMemberModel).filter(
            TeamMemberModel.team_id == team_id,
            TeamMemberModel.employee_id == employee_id
        ).first()

        if not team_member:
            return False

        self._session.delete(team_member)
        self._session.commit()
        return True

    def add_workstation(self, team_id: int, workstation: Workstation) -> bool:
        """Add a workstation to a team."""
        team = self._session.query(TeamModel).get(team_id)
        workstation_model = self._session.query(WorkstationModel).get(workstation.id)

        if not team or not workstation_model:
            return False

        # Check if the workstation is already assigned to the team
        if workstation_model.team_id == team_id:
            return True  # Already assigned

        # Assign the workstation to the team
        workstation_model.team_id = team_id
        self._session.commit()
        return True

    def remove_workstation(self, team_id: int, workstation_id: int) -> bool:
        """Remove a workstation from a team."""
        workstation = self._session.query(WorkstationModel).filter(
            WorkstationModel.id == workstation_id,
            WorkstationModel.team_id == team_id
        ).first()

        if not workstation:
            return False

        # This is a bit tricky - we don't want to delete the workstation,
        # just unassign it from the team. In a real system, you might set
        # id to NULL or reassign it to a default team.
        workstation.team_id = None
        self._session.commit()
        return True

    def get_members(self, team_id: int) -> List[Employee]:
        """Get all members of a team."""
        team = self._session.query(TeamModel).get(team_id)
        if not team:
            return []

        return [member.employee.to_domain() for member in team.members]

    def get_workstations(self, team_id: int) -> List[Workstation]:
        """Get all workstations of a team."""
        workstations = self._session.query(WorkstationModel).filter(
            WorkstationModel.team_id == team_id
        ).all()

        return [self._workstation_to_domain(ws) for ws in workstations]

    def get_with_counts(self, team_id: int) -> Optional[Dict]:
        """Get a team with employee and workstation counts."""
        result = self._session.query(
            TeamModel,
            func.count(distinct(EmployeeModel.id)).label('employee_count'),
            func.count(distinct(WorkstationModel.id)).label('workstation_count')
        ).outerjoin(
            TeamMemberModel, TeamMemberModel.team_id == TeamModel.id
        ).outerjoin(
            EmployeeModel, EmployeeModel.id == TeamMemberModel.employee_id
        ).outerjoin(
            WorkstationModel, WorkstationModel.team_id == TeamModel.id
        ).filter(
            TeamModel.id == team_id
        ).group_by(
            TeamModel.id
        ).first()

        if not result:
            return None

        team, employee_count, workstation_count = result
        return {
            'team': self._to_domain(team),
            'employee_count': employee_count,
            'workstation_count': workstation_count
        }

    def _to_domain(self, model: TeamModel) -> Team:
        """Convert a TeamModel to a Team domain entity using factory."""
        from domain.factories.team_factory import TeamFactory
        return TeamFactory.create_from_model(model)

    def _to_model(self, entity: Team) -> TeamModel:
        """Convert a Team domain entity to a TeamModel."""
        model = TeamModel(
            id=entity.id,  # Changed from team_id to id to match TeamModel schema
            name=entity.name,  # Changed from team_name to name to match TeamModel schema
            description=entity.description
        )
        return model

    def _update_model(self, model: TeamModel, entity: Team) -> None:
        """Update a TeamModel with values from a Team domain entity."""
        model.name = entity.name
        model.description = entity.description
        # Members and workstations would need to be updated through their respective relationships

    def _workstation_to_domain(self, model: WorkstationModel) -> Workstation:
        """Convert a WorkstationModel to a Workstation domain entity using factory."""
        from domain.factories.workstation_factory import WorkstationFactory
        return WorkstationFactory.create_from_model(model)
