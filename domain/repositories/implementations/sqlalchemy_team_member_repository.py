from contextlib import contextmanager
from typing import Optional, List, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.team_member import TeamMember
from domain.models.TeamMemberModel import TeamMemberModel
from domain.models.RoleModel import RoleModel
from domain.repositories.interfaces.team_member_repository import TeamMemberRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyTeamMemberRepository(BaseSqlAlchemyRepository[TeamMember, TeamMemberModel], TeamMemberRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, TeamMemberModel, TeamMember)

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

    def get_by_team_id(self, team_id: int) -> List[TeamMember]:
        """
        Retrieve all team members for a specific team.
        
        Args:
            team_id: The ID of the team.
            
        Returns:
            A list of team members that belong to the team.
        """
        team_member_models = self._session.query(TeamMemberModel).filter(
            TeamMemberModel.team_id == team_id
        ).all()
        return [self._to_domain(model) for model in team_member_models]

    def get_by_employee_id(self, employee_id: int) -> List[TeamMember]:
        """
        Retrieve all team memberships for a specific employee.
        
        Args:
            employee_id: The ID of the employee.
            
        Returns:
            A list of team members that represent the employee's team memberships.
        """
        team_member_models = self._session.query(TeamMemberModel).filter(
            TeamMemberModel.employee_id == employee_id
        ).all()
        return [self._to_domain(model) for model in team_member_models]

    def add_role(self, team_member_id: int, role_name: str) -> bool:
        """
        Add a role to a team member.
        
        Args:
            team_member_id: The ID of the team member.
            role_name: The name of the role to add.
            
        Returns:
            True if the role was added successfully, False otherwise.
        """
        try:
            team_member = self._session.query(TeamMemberModel).get(team_member_id)
            if not team_member:
                return False
                
            role = self._session.query(RoleModel).filter_by(name=role_name).first()
            if not role:
                # Create the role if it doesn't exist
                role = RoleModel(name=role_name)
                self._session.add(role)
                self._session.flush()
                
            if role in team_member.roles:
                return False
                
            team_member.roles.append(role)
            self._session.commit()
            return True
        except SQLAlchemyError:
            self._session.rollback()
            return False

    def remove_role(self, team_member_id: int, role_name: str) -> bool:
        """
        Remove a role from a team member.
        
        Args:
            team_member_id: The ID of the team member.
            role_name: The name of the role to remove.
            
        Returns:
            True if the role was removed successfully, False otherwise.
        """
        try:
            team_member = self._session.query(TeamMemberModel).get(team_member_id)
            if not team_member:
                return False
                
            role = self._session.query(RoleModel).filter_by(name=role_name).first()
            if not role or role not in team_member.roles:
                return False
                
            team_member.roles.remove(role)
            self._session.commit()
            return True
        except SQLAlchemyError:
            self._session.rollback()
            return False

    def get_roles(self, team_member_id: int) -> List[str]:
        """
        Get all roles assigned to a team member.
        
        Args:
            team_member_id: The ID of the team member.
            
        Returns:
            A list of role names assigned to the team member.
        """
        team_member = self._session.query(TeamMemberModel).get(team_member_id)
        if not team_member:
            return []
            
        return [role.name for role in team_member.roles]

    def get_by_team_and_employee(self, team_id: int, employee_id: int) -> Optional[TeamMember]:
        """
        Retrieve a team member by team ID and employee ID.
        
        Args:
            team_id: The ID of the team.
            employee_id: The ID of the employee.
            
        Returns:
            The team member if found, None otherwise.
        """
        team_member = self._session.query(TeamMemberModel).filter(
            TeamMemberModel.team_id == team_id,
            TeamMemberModel.employee_id == employee_id
        ).first()
        
        if not team_member:
            return None
            
        return self._to_domain(team_member)

    def _to_domain(self, model: TeamMemberModel) -> TeamMember:
        """Convert a TeamMemberModel to a TeamMember domain entity."""
        return TeamMember(
            team_member_id=model.id,
            team_id=model.team_id,
            employee_id=model.employee_id,
            roles=[role.name for role in model.roles],
            team=None,  # We don't load the full team object here
            employee=None  # We don't load the full employee object here
        )

    def _to_model(self, entity: TeamMember) -> TeamMemberModel:
        """Convert a TeamMember domain entity to a TeamMemberModel."""
        model = TeamMemberModel(
            team_member_id=entity.team_member_id,
            team_id=entity.team_id,
            employee_id=entity.employee_id
        )
        
        # Add roles if they exist
        if entity.roles:
            with self.session_scope() as session:
                for role_name in entity.roles:
                    role = session.query(RoleModel).filter_by(name=role_name).first()
                    if not role:
                        role = RoleModel(name=role_name)
                        session.add(role)
                        session.flush()
                    model.roles.append(role)
                    
        return model

    def _update_model(self, model: TeamMemberModel, entity: TeamMember) -> None:
        """Update a TeamMemberModel with values from a TeamMember domain entity."""
        model.team_id = entity.team_id
        model.employee_id = entity.employee_id
        
        # Update roles
        # First, clear existing roles
        model.roles.clear()
        
        # Then add the new roles
        if entity.roles:
            with self.session_scope() as session:
                for role_name in entity.roles:
                    role = session.query(RoleModel).filter_by(name=role_name).first()
                    if not role:
                        role = RoleModel(name=role_name)
                        session.add(role)
                        session.flush()
                    model.roles.append(role)