from contextlib import contextmanager
from typing import Optional, List, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.department import Department
from domain.models.DepartmentModel import DepartmentModel
from domain.repositories.interfaces.department_repository import DepartmentRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyDepartmentRepository(BaseSqlAlchemyRepository[Department, DepartmentModel], DepartmentRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, DepartmentModel, Department)

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

    def get_by_name(self, department_name: str) -> Optional[Department]:
        """Retrieve a department by its name."""
        department_model = self._session.query(DepartmentModel).filter(
            DepartmentModel.name == department_name
        ).first()
        if department_model is None:
            return None
        return self._to_domain(department_model)
    
    def get_all_with_groups(self) -> List[Department]:
        """Retrieve all departments with their associated groups."""
        from domain.models.GroupModel import GroupModel
        
        departments = []
        department_models = self._session.query(DepartmentModel).all()
        
        for department_model in department_models:
            department = self._to_domain(department_model)
            departments.append(department)
            
        return departments

    def _to_domain(self, model: DepartmentModel) -> Department:
        """Convert a DepartmentModel to a Department domain entity."""
        return Department(
            id=model.id,
            name=model.name,
            description=model.description
        )

    def _to_model(self, entity: Department) -> DepartmentModel:
        """Convert a Department domain entity to a DepartmentModel."""
        model = DepartmentModel(
            id=entity.id,
            name=entity.name,
            description=entity.description
        )
        return model

    def _update_model(self, model: DepartmentModel, entity: Department) -> None:
        """Update a DepartmentModel with values from a Department domain entity."""
        model.name = entity.name
        model.description = entity.description