from contextlib import contextmanager
from typing import Optional, List, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.contexts.employee_management.entities.team_member import TeamMember
from domain.models.TeamMemberModel import TeamMemberModel
from domain.models.RoleModel import RoleModel
from domain.repositories.interfaces.team_member_repository import TeamMemberRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyTeamMemberRepository(BaseSqlAlchemyRepository[TeamMember, TeamMemberModel], TeamMemberRepositoryInterface):
    """
    SQLAlchemy implementation of the TeamMemberRepository interface.

    This class provides the actual implementation for accessing and manipulating
    TeamMember entities in the database using SQLAlchemy.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, TeamMemberModel, TeamMember)
        self.logger = get_logger("heijunka.repositories.team_member")
        self.rate_limited_logger = get_logger("heijunka.repositories.team_member", rate_limit=True)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.

        Yields:
            The SQLAlchemy session.
        """
        try:
            yield self._session
            self._session.commit()
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Database operation failed: {error_msg}",
                extra={
                    "event_type": "database_error",
                    "error_type": type(e).__name__,
                    "repository": "team_member"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in team member repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "team_member"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_team_id(self, team_id: int) -> List[TeamMember]:
        """
        Retrieve all team members for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of team members that belong to the team.
        """
        try:
            self.logger.info(
                f"Retrieving team members for team ID: {team_id}",
                extra={
                    "event_type": "team_members_lookup",
                    "lookup_type": "team_id",
                    "team_id": team_id
                }
            )

            team_member_models = self._session.query(TeamMemberModel).filter(
                TeamMemberModel.team_id == team_id
            ).all()

            count = len(team_member_models)
            self.logger.info(
                f"Found {count} team members for team ID: {team_id}",
                extra={
                    "event_type": "team_members_lookup_success",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "count": count
                }
            )

            return [self._to_domain(model) for model in team_member_models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving team members by team ID: {error_msg}",
                extra={
                    "event_type": "team_members_lookup_error",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get team members by team ID: {error_msg}")

    def get_by_employee_id(self, employee_id: int) -> List[TeamMember]:
        """
        Retrieve all team memberships for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of team members that represent the employee's team memberships.
        """
        try:
            self.logger.info(
                f"Retrieving team memberships for employee ID: {employee_id}",
                extra={
                    "event_type": "team_members_lookup",
                    "lookup_type": "employee_id",
                    "employee_id": employee_id
                }
            )

            team_member_models = self._session.query(TeamMemberModel).filter(
                TeamMemberModel.employee_id == employee_id
            ).all()

            count = len(team_member_models)
            self.logger.info(
                f"Found {count} team memberships for employee ID: {employee_id}",
                extra={
                    "event_type": "team_members_lookup_success",
                    "lookup_type": "employee_id",
                    "employee_id": employee_id,
                    "count": count
                }
            )

            return [self._to_domain(model) for model in team_member_models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving team memberships by employee ID: {error_msg}",
                extra={
                    "event_type": "team_members_lookup_error",
                    "lookup_type": "employee_id",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get team memberships by employee ID: {error_msg}")

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
            self.logger.info(
                f"Adding role '{role_name}' to team member ID: {team_member_id}",
                extra={
                    "event_type": "team_member_role_add",
                    "team_member_id": team_member_id,
                    "role_name": role_name
                }
            )

            with self.session_scope() as session:
                team_member = session.query(TeamMemberModel).get(team_member_id)
                if not team_member:
                    self.logger.info(
                        f"No team member found with ID: {team_member_id}",
                        extra={
                            "event_type": "team_member_role_add_failed",
                            "team_member_id": team_member_id,
                            "role_name": role_name,
                            "reason": "team_member_not_found"
                        }
                    )
                    return False

                role = session.query(RoleModel).filter_by(name=role_name).first()
                if not role:
                    # Create the role if it doesn't exist
                    self.logger.info(
                        f"Creating new role: {role_name}",
                        extra={
                            "event_type": "role_create",
                            "role_name": role_name
                        }
                    )
                    role = RoleModel(name=role_name)
                    session.add(role)
                    session.flush()

                if role in team_member.roles:
                    self.logger.info(
                        f"Team member already has role: {role_name}",
                        extra={
                            "event_type": "team_member_role_add_failed",
                            "team_member_id": team_member_id,
                            "role_name": role_name,
                            "reason": "role_already_assigned"
                        }
                    )
                    return False

                team_member.roles.append(role)

                self.logger.info(
                    f"Successfully added role '{role_name}' to team member ID: {team_member_id}",
                    extra={
                        "event_type": "team_member_role_add_success",
                        "team_member_id": team_member_id,
                        "role_name": role_name
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            return False
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding role to team member: {error_msg}",
                extra={
                    "event_type": "team_member_role_add_error",
                    "team_member_id": team_member_id,
                    "role_name": role_name,
                    "error_type": type(e).__name__
                }
            )
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
            self.logger.info(
                f"Removing role '{role_name}' from team member ID: {team_member_id}",
                extra={
                    "event_type": "team_member_role_remove",
                    "team_member_id": team_member_id,
                    "role_name": role_name
                }
            )

            with self.session_scope() as session:
                team_member = session.query(TeamMemberModel).get(team_member_id)
                if not team_member:
                    self.logger.info(
                        f"No team member found with ID: {team_member_id}",
                        extra={
                            "event_type": "team_member_role_remove_failed",
                            "team_member_id": team_member_id,
                            "role_name": role_name,
                            "reason": "team_member_not_found"
                        }
                    )
                    return False

                role = session.query(RoleModel).filter_by(name=role_name).first()
                if not role or role not in team_member.roles:
                    self.logger.info(
                        f"Role '{role_name}' not found or not assigned to team member ID: {team_member_id}",
                        extra={
                            "event_type": "team_member_role_remove_failed",
                            "team_member_id": team_member_id,
                            "role_name": role_name,
                            "reason": "role_not_found_or_not_assigned"
                        }
                    )
                    return False

                team_member.roles.remove(role)

                self.logger.info(
                    f"Successfully removed role '{role_name}' from team member ID: {team_member_id}",
                    extra={
                        "event_type": "team_member_role_remove_success",
                        "team_member_id": team_member_id,
                        "role_name": role_name
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            return False
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error removing role from team member: {error_msg}",
                extra={
                    "event_type": "team_member_role_remove_error",
                    "team_member_id": team_member_id,
                    "role_name": role_name,
                    "error_type": type(e).__name__
                }
            )
            return False

    def get_roles(self, team_member_id: int) -> List[str]:
        """
        Get all roles assigned to a team member.

        Args:
            team_member_id: The ID of the team member.

        Returns:
            A list of role names assigned to the team member.
        """
        try:
            self.logger.info(
                f"Retrieving roles for team member ID: {team_member_id}",
                extra={
                    "event_type": "team_member_roles_lookup",
                    "team_member_id": team_member_id
                }
            )

            team_member = self._session.query(TeamMemberModel).get(team_member_id)
            if not team_member:
                self.logger.info(
                    f"No team member found with ID: {team_member_id}",
                    extra={
                        "event_type": "team_member_roles_lookup_failed",
                        "team_member_id": team_member_id,
                        "reason": "team_member_not_found"
                    }
                )
                return []

            roles = [role.name for role in team_member.roles]
            role_count = len(roles)

            self.logger.info(
                f"Found {role_count} roles for team member ID: {team_member_id}",
                extra={
                    "event_type": "team_member_roles_lookup_success",
                    "team_member_id": team_member_id,
                    "role_count": role_count,
                    "roles": roles
                }
            )

            return roles
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving roles for team member: {error_msg}",
                extra={
                    "event_type": "team_member_roles_lookup_error",
                    "team_member_id": team_member_id,
                    "error_type": type(e).__name__
                }
            )
            return []

    def get_by_team_and_employee(self, team_id: int, employee_id: int) -> Optional[TeamMember]:
        """
        Retrieve a team member by team ID and employee ID.

        Args:
            team_id: The ID of the team.
            employee_id: The ID of the employee.

        Returns:
            The team member if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving team member by team ID: {team_id} and employee ID: {employee_id}",
                extra={
                    "event_type": "team_member_lookup",
                    "lookup_type": "team_and_employee",
                    "team_id": team_id,
                    "employee_id": employee_id
                }
            )

            team_member = self._session.query(TeamMemberModel).filter(
                TeamMemberModel.team_id == team_id,
                TeamMemberModel.employee_id == employee_id
            ).first()

            if not team_member:
                self.logger.info(
                    f"No team member found for team ID: {team_id} and employee ID: {employee_id}",
                    extra={
                        "event_type": "team_member_lookup_failed",
                        "lookup_type": "team_and_employee",
                        "team_id": team_id,
                        "employee_id": employee_id,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found team member for team ID: {team_id} and employee ID: {employee_id}",
                extra={
                    "event_type": "team_member_lookup_success",
                    "lookup_type": "team_and_employee",
                    "team_id": team_id,
                    "employee_id": employee_id,
                    "team_member_id": team_member.id
                }
            )

            return self._to_domain(team_member)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving team member by team and employee: {error_msg}",
                extra={
                    "event_type": "team_member_lookup_error",
                    "lookup_type": "team_and_employee",
                    "team_id": team_id,
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get team member by team and employee: {error_msg}")

    def _to_domain(self, model: TeamMemberModel) -> TeamMember:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting team member model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "team_id": model.team_id,
                    "employee_id": model.employee_id
                }
            )

            team_member = TeamMember(
                team_member_id=model.id,
                team_id=model.team_id,
                employee_id=model.employee_id,
                roles=[role.to_domain() for role in model.roles],
                team=None,  # We don't load the full team object here
                employee=None  # We don't load the full employee object here
            )

            self.logger.debug(
                "Successfully converted team member model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return team_member
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting team member model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: TeamMember) -> TeamMemberModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            entity_id = entity.team_member_id if hasattr(entity, 'team_member_id') and entity.team_member_id else "new"
            self.logger.debug(
                "Converting team member domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id,
                    "team_id": entity.team_id,
                    "employee_id": entity.employee_id
                }
            )

            model = TeamMemberModel(
                id=entity.team_member_id,
                team_id=entity.team_id,
                employee_id=entity.employee_id
            )

            # Add roles if they exist
            if entity.roles:
                with self.session_scope() as session:
                    for role_entity in entity.roles:
                        role = session.query(RoleModel).filter_by(name=role_entity.name).first()
                        if not role:
                            role = RoleModel(name=role_entity.name)
                            session.add(role)
                            session.flush()
                        model.roles.append(role)

            self.logger.debug(
                "Successfully converted team member domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_id": entity_id
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting team member domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.team_member_id if entity and hasattr(entity, 'team_member_id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: TeamMemberModel, entity: TeamMember) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating team member model from domain entity",
                extra={
                    "event_type": "team_member_model_update",
                    "entity_id": model.id,
                    "team_id": model.team_id,
                    "employee_id": model.employee_id
                }
            )

            # Check for significant changes and log them
            if model.team_id != entity.team_id:
                self.logger.info(
                    "Changing team member team",
                    extra={
                        "event_type": "team_member_field_change",
                        "entity_id": model.id,
                        "field": "team_id",
                        "old_value": model.team_id,
                        "new_value": entity.team_id
                    }
                )

            if model.employee_id != entity.employee_id:
                self.logger.info(
                    "Changing team member employee",
                    extra={
                        "event_type": "team_member_field_change",
                        "entity_id": model.id,
                        "field": "employee_id",
                        "old_value": model.employee_id,
                        "new_value": entity.employee_id
                    }
                )

            # Update the model
            model.team_id = entity.team_id
            model.employee_id = entity.employee_id

            # Update roles
            # First, log the roles that will be removed
            current_roles = [role.name for role in model.roles]
            roles_to_remove = [role for role in current_roles if role not in entity.roles]
            roles_to_add = [role for role in entity.roles if role not in current_roles]

            if roles_to_remove:
                self.logger.info(
                    "Removing roles from team member",
                    extra={
                        "event_type": "team_member_roles_change",
                        "entity_id": model.id,
                        "action": "remove",
                        "roles": roles_to_remove
                    }
                )

            if roles_to_add:
                self.logger.info(
                    "Adding roles to team member",
                    extra={
                        "event_type": "team_member_roles_change",
                        "entity_id": model.id,
                        "action": "add",
                        "roles": roles_to_add
                    }
                )

            # Clear existing roles
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

            self.logger.debug(
                "Successfully updated team member model",
                extra={
                    "event_type": "team_member_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating team member model: {error_msg}",
                extra={
                    "event_type": "team_member_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
