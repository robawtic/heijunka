# domain/factories/workstation_factory.py
from typing import Optional, List, Any
from domain.entities.workstation import Workstation

class WorkstationFactory:
    @staticmethod
    def create_workstation(
        id: Optional[int] = None,
        name: str = "",
        line_type: Optional[str] = "",
        is_loading_job: bool = False,
        is_heavy_job: bool = False,
        is_key_skill_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """
        Create a new Workstation entity with validation.

        Args:
            id: Optional workstation ID (None for new workstations)
            name: Workstation name
            line_type: Type of line (e.g., "Mainline", "Sub-Assembly")
            is_loading_job: Whether this is a loading job
            is_heavy_job: Whether this is a heavy job
            is_key_skill_job: Whether this requires a key skill
            team_id: Optional team ID the workstation belongs to

        Returns:
            A new Workstation entity

        Raises:
            ValueError: If validation fails (e.g., empty name or line_type)
        """
        # Validate inputs before creating the workstation
        if name and not isinstance(name, str):
            raise ValueError("Name must be a string")

        if line_type and not isinstance(line_type, str):
            raise ValueError("Line type must be a string")

        if team_id is not None and (not isinstance(team_id, int) or team_id <= 0):
            raise ValueError("Team ID must be a positive integer or None")

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
        line_type: Optional[str] = "",
        is_heavy_job: bool = False,
        is_key_skill_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """
        Create a workstation that is a loading job.

        Args:
            id: Optional workstation ID
            name: Workstation name
            line_type: Type of line
            is_heavy_job: Whether this is a heavy job
            is_key_skill_job: Whether this requires a key skill
            team_id: Optional team ID

        Returns:
            A new Workstation entity configured as a loading job

        Raises:
            ValueError: If validation fails
        """
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
        line_type: Optional[str] = "",
        is_loading_job: bool = True,  # Heavy jobs are typically loading jobs
        is_key_skill_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """
        Create a workstation that is a heavy job.

        Args:
            id: Optional workstation ID
            name: Workstation name
            line_type: Type of line
            is_loading_job: Whether this is a loading job (default: True)
            is_key_skill_job: Whether this requires a key skill
            team_id: Optional team ID

        Returns:
            A new Workstation entity configured as a heavy job

        Raises:
            ValueError: If validation fails
        """
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
        line_type: Optional[str] = "",
        is_loading_job: bool = False,
        is_heavy_job: bool = False,
        team_id: Optional[int] = None
    ) -> Workstation:
        """
        Create a workstation that requires a key skill.

        Args:
            id: Optional workstation ID
            name: Workstation name
            line_type: Type of line
            is_loading_job: Whether this is a loading job
            is_heavy_job: Whether this is a heavy job
            team_id: Optional team ID

        Returns:
            A new Workstation entity configured as requiring a key skill

        Raises:
            ValueError: If validation fails
        """
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
    def create_from_model(model: Any) -> Workstation:
        """
        Create a Workstation entity from a database model.

        Args:
            model: The database model to convert

        Returns:
            A new Workstation entity populated with data from the model

        Raises:
            ValueError: If validation fails
        """
        return WorkstationFactory.create_workstation(
            id=model.id,
            name=model.name,
            line_type=model.line_type.name if model.line_type else None,
            is_loading_job=model.is_loading_job,
            is_heavy_job=model.is_heavy_job,
            is_key_skill_job=model.is_key_skill_job,
            team_id=model.team_id
        )
