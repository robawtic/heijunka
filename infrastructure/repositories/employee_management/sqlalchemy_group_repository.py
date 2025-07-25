from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.contexts.employee_management.entities.group import Group
from domain.models.GroupModel import GroupModel
from domain.factories.group_factory import GroupFactory
from domain.repositories.interfaces.group_repository import GroupRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyGroupRepository(BaseSqlAlchemyRepository[Group, GroupModel], GroupRepositoryInterface):
    """
    SQLAlchemy implementation of the GroupRepository interface.

    This repository provides CRUD operations for Group entities and implements
    the GroupRepositoryInterface.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, GroupModel, Group)
        self.logger = get_logger("heijunka.repositories.group")
        self.rate_limited_logger = get_logger("heijunka.repositories.group", rate_limit=True)

    def get_by_name(self, group_name: str) -> Optional[Group]:
        """
        Retrieve a group by its name.

        Args:
            group_name: The name of the group to retrieve.

        Returns:
            The group if found, None otherwise.

        Raises:
            RepositoryError: If there is an error retrieving the group.
        """
        try:
            self.logger.info(
                f"Entering GroupRepository.get_by_name (name={group_name})",
                extra={
                    "event_type": "group_lookup",
                    "lookup_type": "name",
                    "group_name": group_name
                }
            )

            group_model = self._session.query(GroupModel).filter(
                GroupModel.name == group_name
            ).first()

            if group_model is None:
                self.logger.info(
                    f"No group found with name: {group_name}",
                    extra={
                        "event_type": "group_lookup_failed",
                        "lookup_type": "name",
                        "group_name": group_name,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found group with ID: {group_model.id}",
                extra={
                    "event_type": "group_lookup_success",
                    "lookup_type": "name",
                    "group_name": group_name,
                    "group_id": group_model.id
                }
            )

            # Use rate-limited logger for potentially high-frequency debug logs
            self.rate_limited_logger.debug(
                f"Converting GroupModel [id={group_model.id}] to domain Group",
                event_type="model_to_domain_conversion",
                identifier=str(group_model.id),
                extra={
                    "entity_type": "Group"
                }
            )

            return GroupFactory.create_from_model(group_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in GroupRepository.get_by_name: {error_msg}",
                extra={
                    "event_type": "group_lookup_error",
                    "lookup_type": "name",
                    "group_name": group_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving group by name: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in GroupRepository.get_by_name: {error_msg}",
                extra={
                    "event_type": "group_lookup_error",
                    "lookup_type": "name",
                    "group_name": group_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving group by name: {error_msg}")

    def _to_domain(self, model: GroupModel) -> Group:
        """
        Convert a GroupModel to a Group domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                f"Converting GroupModel [id={model.id}] to domain Group",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_type": "Group"
                }
            )

            return GroupFactory.create_from_model(model)
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting GroupModel to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Group) -> GroupModel:
        """
        Convert a Group domain entity to a GroupModel.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            entity_id = entity.id if entity.id is not None else "new"
            self.logger.debug(
                f"Converting domain Group [id={entity_id}] to GroupModel",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id,
                    "entity_type": "Group"
                }
            )

            return GroupFactory.to_model(entity)
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting domain Group to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: GroupModel, entity: Group) -> None:
        """
        Update a GroupModel with values from a Group domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                f"Updating GroupModel [id={model.id}] from domain Group",
                extra={
                    "event_type": "model_update",
                    "entity_id": model.id,
                    "entity_type": "Group"
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    f"Changing group name from '{model.name}' to '{entity.name}'",
                    extra={
                        "event_type": "field_change",
                        "entity_id": model.id,
                        "entity_type": "Group",
                        "field": "name",
                        "old_value": model.name,
                        "new_value": entity.name
                    }
                )

            if model.department_id != entity.department_id:
                self.logger.info(
                    f"Changing group department from {model.department_id} to {entity.department_id}",
                    extra={
                        "event_type": "field_change",
                        "entity_id": model.id,
                        "entity_type": "Group",
                        "field": "department_id",
                        "old_value": model.department_id,
                        "new_value": entity.department_id
                    }
                )

            # Update the model using the factory
            GroupFactory.update_model(model, entity)

            self.logger.debug(
                f"Successfully updated GroupModel [id={model.id}]",
                extra={
                    "event_type": "model_update_success",
                    "entity_id": model.id,
                    "entity_type": "Group"
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating GroupModel: {error_msg}",
                extra={
                    "event_type": "model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def get_by_id(self, entity_id: int) -> Optional[Group]:
        """
        Retrieve a group by its ID.

        Args:
            entity_id: The ID of the group to retrieve.

        Returns:
            The group if found, None otherwise.

        Raises:
            RepositoryError: If there is an error retrieving the group.
        """
        try:
            self.logger.info(
                f"Entering GroupRepository.get_by_id (id={entity_id})",
                extra={
                    "event_type": "group_lookup",
                    "lookup_type": "id",
                    "entity_id": entity_id
                }
            )

            # Use session.get for more efficient primary key lookup
            group_model = self._session.get(GroupModel, entity_id)

            if group_model is None:
                self.logger.info(
                    f"No group found with ID: {entity_id}",
                    extra={
                        "event_type": "group_lookup_failed",
                        "lookup_type": "id",
                        "entity_id": entity_id,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found group with ID: {entity_id}",
                extra={
                    "event_type": "group_lookup_success",
                    "lookup_type": "id",
                    "entity_id": entity_id
                }
            )

            # Use rate-limited logger for potentially high-frequency debug logs
            self.rate_limited_logger.debug(
                f"Converting GroupModel [id={group_model.id}] to domain Group",
                event_type="model_to_domain_conversion",
                identifier=str(group_model.id),
                extra={
                    "entity_type": "Group"
                }
            )

            return GroupFactory.create_from_model(group_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in GroupRepository.get_by_id: {error_msg}",
                extra={
                    "event_type": "group_lookup_error",
                    "lookup_type": "id",
                    "entity_id": entity_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving group by ID: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in GroupRepository.get_by_id: {error_msg}",
                extra={
                    "event_type": "group_lookup_error",
                    "lookup_type": "id",
                    "entity_id": entity_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving group by ID: {error_msg}")

    def add(self, entity: Group) -> Group:
        """
        Add a new group.

        Args:
            entity: The group to add.

        Returns:
            The added group with its new ID.

        Raises:
            RepositoryError: If there is an error adding the group.
        """
        try:
            entity_id = getattr(entity, 'id', 'new')
            self.logger.info(
                f"Entering GroupRepository.add (entity_id={entity_id})",
                extra={
                    "event_type": "group_add",
                    "entity_type": "Group",
                    "entity_id": entity_id
                }
            )

            # Use rate-limited logger for potentially high-frequency debug logs
            self.rate_limited_logger.debug(
                f"Converting domain Group [id={entity_id}] to GroupModel",
                event_type="domain_to_model_conversion",
                identifier=str(entity_id),
                extra={
                    "entity_type": "Group"
                }
            )

            with self.session_scope() as session:
                model = GroupFactory.to_model(entity)
                session.add(model)
                session.flush()  # Flush to get the ID if it's auto-generated

                # Get the ID after flush
                model_id = model.id

                self.logger.info(
                    f"Successfully added Group with ID: {model_id}",
                    extra={
                        "event_type": "group_add_success",
                        "entity_type": "Group",
                        "entity_id": model_id
                    }
                )

                # Use rate-limited logger for potentially high-frequency debug logs
                self.rate_limited_logger.debug(
                    f"Converting GroupModel [id={model_id}] to domain Group",
                    event_type="model_to_domain_conversion",
                    identifier=str(model_id),
                    extra={
                        "entity_type": "Group"
                    }
                )

                return GroupFactory.create_from_model(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in GroupRepository.add: {error_msg}",
                extra={
                    "event_type": "group_add_error",
                    "entity_type": "Group",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error adding group: {error_msg}")

    def update(self, entity: Group) -> Group:
        """
        Update an existing group.

        Args:
            entity: The group to update.

        Returns:
            The updated group.

        Raises:
            RepositoryError: If there is an error updating the group or if the group doesn't exist.
        """
        try:
            entity_id = getattr(entity, 'id', None)
            if entity_id is None:
                error_msg = "Cannot update group without ID"
                self.logger.error(
                    error_msg,
                    extra={
                        "event_type": "group_update_error",
                        "entity_type": "Group",
                        "reason": "missing_id"
                    }
                )
                raise RepositoryError(error_msg)

            self.logger.info(
                f"Entering GroupRepository.update (entity_id={entity_id})",
                extra={
                    "event_type": "group_update",
                    "entity_type": "Group",
                    "entity_id": entity_id
                }
            )

            with self.session_scope() as session:
                # Use session.get for more efficient primary key lookup
                model = session.get(GroupModel, entity_id)
                if model is None:
                    error_msg = f"Group with ID {entity_id} not found"
                    self.logger.warning(
                        error_msg,
                        extra={
                            "event_type": "group_update_failed",
                            "entity_type": "Group",
                            "entity_id": entity_id,
                            "reason": "not_found"
                        }
                    )
                    raise RepositoryError(error_msg)

                # Use rate-limited logger for potentially high-frequency debug logs
                self.rate_limited_logger.debug(
                    f"Updating GroupModel [id={model.id}] from domain Group",
                    event_type="model_update",
                    identifier=str(model.id),
                    extra={
                        "entity_type": "Group"
                    }
                )

                # Check for significant changes and log them
                if model.name != entity.name:
                    self.logger.info(
                        f"Changing group name from '{model.name}' to '{entity.name}'",
                        extra={
                            "event_type": "field_change",
                            "entity_id": model.id,
                            "entity_type": "Group",
                            "field": "name",
                            "old_value": model.name,
                            "new_value": entity.name
                        }
                    )

                if model.department_id != entity.department_id:
                    self.logger.info(
                        f"Changing group department from {model.department_id} to {entity.department_id}",
                        extra={
                            "event_type": "field_change",
                            "entity_id": model.id,
                            "entity_type": "Group",
                            "field": "department_id",
                            "old_value": model.department_id,
                            "new_value": entity.department_id
                        }
                    )

                GroupFactory.update_model(model, entity)

                self.logger.info(
                    f"Successfully updated Group with ID: {entity_id}",
                    extra={
                        "event_type": "group_update_success",
                        "entity_type": "Group",
                        "entity_id": entity_id
                    }
                )

                # Use rate-limited logger for potentially high-frequency debug logs
                self.rate_limited_logger.debug(
                    f"Converting GroupModel [id={model.id}] to domain Group",
                    event_type="model_to_domain_conversion",
                    identifier=str(model.id),
                    extra={
                        "entity_type": "Group"
                    }
                )

                return GroupFactory.create_from_model(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in GroupRepository.update: {error_msg}",
                extra={
                    "event_type": "group_update_error",
                    "entity_type": "Group",
                    "entity_id": getattr(entity, 'id', None),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error updating group: {error_msg}")

    def delete(self, entity_id: int) -> bool:
        """
        Delete a group by its ID.

        Args:
            entity_id: The ID of the group to delete.

        Returns:
            True if the group was deleted, False if it wasn't found.

        Raises:
            RepositoryError: If there is an error deleting the group.
        """
        try:
            self.logger.info(
                f"Entering GroupRepository.delete (entity_id={entity_id})",
                extra={
                    "event_type": "group_delete",
                    "entity_type": "Group",
                    "entity_id": entity_id
                }
            )

            with self.session_scope() as session:
                # Use session.get for more efficient primary key lookup
                model = session.get(GroupModel, entity_id)
                if model is None:
                    self.logger.info(
                        f"No group found with ID: {entity_id} to delete",
                        extra={
                            "event_type": "group_delete_failed",
                            "entity_type": "Group",
                            "entity_id": entity_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                session.delete(model)

                self.logger.info(
                    f"Successfully deleted Group with ID: {entity_id}",
                    extra={
                        "event_type": "group_delete_success",
                        "entity_type": "Group",
                        "entity_id": entity_id
                    }
                )

                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in GroupRepository.delete: {error_msg}",
                extra={
                    "event_type": "group_delete_error",
                    "entity_type": "Group",
                    "entity_id": entity_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error deleting group with ID {entity_id}: {error_msg}")

    def list_all(self) -> List[Group]:
        """
        Retrieve all groups.

        Returns:
            A list of all groups.

        Raises:
            RepositoryError: If there is an error retrieving the groups.
        """
        try:
            self.logger.info(
                "Entering GroupRepository.list_all",
                extra={
                    "event_type": "group_list_all",
                    "entity_type": "Group"
                }
            )

            group_models = self._session.query(GroupModel).all()
            count = len(group_models)

            self.logger.info(
                f"Retrieved {count} groups",
                extra={
                    "event_type": "group_list_all_success",
                    "entity_type": "Group",
                    "count": count
                }
            )

            groups = []
            for model in group_models:
                # Use rate-limited logger for potentially high-frequency debug logs
                self.rate_limited_logger.debug(
                    f"Converting GroupModel [id={model.id}] to domain Group",
                    event_type="model_to_domain_conversion",
                    identifier=str(model.id),
                    extra={
                        "entity_type": "Group"
                    }
                )
                groups.append(GroupFactory.create_from_model(model))

            return groups
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in GroupRepository.list_all: {error_msg}",
                extra={
                    "event_type": "group_list_all_error",
                    "entity_type": "Group",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving all groups: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in GroupRepository.list_all: {error_msg}",
                extra={
                    "event_type": "group_list_all_error",
                    "entity_type": "Group",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving all groups: {error_msg}")
