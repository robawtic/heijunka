from typing import Generic, TypeVar, Optional, List, Type
from sqlalchemy.orm import Session

from domain.repositories.interfaces.base_repository import BaseRepository

T = TypeVar('T')
M = TypeVar('M')  # SQLAlchemy model type


class BaseSqlAlchemyRepository(Generic[T, M], BaseRepository[T]):
    """
    Base SQLAlchemy repository implementation that provides common functionality
    for all SQLAlchemy-backed repositories.
    """
    
    def __init__(self, session: Session, model_class: Type[M], entity_class: Type[T]):
        """
        Initialize the repository with a SQLAlchemy session and model class.
        
        Args:
            session: The SQLAlchemy session to use for database operations.
            model_class: The SQLAlchemy model class.
            entity_class: The domain entity class.
        """
        self._session = session
        self._model_class = model_class
        self._entity_class = entity_class
    
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Retrieve an entity by its ID.
        
        Args:
            entity_id: The ID of the entity to retrieve.
            
        Returns:
            The entity if found, None otherwise.
        """
        model = self._session.query(self._model_class).get(entity_id)
        if model is None:
            return None
        return self._to_domain(model)
    
    def list_all(self) -> List[T]:
        """
        Retrieve all entities.
        
        Returns:
            A list of all entities.
        """
        models = self._session.query(self._model_class).all()
        return [self._to_domain(model) for model in models]
    
    def add(self, entity: T) -> T:
        """
        Add a new entity.
        
        Args:
            entity: The entity to add.
            
        Returns:
            The added entity.
        """
        model = self._to_model(entity)
        self._session.add(model)
        self._session.commit()
        return self._to_domain(model)
    
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: The entity to update.
            
        Returns:
            The updated entity.
        """
        model = self._session.query(self._model_class).get(entity.id)
        if model is None:
            raise ValueError(f"Entity with ID {entity.id} not found")
        
        self._update_model(model, entity)
        self._session.commit()
        return self._to_domain(model)
    
    def delete(self, entity_id: int) -> bool:
        """
        Delete an entity by its ID.
        
        Args:
            entity_id: The ID of the entity to delete.
            
        Returns:
            True if the entity was deleted, False otherwise.
        """
        model = self._session.query(self._model_class).get(entity_id)
        if model is None:
            return False
        
        self._session.delete(model)
        self._session.commit()
        return True
    
    def _to_domain(self, model: M) -> T:
        """
        Convert a SQLAlchemy model to a domain entity.
        
        Args:
            model: The SQLAlchemy model to convert.
            
        Returns:
            The domain entity.
        """
        raise NotImplementedError("Subclasses must implement _to_domain")
    
    def _to_model(self, entity: T) -> M:
        """
        Convert a domain entity to a SQLAlchemy model.
        
        Args:
            entity: The domain entity to convert.
            
        Returns:
            The SQLAlchemy model.
        """
        raise NotImplementedError("Subclasses must implement _to_model")
    
    def _update_model(self, model: M, entity: T) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.
        
        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        raise NotImplementedError("Subclasses must implement _update_model")