# domain/factories/workstation_factory.py

from typing import Optional, List, Any
from domain.contexts.workstation_management.entities.workstation import Workstation

class WorkstationFactory:
    @staticmethod
    def create_workstation(
        *,
        id: Optional[int]    = None,
        name: str            = "",
        line_type: str       = "",
        attributes: List[str]= None,
        team_id: Optional[int]= None
    ) -> Workstation:
        """
        Create a new Workstation aggregate.

        Args:
            id: Optional existing ID (None for new).
            name: Workstation name.
            line_type: One of 'mainline' or 'subline'.
            attributes: List of tags like ['loading','heavy','skill_level_2'].
            team_id: Optional team ID.

        Returns:
            A new Workstation entity.
        """
        attrs = list(attributes) if attributes else []
        # Validate core fields
        if not isinstance(name, str) or not name:
            raise ValueError("Name must be a non-empty string")
        if not isinstance(line_type, str) or not line_type:
            raise ValueError("Line type must be a non-empty string")
        if team_id is not None and (not isinstance(team_id, int) or team_id <= 0):
            raise ValueError("team_id must be a positive integer or None")

        return Workstation(
            id=id,
            name=name,
            line_type=line_type,
            team_id=team_id,
            _attributes=attrs
        )

    @staticmethod
    def create_loading_workstation(
        *,
        id: Optional[int]     = None,
        name: str             = "",
        line_type: str        = "",
        team_id: Optional[int]= None
    ) -> Workstation:
        """Convenience: a loading job station."""
        return WorkstationFactory.create_workstation(
            id=id,
            name=name,
            line_type=line_type,
            attributes=['loading'],
            team_id=team_id
        )

    @staticmethod
    def create_heavy_workstation(
        *,
        id: Optional[int]     = None,
        name: str             = "",
        line_type: str        = "",
        team_id: Optional[int]= None
    ) -> Workstation:
        """Convenience: a heavy (and loading) job station."""
        return WorkstationFactory.create_workstation(
            id=id,
            name=name,
            line_type=line_type,
            attributes=['heavy', 'loading'],
            team_id=team_id
        )

    @staticmethod
    def create_key_skill_workstation(
        *,
        id: Optional[int]     = None,
        name: str             = "",
        line_type: str        = "",
        level: int            = 3,
        team_id: Optional[int]= None
    ) -> Workstation:
        """
        Convenience: a key-skill station.
        Defaults to skill_level_3, adjust `level` as needed.
        """
        skill_tag = f"skill_level_{level}"
        return WorkstationFactory.create_workstation(
            id=id,
            name=name,
            line_type=line_type,
            attributes=[skill_tag],
            team_id=team_id
        )

    @staticmethod
    def create_from_model(model: Any) -> Workstation:
        """
        Reconstitute a Workstation entity from a SQLAlchemy model.
        Assumes your WorkstationModel.attributes is a list of attribute‐definitions.
        """
        # Extract raw attribute names
        attrs = [attr.name for attr in getattr(model, 'attributes', [])]

        # Derive line_type from attributes (fallback to blank)
        if 'mainline' in attrs:
            lt = 'mainline'
        elif 'subline' in attrs:
            lt = 'subline'
        else:
            lt = ''

        return WorkstationFactory.create_workstation(
            id=model.id,
            name=model.name,
            line_type=lt,
            attributes=attrs,
            team_id=model.team_id
        )
