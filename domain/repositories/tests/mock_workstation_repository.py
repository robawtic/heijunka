from typing import Optional, List

from domain.entities.workstation import Workstation
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface


class MockWorkstationRepository(WorkstationRepositoryInterface):
    """
    Mock implementation of the workstation repository for testing.
    """
    
    def __init__(self):
        self.workstations = {}  # Dictionary of workstations by ID
        
    def get_by_id(self, entity_id: int) -> Optional[Workstation]:
        """Retrieve a workstation by ID."""
        return self.workstations.get(entity_id)
    
    def list_all(self) -> List[Workstation]:
        """Retrieve all workstations."""
        return list(self.workstations.values())
    
    def add(self, entity: Workstation) -> Workstation:
        """Add a new workstation."""
        self.workstations[entity.id] = entity
        return entity
    
    def update(self, entity: Workstation) -> Workstation:
        """Update an existing workstation."""
        self.workstations[entity.id] = entity
        return entity
    
    def delete(self, entity_id: int) -> bool:
        """Delete a workstation by ID."""
        if entity_id in self.workstations:
            del self.workstations[entity_id]
            return True
        return False
    
    def get_by_team_id(self, team_id: int) -> List[Workstation]:
        """Retrieve all workstations for a specific team."""
        return [w for w in self.workstations.values() if w.id == team_id]