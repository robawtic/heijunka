from abc import abstractmethod
from typing import Optional, List

from domain.entities.department import Department
from domain.repositories.interfaces.base_repository import BaseRepository


class DepartmentRepositoryInterface(BaseRepository[Department]):
    """
    Interface for department repository operations.
    """
    
    @abstractmethod
    def get_by_name(self, department_name: str) -> Optional[Department]:
        """
        Retrieve a department by its name.
        
        Args:
            department_name: The name of the department.
            
        Returns:
            The department if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_all_with_groups(self) -> List[Department]:
        """
        Retrieve all departments with their associated groups.
        
        Returns:
            A list of all departments with their groups.
        """
        pass