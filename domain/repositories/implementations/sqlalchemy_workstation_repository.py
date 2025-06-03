from contextlib import contextmanager
from typing import List, Optional, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.workstation import Workstation
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyWorkstationRepository(BaseSqlAlchemyRepository[Workstation, WorkstationModel], WorkstationRepositoryInterface):
    """
    SQLAlchemy implementation of the WorkstationRepository interface.

    This class provides the actual implementation for accessing and manipulating
    Workstation entities in the database using SQLAlchemy.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, WorkstationModel, Workstation)
        self.logger = get_logger("heijunka.repositories.workstation")
        self.rate_limited_logger = get_logger("heijunka.repositories.workstation", rate_limit=True)

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
                    "repository": "workstation"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in workstation repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "workstation"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

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

            workstation_models = self._session.query(WorkstationModel).filter(
                WorkstationModel.team_id == team_id
            ).all()

            workstation_count = len(workstation_models)
            self.logger.info(
                f"Found {workstation_count} workstations for team ID: {team_id}",
                extra={
                    "event_type": "workstations_lookup_success",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "count": workstation_count
                }
            )

            return [self._to_domain(model) for model in workstation_models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving workstations by team ID: {error_msg}",
                extra={
                    "event_type": "workstations_lookup_error",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstations by team ID: {error_msg}")

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
                f"Retrieving workstations for {len(team_ids)} teams with eager loading",
                extra={
                    "event_type": "bulk_workstations_lookup",
                    "team_count": len(team_ids)
                }
            )

            # Use SQLAlchemy's selectinload for eager loading related data
            from sqlalchemy.orm import selectinload

            workstation_models = self._session.query(WorkstationModel).filter(
                WorkstationModel.team_id.in_(team_ids)
            ).options(
                selectinload(WorkstationModel.line_type),
                selectinload(WorkstationModel.employees),
                selectinload(WorkstationModel.team),
                selectinload(WorkstationModel.employee_skills)
            ).all()

            workstation_count = len(workstation_models)
            self.logger.info(
                f"Found {workstation_count} workstations for {len(team_ids)} teams with eager loading",
                extra={
                    "event_type": "bulk_workstations_lookup_success",
                    "team_count": len(team_ids),
                    "workstation_count": workstation_count
                }
            )

            return [self._to_domain(model) for model in workstation_models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving workstations for multiple teams: {error_msg}",
                extra={
                    "event_type": "bulk_workstations_lookup_error",
                    "team_count": len(team_ids),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstations for multiple teams: {error_msg}")

    def get_all(self, team_id: Optional[int] = None, is_active: Optional[bool] = None,
                required_qualification: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Workstation]:
        """
        Get all workstations with filtering and pagination.

        Args:
            team_id: Filter by team ID
            is_active: Filter by active status
            required_qualification: Filter by required qualification
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            A list of workstations that match the filters
        """
        try:
            self.logger.info(
                "Retrieving workstations with filters",
                extra={
                    "event_type": "workstations_list",
                    "team_id": team_id,
                    "is_active": is_active,
                    "required_qualification": required_qualification,
                    "skip": skip,
                    "limit": limit
                }
            )

            query = self._session.query(WorkstationModel)

            # Apply filters at the database level
            if team_id is not None:
                query = query.filter(WorkstationModel.team_id == team_id)

            if is_active is not None:
                query = query.filter(WorkstationModel.is_active == is_active)

            if required_qualification is not None:
                # This assumes required_qualifications is stored as a JSON array
                # The exact implementation depends on the database and how qualifications are stored
                # For PostgreSQL with JSONB:
                # query = query.filter(WorkstationModel.required_qualifications.contains([required_qualification]))
                # For SQLite or simpler databases, we might need to filter in Python
                # For now, we'll get all workstations and filter in Python
                self.logger.debug(
                    f"Filtering workstations by required qualification: {required_qualification}",
                    extra={
                        "event_type": "workstations_filter",
                        "filter_type": "required_qualification",
                        "value": required_qualification
                    }
                )

                workstations = query.all()
                filtered_workstations = []
                for ws in workstations:
                    if hasattr(ws, 'required_qualifications') and ws.required_qualifications:
                        if required_qualification in ws.required_qualifications:
                            filtered_workstations.append(ws)

                # Apply pagination in Python
                paginated_workstations = filtered_workstations[skip:skip+limit]
                result = [self._to_domain(model) for model in paginated_workstations]

                count = len(result)
                self.logger.info(
                    f"Retrieved {count} workstations after filtering by required qualification",
                    extra={
                        "event_type": "workstations_list_success",
                        "count": count,
                        "filter": "required_qualification"
                    }
                )

                return result

            # Apply pagination at the database level if no required_qualification filter
            paginated_query = query.offset(skip).limit(limit)
            result = [self._to_domain(model) for model in paginated_query.all()]

            count = len(result)
            self.logger.info(
                f"Retrieved {count} workstations",
                extra={
                    "event_type": "workstations_list_success",
                    "count": count,
                    "team_id": team_id,
                    "is_active": is_active
                }
            )

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving workstations: {error_msg}",
                extra={
                    "event_type": "workstations_list_error",
                    "team_id": team_id,
                    "is_active": is_active,
                    "required_qualification": required_qualification,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstations: {error_msg}")

    def _to_domain(self, model: WorkstationModel) -> Workstation:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting workstation model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            from domain.factories.workstation_factory import WorkstationFactory
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
                f"Error converting workstation model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Workstation) -> WorkstationModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting workstation domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity.id,
                    "entity_name": entity.name
                }
            )

            from domain.models.LineTypeModel import LineTypeModel

            # Query the LineTypeModel by name
            line_type_model = self._session.query(LineTypeModel).filter(
                LineTypeModel.name == entity.line_type
            ).first()

            if not line_type_model:
                error_msg = f"LineType with name '{entity.line_type}' not found"
                self.logger.error(
                    error_msg,
                    extra={
                        "event_type": "domain_to_model_conversion_error",
                        "entity_id": entity.id,
                        "entity_name": entity.name,
                        "line_type": entity.line_type,
                        "reason": "line_type_not_found"
                    }
                )
                raise ValueError(error_msg)

            model = WorkstationModel(
                id=entity.id,
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
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting workstation domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: WorkstationModel, entity: Workstation) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating workstation model from domain entity",
                extra={
                    "event_type": "workstation_model_update",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            from domain.models.LineTypeModel import LineTypeModel

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

            # Query the LineTypeModel by name
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

                line_type_model = self._session.query(LineTypeModel).filter(
                    LineTypeModel.name == entity.line_type
                ).first()

                if not line_type_model:
                    error_msg = f"LineType with name '{entity.line_type}' not found"
                    self.logger.error(
                        error_msg,
                        extra={
                            "event_type": "workstation_model_update_error",
                            "entity_id": model.id,
                            "entity_name": model.name,
                            "line_type": entity.line_type,
                            "reason": "line_type_not_found"
                        }
                    )
                    raise ValueError(error_msg)

                model.line_type = line_type_model
            else:
                model.line_type = entity.line_type

            # Update the model
            model.name = entity.name
            model.is_loading_job = entity.is_loading_job
            model.is_heavy_job = entity.is_heavy_job
            model.is_key_skill_job = entity.is_key_skill_job
            model.team_id = entity.team_id

            self.logger.debug(
                "Successfully updated workstation model",
                extra={
                    "event_type": "workstation_model_update_success",
                    "entity_id": model.id
                }
            )
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
                f"Retrieving workstation by name: {name}",
                extra={
                    "event_type": "workstation_lookup",
                    "lookup_type": "name",
                    "workstation_name": name
                }
            )

            workstation_model = self._session.query(WorkstationModel).filter(WorkstationModel.name == name).first()

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
                f"Error retrieving workstation by name: {error_msg}",
                extra={
                    "event_type": "workstation_lookup_error",
                    "lookup_type": "name",
                    "workstation_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstation by name: {error_msg}")
