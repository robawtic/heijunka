from contextlib import contextmanager
from typing import List, Optional, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.workstation import Workstation
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyWorkstationRepository(BaseSqlAlchemyRepository[Workstation, WorkstationModel], WorkstationRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, WorkstationModel, Workstation)

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

    def get_by_team_id(self, team_id: int) -> List[Workstation]:
        """Retrieve all workstations for a specific team and return as domain entities."""
        workstation_models = self._session.query(WorkstationModel).filter(
            WorkstationModel.team_id == team_id
        ).all()
        return [self._to_domain(model) for model in workstation_models]

    def get_all(self, team_id: Optional[int] = None, is_active: Optional[bool] = None,
                required_qualification: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Workstation]:
        """Get all workstations with filtering and pagination."""
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
            workstations = query.all()
            filtered_workstations = []
            for ws in workstations:
                if hasattr(ws, 'required_qualifications') and ws.required_qualifications:
                    if required_qualification in ws.required_qualifications:
                        filtered_workstations.append(ws)

            # Apply pagination in Python
            return [self._to_domain(model) for model in filtered_workstations[skip:skip+limit]]

        # Apply pagination at the database level if no required_qualification filter
        return [self._to_domain(model) for model in query.offset(skip).limit(limit).all()]

    def _to_domain(self, model: WorkstationModel) -> Workstation:
        """Convert a WorkstationModel to a Workstation domain entity."""
        return Workstation(
            id=model.id,
            name=model.name,
            line_type=model.line_type.name if model.line_type else None,
            is_loading_job=model.is_loading_job,
            is_heavy_job=model.is_heavy_job,
            is_key_skill_job=model.is_key_skill_job,
            team_id=model.team_id
        )

    def _to_model(self, entity: Workstation) -> WorkstationModel:
        """Convert a Workstation domain entity to a WorkstationModel."""
        from domain.models.LineTypeModel import LineTypeModel

        # Query the LineTypeModel by name
        line_type_model = self._session.query(LineTypeModel).filter(
            LineTypeModel.name == entity.line_type
        ).first()

        if not line_type_model:
            raise ValueError(f"LineType with name '{entity.line_type}' not found")

        model = WorkstationModel(
            id=entity.id,
            name=entity.name,
            line_type=line_type_model,
            is_loading_job=entity.is_loading_job,
            is_heavy_job=entity.is_heavy_job,
            is_key_skill_job=entity.is_key_skill_job,
            team_id=entity.team_id
        )
        return model

    def _update_model(self, model: WorkstationModel, entity: Workstation) -> None:
        """Update a WorkstationModel with values from a Workstation domain entity."""
        from domain.models.LineTypeModel import LineTypeModel

        # Query the LineTypeModel by name
        if isinstance(entity.line_type, str):
            line_type_model = self._session.query(LineTypeModel).filter(
                LineTypeModel.name == entity.line_type
            ).first()

            if not line_type_model:
                raise ValueError(f"LineType with name '{entity.line_type}' not found")

            model.line_type = line_type_model
        else:
            model.line_type = entity.line_type

        model.name = entity.name
        model.is_loading_job = entity.is_loading_job
        model.is_heavy_job = entity.is_heavy_job
        model.is_key_skill_job = entity.is_key_skill_job
        model.team_id = entity.team_id

    def get_by_name(self, name: str) -> Optional[Workstation]:
        """Get a workstation by name."""
        workstation_model = self._session.query(WorkstationModel).filter(WorkstationModel.name == name).first()
        if not workstation_model:
            return None
        return self._to_domain(workstation_model)
