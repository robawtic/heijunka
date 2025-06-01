from contextlib import contextmanager
from typing import Optional, List, Generator
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.role import Role
from domain.models.RoleModel import RoleModel
from domain.models.team_member_roles import team_member_roles
from domain.models.TeamMemberModel import TeamMemberModel
from domain.repositories.interfaces.role_repository import RoleRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyRoleRepository(BaseSqlAlchemyRepository[Role, RoleModel], RoleRepositoryInterface):
    """
    SQLAlchemy implementation of the role repository.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, RoleModel, Role)
        self.logger = get_logger("heijunka.repositories.role")

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
                    "repository": "RoleRepository"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "RoleRepository"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_name(self, name: str) -> Optional[Role]:
        """
        Retrieve a role by its name.

        Args:
            name: The name of the role to retrieve.

        Returns:
            The role if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving role by name: {name}",
                extra={
                    "event_type": "role_lookup",
                    "lookup_type": "name",
                    "role_name": name
                }
            )

            role_model = self._session.query(RoleModel).filter(RoleModel.name == name).first()
            if not role_model:
                self.logger.info(
                    f"No role found with name: {name}",
                    extra={
                        "event_type": "role_lookup_failed",
                        "lookup_type": "name",
                        "role_name": name,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Successfully retrieved role by name: {name}",
                extra={
                    "event_type": "role_lookup_success",
                    "lookup_type": "name",
                    "role_name": name,
                    "role_id": role_model.id
                }
            )

            return self._to_domain(role_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving role by name: {error_msg}",
                extra={
                    "event_type": "role_lookup_error",
                    "lookup_type": "name",
                    "role_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get role by name: {error_msg}")

    def name_exists(self, name: str) -> bool:
        """
        Check if a role name already exists.

        Args:
            name: The role name to check.

        Returns:
            True if the role name exists, False otherwise.
        """
        try:
            self.logger.info(
                f"Checking if role name exists: {name}",
                extra={
                    "event_type": "role_name_check",
                    "role_name": name
                }
            )

            exists = self._session.query(RoleModel).filter(RoleModel.name == name).first() is not None

            self.logger.info(
                f"Role name check result: {exists}",
                extra={
                    "event_type": "role_name_check_result",
                    "role_name": name,
                    "exists": exists
                }
            )

            return exists
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error checking if role name exists: {error_msg}",
                extra={
                    "event_type": "role_name_check_error",
                    "role_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to check if role name exists: {error_msg}")

    def get_all_roles(self) -> List[Role]:
        """
        Get all roles in the system.

        Returns:
            A list of all roles.
        """
        try:
            self.logger.info(
                "Retrieving all roles",
                extra={
                    "event_type": "get_all_roles"
                }
            )

            role_models = self._session.query(RoleModel).all()
            roles = [self._to_domain(role_model) for role_model in role_models]

            self.logger.info(
                f"Successfully retrieved {len(roles)} roles",
                extra={
                    "event_type": "get_all_roles_success",
                    "role_count": len(roles)
                }
            )

            return roles
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving all roles: {error_msg}",
                extra={
                    "event_type": "get_all_roles_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get all roles: {error_msg}")

    def create_role(self, name: str, description: str = None) -> Role:
        """
        Create a new role.

        Args:
            name: The name of the role.
            description: Optional description of the role.

        Returns:
            The created role.
        """
        try:
            self.logger.info(
                f"Creating new role: {name}",
                extra={
                    "event_type": "create_role",
                    "role_name": name
                }
            )

            # Check if role with this name already exists
            if self.name_exists(name):
                self.logger.warning(
                    f"Role with name '{name}' already exists",
                    extra={
                        "event_type": "create_role_failed",
                        "role_name": name,
                        "reason": "name_exists"
                    }
                )
                raise RepositoryError(f"Role with name '{name}' already exists")

            # Create new role model
            role_model = RoleModel(name=name, description=description)
            self._session.add(role_model)
            self._session.commit()

            self.logger.info(
                f"Successfully created role: {name}",
                extra={
                    "event_type": "create_role_success",
                    "role_name": name,
                    "role_id": role_model.id
                }
            )

            return self._to_domain(role_model)
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error creating role: {error_msg}",
                extra={
                    "event_type": "create_role_error",
                    "role_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to create role: {error_msg}")

    def update_role(self, role_id: int, name: str = None, description: str = None) -> Optional[Role]:
        """
        Update an existing role.

        Args:
            role_id: The ID of the role to update.
            name: Optional new name for the role.
            description: Optional new description for the role.

        Returns:
            The updated role if successful, None otherwise.
        """
        try:
            self.logger.info(
                f"Updating role with ID: {role_id}",
                extra={
                    "event_type": "update_role",
                    "role_id": role_id
                }
            )

            # Get the role model
            role_model = self._session.query(RoleModel).filter(RoleModel.id == role_id).first()
            if not role_model:
                self.logger.warning(
                    f"Role with ID {role_id} not found",
                    extra={
                        "event_type": "update_role_failed",
                        "role_id": role_id,
                        "reason": "not_found"
                    }
                )
                return None

            # Update fields if provided
            if name is not None:
                # Check if another role with this name already exists
                existing_role = self._session.query(RoleModel).filter(
                    RoleModel.name == name, 
                    RoleModel.id != role_id
                ).first()
                if existing_role:
                    self.logger.warning(
                        f"Another role with name '{name}' already exists",
                        extra={
                            "event_type": "update_role_failed",
                            "role_id": role_id,
                            "new_name": name,
                            "reason": "name_exists"
                        }
                    )
                    raise RepositoryError(f"Another role with name '{name}' already exists")
                role_model.name = name

            if description is not None:
                role_model.description = description

            # Update timestamp
            role_model.updated_at = datetime.utcnow()

            self._session.commit()

            self.logger.info(
                f"Successfully updated role with ID: {role_id}",
                extra={
                    "event_type": "update_role_success",
                    "role_id": role_id,
                    "role_name": role_model.name
                }
            )

            return self._to_domain(role_model)
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating role: {error_msg}",
                extra={
                    "event_type": "update_role_error",
                    "role_id": role_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update role: {error_msg}")

    def delete_role(self, role_id: int) -> bool:
        """
        Delete a role.

        Args:
            role_id: The ID of the role to delete.

        Returns:
            True if the role was deleted successfully, False otherwise.
        """
        try:
            self.logger.info(
                f"Deleting role with ID: {role_id}",
                extra={
                    "event_type": "delete_role",
                    "role_id": role_id
                }
            )

            # Get the role model
            role_model = self._session.query(RoleModel).filter(RoleModel.id == role_id).first()
            if not role_model:
                self.logger.warning(
                    f"Role with ID {role_id} not found",
                    extra={
                        "event_type": "delete_role_failed",
                        "role_id": role_id,
                        "reason": "not_found"
                    }
                )
                return False

            # Delete the role
            self._session.delete(role_model)
            self._session.commit()

            self.logger.info(
                f"Successfully deleted role with ID: {role_id}",
                extra={
                    "event_type": "delete_role_success",
                    "role_id": role_id
                }
            )

            return True
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting role: {error_msg}",
                extra={
                    "event_type": "delete_role_error",
                    "role_id": role_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to delete role: {error_msg}")

    def get_roles_for_team_member(self, team_member_id: int) -> List[Role]:
        """
        Get all roles assigned to a team member.

        Args:
            team_member_id: The ID of the team member.

        Returns:
            A list of roles assigned to the team member.
        """
        try:
            self.logger.info(
                f"Retrieving roles for team member with ID: {team_member_id}",
                extra={
                    "event_type": "get_roles_for_team_member",
                    "team_member_id": team_member_id
                }
            )

            # Query roles for the team member
            role_models = self._session.query(RoleModel).join(
                team_member_roles,
                RoleModel.id == team_member_roles.c.role_id
            ).filter(
                team_member_roles.c.team_member_id == team_member_id
            ).all()

            roles = [self._to_domain(role_model) for role_model in role_models]

            self.logger.info(
                f"Successfully retrieved {len(roles)} roles for team member with ID: {team_member_id}",
                extra={
                    "event_type": "get_roles_for_team_member_success",
                    "team_member_id": team_member_id,
                    "role_count": len(roles)
                }
            )

            return roles
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving roles for team member: {error_msg}",
                extra={
                    "event_type": "get_roles_for_team_member_error",
                    "team_member_id": team_member_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get roles for team member: {error_msg}")

    def assign_role_to_team_member(self, team_member_id: int, role_id: int) -> bool:
        """
        Assign a role to a team member.

        Args:
            team_member_id: The ID of the team member.
            role_id: The ID of the role to assign.

        Returns:
            True if the role was assigned successfully, False otherwise.
        """
        try:
            self.logger.info(
                f"Assigning role with ID {role_id} to team member with ID: {team_member_id}",
                extra={
                    "event_type": "assign_role_to_team_member",
                    "team_member_id": team_member_id,
                    "role_id": role_id
                }
            )

            # Check if team member exists
            team_member = self._session.query(TeamMemberModel).filter(
                TeamMemberModel.id == team_member_id
            ).first()
            if not team_member:
                self.logger.warning(
                    f"Team member with ID {team_member_id} not found",
                    extra={
                        "event_type": "assign_role_to_team_member_failed",
                        "team_member_id": team_member_id,
                        "role_id": role_id,
                        "reason": "team_member_not_found"
                    }
                )
                return False

            # Check if role exists
            role = self._session.query(RoleModel).filter(RoleModel.id == role_id).first()
            if not role:
                self.logger.warning(
                    f"Role with ID {role_id} not found",
                    extra={
                        "event_type": "assign_role_to_team_member_failed",
                        "team_member_id": team_member_id,
                        "role_id": role_id,
                        "reason": "role_not_found"
                    }
                )
                return False

            # Check if the role is already assigned
            existing_assignment = self._session.query(team_member_roles).filter(
                team_member_roles.c.team_member_id == team_member_id,
                team_member_roles.c.role_id == role_id
            ).first()
            if existing_assignment:
                self.logger.info(
                    f"Role with ID {role_id} is already assigned to team member with ID: {team_member_id}",
                    extra={
                        "event_type": "assign_role_to_team_member_skipped",
                        "team_member_id": team_member_id,
                        "role_id": role_id,
                        "reason": "already_assigned"
                    }
                )
                return True

            # Assign the role
            stmt = team_member_roles.insert().values(
                team_member_id=team_member_id,
                role_id=role_id
            )
            self._session.execute(stmt)
            self._session.commit()

            self.logger.info(
                f"Successfully assigned role with ID {role_id} to team member with ID: {team_member_id}",
                extra={
                    "event_type": "assign_role_to_team_member_success",
                    "team_member_id": team_member_id,
                    "role_id": role_id
                }
            )

            return True
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error assigning role to team member: {error_msg}",
                extra={
                    "event_type": "assign_role_to_team_member_error",
                    "team_member_id": team_member_id,
                    "role_id": role_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to assign role to team member: {error_msg}")

    def remove_role_from_team_member(self, team_member_id: int, role_id: int) -> bool:
        """
        Remove a role from a team member.

        Args:
            team_member_id: The ID of the team member.
            role_id: The ID of the role to remove.

        Returns:
            True if the role was removed successfully, False otherwise.
        """
        try:
            self.logger.info(
                f"Removing role with ID {role_id} from team member with ID: {team_member_id}",
                extra={
                    "event_type": "remove_role_from_team_member",
                    "team_member_id": team_member_id,
                    "role_id": role_id
                }
            )

            # Check if the assignment exists
            existing_assignment = self._session.query(team_member_roles).filter(
                team_member_roles.c.team_member_id == team_member_id,
                team_member_roles.c.role_id == role_id
            ).first()
            if not existing_assignment:
                self.logger.warning(
                    f"Role with ID {role_id} is not assigned to team member with ID: {team_member_id}",
                    extra={
                        "event_type": "remove_role_from_team_member_failed",
                        "team_member_id": team_member_id,
                        "role_id": role_id,
                        "reason": "not_assigned"
                    }
                )
                return False

            # Remove the role
            stmt = team_member_roles.delete().where(
                team_member_roles.c.team_member_id == team_member_id,
                team_member_roles.c.role_id == role_id
            )
            self._session.execute(stmt)
            self._session.commit()

            self.logger.info(
                f"Successfully removed role with ID {role_id} from team member with ID: {team_member_id}",
                extra={
                    "event_type": "remove_role_from_team_member_success",
                    "team_member_id": team_member_id,
                    "role_id": role_id
                }
            )

            return True
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error removing role from team member: {error_msg}",
                extra={
                    "event_type": "remove_role_from_team_member_error",
                    "team_member_id": team_member_id,
                    "role_id": role_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to remove role from team member: {error_msg}")

    def _to_domain(self, model: RoleModel) -> Role:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting role model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            role = Role(
                id=model.id,
                name=model.name,
                description=model.description,
                created_at=model.created_at,
                updated_at=model.updated_at
            )

            self.logger.debug(
                "Successfully converted role model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return role
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting role model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Role) -> RoleModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting role domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity.id,
                    "entity_name": entity.name
                }
            )

            model = RoleModel(
                id=entity.id,
                name=entity.name,
                description=entity.description,
                created_at=entity.created_at,
                updated_at=entity.updated_at
            )

            self.logger.debug(
                "Successfully converted role domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_id": entity.id
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting role domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: RoleModel, entity: Role) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating role model from domain entity",
                extra={
                    "event_type": "role_model_update",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    f"Role name changed from '{model.name}' to '{entity.name}'",
                    extra={
                        "event_type": "role_name_changed",
                        "entity_id": model.id,
                        "old_name": model.name,
                        "new_name": entity.name
                    }
                )

            if model.description != entity.description:
                self.logger.info(
                    "Role description changed",
                    extra={
                        "event_type": "role_description_changed",
                        "entity_id": model.id,
                        "entity_name": model.name
                    }
                )

            # Update the model
            model.name = entity.name
            model.description = entity.description
            model.updated_at = datetime.utcnow()

            self.logger.debug(
                "Successfully updated role model from domain entity",
                extra={
                    "event_type": "role_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating role model from domain entity: {error_msg}",
                extra={
                    "event_type": "role_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise