# domain/factories/workstation_factory.py
from typing import Optional, List
from domain.entities.workstation import Workstation

class WorkstationFactory:
    @staticmethod
    def create_workstation(
        id: Optional[int] = None,
        name: str = "",
        line_type: str = "",
        is_loading_job: bool = False,
        is_heavy_job: bool = False,
        is_key_skill_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """Create a new Workstation entity with validation."""
        # Create the workstation
        workstation = Workstation(
            id=id,
            name=name,
            line_type=line_type,
            is_loading_job=is_loading_job,
            is_heavy_job=is_heavy_job,
            is_key_skill_job=is_key_skill_job,
            team_id=team_id
        )
        
        # Validate the workstation
        workstation.validate()
        
        return workstation
    
    @staticmethod
    def create_loading_workstation(
        id: Optional[int] = None,
        name: str = "",
        line_type: str = "",
        is_heavy_job: bool = False,
        is_key_skill_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """Create a workstation that is a loading job."""
        return WorkstationFactory.create_workstation(
            id=id,
            name=name,
            line_type=line_type,
            is_loading_job=True,
            is_heavy_job=is_heavy_job,
            is_key_skill_job=is_key_skill_job,
            team_id=team_id
        )
    
    @staticmethod
    def create_heavy_workstation(
        id: Optional[int] = None,
        name: str = "",
        line_type: str = "",
        is_loading_job: bool = True,  # Heavy jobs are typically loading jobs
        is_key_skill_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """Create a workstation that is a heavy job."""
        return WorkstationFactory.create_workstation(
            id=id,
            name=name,
            line_type=line_type,
            is_loading_job=is_loading_job,
            is_heavy_job=True,
            is_key_skill_job=is_key_skill_job,
            team_id=team_id
        )
    
    @staticmethod
    def create_key_skill_workstation(
        id: Optional[int] = None,
        name: str = "",
        line_type: str = "",
        is_loading_job: bool = False,
        is_heavy_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """Create a workstation that requires a key skill."""
        return WorkstationFactory.create_workstation(
            id=id,
            name=name,
            line_type=line_type,
            is_loading_job=is_loading_job,
            is_heavy_job=is_heavy_job,
            is_key_skill_job=True,
            team_id=team_id
        )
    
    @staticmethod
    def create_from_model(model) -> Workstation:
        """Create a Workstation entity from a database model."""
        return WorkstationFactory.create_workstation(
            id=model.id,
            name=model.name,
            line_type=model.line_type.name if model.line_type else None,
            is_loading_job=model.is_loading_job,
            is_heavy_job=model.is_heavy_job,
            is_key_skill_job=model.is_key_skill_job,
            team_id=model.team_id
        )