from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, distinct

from domain.entities.workstation import Workstation
from domain.models.WorkstationModel import WorkstationModel
from domain.models.LineTypeModel import LineTypeModel
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger
from domain.factories.workstation_factory import WorkstationFactory


class SqlAlchemyWorkstationRepository(BaseSqlAlchemyRepository[Workstation, WorkstationModel], WorkstationRepositoryInterface):
    """
    SQLAlchemy implementation of the WorkstationRepository interface.

    This class provides the actual implementation for accessing and manipulating
    Workstation entities in the database using SQLAlchemy.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, WorkstationModel, Workstation)
        self.logger = get_logger("heijunka.repositories.workstation")
        self.rate_limited_logger = get_logger("heijunka.repositories.workstation", rate_limit=True)

    # Core CRUD Operations

    def get(self, id: int) -> Optional[Workstation]:
        """
        Retrieve a Workstation aggregate by its ID.

        Args:
            id: The unique identifier of the workstation.

        Returns:
            A Workstation entity if found; otherwise, None.
        """
        return self.get_by_id(id)  # Use the base class implementation

    def add(self, entity: Workstation) -> Workstation:
        """
        Add a new Workstation entity to the repository.

        Args:
            entity: The Workstation entity to add.

        Returns:
            The added Workstation entity with updated ID.

        Raises:
            RepositoryError: If there is an error adding the entity.
        """
        self.logger.info(
            "Adding new Workstation",
            extra={
                "event_type": "workstation_add",
                "workstation_name": entity.name,
                "team_id": entity.team_id
            }
        )

        try:
            return super().add(entity)
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding Workstation: {error_msg}",
                extra={
                    "event_type": "workstation_add_error",
                    "workstation_name": entity.name,
                    "team_id": entity.team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to add workstation: {error_msg}")

    def update(self, entity: Workstation) -> Workstation:
        """
        Update an existing Workstation entity in the repository.

        Args:
            entity: The Workstation entity to update.

        Returns:
            The updated Workstation entity.

        Raises:
            RepositoryError: If there is an error updating the entity.
        """
        self.logger.info(
            f"Updating Workstation with ID: {entity.id}",
            extra={
                "event_type": "workstation_update",
                "workstation_id": entity.id,
                "workstation_name": entity.name,
                "team_id": entity.team_id
            }
        )

        try:
            return super().update(entity)
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating Workstation: {error_msg}",
                extra={
                    "event_type": "workstation_update_error",
                    "workstation_id": entity.id,
                    "workstation_name": entity.name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update workstation: {error_msg}")

    def delete(self, entity_id: int) -> bool:
        """
        Delete a Workstation entity from the repository.

        Args:
            entity_id: The ID of the Workstation entity to delete.

        Returns:
            True if the entity was deleted, False if it wasn't found.

        Raises:
            RepositoryError: If there is an error deleting the entity.
        """
        self.logger.info(
            f"Deleting Workstation with ID: {entity_id}",
            extra={
                "event_type": "workstation_delete",
                "workstation_id": entity_id
            }
        )

        try:
            return super().delete(entity_id)
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting Workstation: {error_msg}",
                extra={
                    "event_type": "workstation_delete_error",
                    "workstation_id": entity_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to delete workstation: {error_msg}")

    def get_filtered(self,
                  team_id: Optional[int] = None,
                  team_ids: Optional[List[int]] = None,
                  is_active: Optional[bool] = None,
                  skip: int = 0,
                  limit: int = 100,
                  eager: bool = False,
                  count_total: bool = False) -> Tuple[List[Workstation], Optional[int]]:
        """
        Get workstations with flexible filtering, pagination, and optional eager loading.

        Args:
            team_id: Filter by a single team ID
            team_ids: Filter by multiple team IDs
            is_active: Filter by active status
            skip: Number of records to skip
            limit: Maximum number of records to return
            eager: Whether to eagerly load related entities
            count_total: Whether to return the total count (for UI pagination)

        Returns:
            A tuple containing:
            - A list of workstations that match the filters
            - The total count of matching records (if count_total=True), otherwise None
        """
        try:
            self.logger.info(
                "Retrieving filtered workstations",
                extra={
                    "event_type": "workstations_filtered_list",
                    "team_id": team_id,
                    "team_ids_count": len(team_ids) if team_ids else 0,
                    "is_active": is_active,
                    "skip": skip,
                    "limit": limit,
                    "eager": eager,
                    "count_total": count_total
                }
            )

            with self.session_scope() as session:
                # Start building the query
                query = session.query(WorkstationModel)

                # Apply filters at the database level
                if team_id is not None:
                    query = query.filter(WorkstationModel.team_id == team_id)

                if team_ids:
                    query = query.filter(WorkstationModel.team_id.in_(team_ids))

                if is_active is not None:
                    query = query.filter(WorkstationModel.is_active == is_active)

                # Get total count if requested
                total_count = None
                if count_total:
                    total_count = query.count()
                    self.logger.info(
                        f"Total matching workstations before pagination: {total_count}",
                        extra={
                            "event_type": "workstations_filtered_count",
                            "total_count": total_count
                        }
                    )

                # Apply eager loading if requested
                if eager:
                    query = query.options(
                        selectinload(WorkstationModel.line_type),
                        selectinload(WorkstationModel.employees),
                        selectinload(WorkstationModel.team),
                        selectinload(WorkstationModel.employee_skills)
                    )

                # Apply pagination at the database level
                paginated_query = query.offset(skip).limit(limit)

                # Execute the query and convert models to domain entities
                models = paginated_query.all()
                result = []
                for model in models:
                    result.append(self._to_domain(model))

            count = len(result)
            self.logger.info(
                f"Retrieved {count} workstations",
                extra={
                    "event_type": "workstations_filtered_list_success",
                    "count": count,
                    "total_count": total_count,
                    "team_id": team_id,
                    "team_ids_count": len(team_ids) if team_ids else 0,
                    "is_active": is_active
                }
            )

            return result, total_count
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving filtered workstations: {error_msg}",
                extra={
                    "event_type": "workstations_filtered_list_error",
                    "team_id": team_id,
                    "team_ids_count": len(team_ids) if team_ids else 0,
                    "is_active": is_active,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get filtered workstations: {error_msg}")

    def get_all(self, team_id: Optional[int] = None, is_active: Optional[bool] = None,
                skip: int = 0, limit: int = 100) -> List[Workstation]:
        """
        Get all workstations with filtering and pagination.

        Args:
            team_id: Filter by team ID
            is_active: Filter by active status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            A list of workstations that match the filters
        """
        try:
            self.logger.info(
                "Entering WorkstationRepository.get_all",
                extra={
                    "event_type": "workstations_list",
                    "team_id": team_id,
                    "is_active": is_active,
                    "skip": skip,
                    "limit": limit
                }
            )

            # Delegate to get_filtered
            workstations, _ = self.get_filtered(
                team_id=team_id,
                is_active=is_active,
                skip=skip,
                limit=limit
            )

            return workstations
        except RepositoryError:
            # Re-raise RepositoryError from get_filtered
            raise

    def get_by_name(self, name: str) -> Optional[Workstation]:
        """
        Get a workstation by name.

        Args:
            name: The name of the workstation.

        Returns:
            The workstation if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Looking up workstation by name: {name}",
                extra={
                    "event_type": "workstation_lookup",
                    "lookup_type": "name",
                    "workstation_name": name
                }
            )

            with self.session_scope() as session:
                workstation_model = session.query(WorkstationModel).filter(
                    func.lower(WorkstationModel.name) == func.lower(name)
                ).first()

                if not workstation_model:
                    self.logger.info(
                        f"No workstation found with name: {name}",
                        extra={
                            "event_type": "workstation_lookup_failed",
                            "lookup_type": "name",
                            "workstation_name": name,
                            "reason": "not_found"
                        }
                    )
                    return None

                self.logger.info(
                    f"Found workstation with name: {name}",
                    extra={
                        "event_type": "workstation_lookup_success",
                        "lookup_type": "name",
                        "workstation_name": name,
                        "workstation_id": workstation_model.id
                    }
                )

                return self._to_domain(workstation_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error looking up workstation by name: {error_msg}",
                extra={
                    "event_type": "workstation_lookup_error",
                    "lookup_type": "name",
                    "workstation_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstation by name: {error_msg}")

    def get_by_team_id(self, team_id: int) -> List[Workstation]:
        """
        Retrieve all workstations for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of workstations belonging to the team.
        """
        try:
            self.logger.info(
                f"Retrieving workstations for team ID: {team_id}",
                extra={
                    "event_type": "workstations_lookup",
                    "lookup_type": "team_id",
                    "team_id": team_id
                }
            )

            # Delegate to get_filtered
            workstations, _ = self.get_filtered(team_id=team_id)

            return workstations
        except RepositoryError:
            # Re-raise RepositoryError from get_filtered
            raise

    def get_by_team_ids(self, team_ids: List[int]) -> List[Workstation]:
        """
        Retrieve all workstations for multiple teams in a single query with eager loading.

        Args:
            team_ids: List of team IDs to fetch workstations for.

        Returns:
            A list of workstations belonging to any of the specified teams.
        """
        if not team_ids:
            return []

        try:
            self.logger.info(
                f"Retrieving workstations for {len(team_ids)} teams",
                extra={
                    "event_type": "bulk_workstations_lookup",
                    "team_count": len(team_ids)
                }
            )

            # Delegate to get_filtered with eager loading
            workstations, _ = self.get_filtered(
                team_ids=team_ids,
                eager=True
            )

            return workstations
        except RepositoryError:
            # Re-raise RepositoryError from get_filtered
            raise

    # Helper Methods

    def _fetch_line_type(self, name: str) -> LineTypeModel:
        """
        Fetch a LineTypeModel by name.

        Args:
            name: The name of the line type to fetch.

        Returns:
            The LineTypeModel if found.

        Raises:
            RepositoryError: If the line type is not found.
        """
        try:
            self.logger.debug(
                f"Fetching LineTypeModel by name: {name}",
                extra={
                    "event_type": "line_type_lookup",
                    "line_type_name": name
                }
            )

            with self.session_scope() as session:
                line_type_model = session.query(LineTypeModel).filter(
                    LineTypeModel.name == name
                ).first()

                if not line_type_model:
                    error_msg = f"LineType with name '{name}' not found"
                    self.logger.error(
                        error_msg,
                        extra={
                            "event_type": "line_type_lookup_error",
                            "line_type_name": name,
                            "reason": "not_found"
                        }
                    )
                    raise RepositoryError(error_msg)

                return line_type_model
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Database error fetching LineType: {error_msg}",
                extra={
                    "event_type": "line_type_lookup_error",
                    "line_type_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to fetch line type: {error_msg}")

    # Conversion Methods

    def _to_domain(self, model: WorkstationModel) -> Workstation:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.

        Raises:
            RepositoryError: If conversion fails.
        """
        try:
            self.logger.debug(
                f"Converting WorkstationModel [id={model.id}] to domain Workstation",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            workstation = WorkstationFactory.create_from_model(model)

            self.logger.debug(
                "Successfully converted workstation model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return workstation
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting WorkstationModel to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to convert workstation model to domain entity: {error_msg}")

    def _to_model(self, entity: Workstation, for_update: bool = False) -> WorkstationModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.
            for_update: Whether this conversion is for an update operation.
                        If True, includes the ID; if False, omits the ID for new entities.

        Returns:
            The SQLAlchemy model.

        Raises:
            RepositoryError: If conversion fails.
        """
        try:
            entity_id = entity.id if for_update else None

            self.logger.debug(
                f"Converting Workstation domain entity to model (for_update={for_update})",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity.id,
                    "entity_name": entity.name,
                    "for_update": for_update
                }
            )

            # Fetch the LineTypeModel by name
            line_type_model = self._fetch_line_type(entity.line_type)

            # Create a new model
            model = WorkstationModel(
                id=entity_id,
                name=entity.name,
                line_type=line_type_model,
                is_loading_job=entity.is_loading_job,
                is_heavy_job=entity.is_heavy_job,
                is_key_skill_job=entity.is_key_skill_job,
                team_id=entity.team_id
            )

            self.logger.debug(
                "Successfully converted workstation domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_id": entity.id,
                    "entity_name": entity.name
                }
            )

            return model
        except RepositoryError:
            # Re-raise RepositoryError from _fetch_line_type
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting Workstation domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to convert workstation domain entity to model: {error_msg}")

    def _update_model(self, model: WorkstationModel, entity: Workstation) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.

        Raises:
            RepositoryError: If the update fails.
        """
        try:
            self.logger.debug(
                f"Updating WorkstationModel [id={model.id}] from domain entity",
                extra={
                    "event_type": "workstation_model_update",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    "Changing workstation name",
                    extra={
                        "event_type": "workstation_field_change",
                        "entity_id": model.id,
                        "field": "name",
                        "old_value": model.name,
                        "new_value": entity.name
                    }
                )

            if model.is_loading_job != entity.is_loading_job:
                self.logger.info(
                    "Changing workstation loading job status",
                    extra={
                        "event_type": "workstation_field_change",
                        "entity_id": model.id,
                        "field": "is_loading_job",
                        "old_value": model.is_loading_job,
                        "new_value": entity.is_loading_job
                    }
                )

            if model.is_heavy_job != entity.is_heavy_job:
                self.logger.info(
                    "Changing workstation heavy job status",
                    extra={
                        "event_type": "workstation_field_change",
                        "entity_id": model.id,
                        "field": "is_heavy_job",
                        "old_value": model.is_heavy_job,
                        "new_value": entity.is_heavy_job
                    }
                )

            if model.is_key_skill_job != entity.is_key_skill_job:
                self.logger.info(
                    "Changing workstation key skill job status",
                    extra={
                        "event_type": "workstation_field_change",
                        "entity_id": model.id,
                        "field": "is_key_skill_job",
                        "old_value": model.is_key_skill_job,
                        "new_value": entity.is_key_skill_job
                    }
                )

            if model.team_id != entity.team_id:
                self.logger.info(
                    "Changing workstation team",
                    extra={
                        "event_type": "workstation_field_change",
                        "entity_id": model.id,
                        "field": "team_id",
                        "old_value": model.team_id,
                        "new_value": entity.team_id
                    }
                )

            # Check and update line type if needed
            if isinstance(entity.line_type, str):
                current_line_type_name = model.line_type.name if model.line_type else None
                if current_line_type_name != entity.line_type:
                    self.logger.info(
                        "Changing workstation line type",
                        extra={
                            "event_type": "workstation_field_change",
                            "entity_id": model.id,
                            "field": "line_type",
                            "old_value": current_line_type_name,
                            "new_value": entity.line_type
                        }
                    )

                    # Use the centralized helper to fetch line type
                    line_type_model = self._fetch_line_type(entity.line_type)
                    model.line_type = line_type_model
            else:
                model.line_type = entity.line_type

            # Update the model
            model.name = entity.name
            model.is_loading_job = entity.is_loading_job
            model.is_heavy_job = entity.is_heavy_job
            model.is_key_skill_job = entity.is_key_skill_job
            model.team_id = entity.team_id

            # Update timestamp if available
            self._stamp_updated(model)

            self.logger.debug(
                "Successfully updated workstation model",
                extra={
                    "event_type": "workstation_model_update_success",
                    "entity_id": model.id
                }
            )
        except RepositoryError:
            # Re-raise RepositoryError from _fetch_line_type
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating workstation model: {error_msg}",
                extra={
                    "event_type": "workstation_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update workstation model: {error_msg}")
