from contextlib import contextmanager
from typing import Optional, List, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.group import Group
from domain.models.GroupModel import GroupModel
from domain.repositories.interfaces.group_repository import GroupRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyGroupRepository(BaseSqlAlchemyRepository[Group, GroupModel], GroupRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, GroupModel, Group)

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

    def get_by_name(self, group_name: str) -> Optional[Group]:
        """Retrieve a group by its name."""
        group_model = self._session.query(GroupModel).filter(
            GroupModel.name == group_name
        ).first()
        if group_model is None:
            return None
        return self._to_domain(group_model)

    def _to_domain(self, model: GroupModel) -> Group:
        """Convert a GroupModel to a Group domain entity."""
        return Group(
            id=model.id,
            name=model.name,
            department_id=model.department_id
        )

    def _to_model(self, entity: Group) -> GroupModel:
        """Convert a Group domain entity to a GroupModel."""
        model = GroupModel(
            id=entity.id,
            name=entity.name,
            department_id=entity.department_id
        )
        return model

    def _update_model(self, model: GroupModel, entity: Group) -> None:
        """Update a GroupModel with values from a Group domain entity."""
        model.name = entity.name
        model.department_id = entity.department_id
