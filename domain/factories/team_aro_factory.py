from typing import Optional
from domain.contexts.assignment.entities.team_aro import TeamAro
from domain.models.TeamAroModel import AroTeamStatus

class TeamAroFactory:
    @staticmethod
    def create_team_aro(
        id: Optional[int] = None,
        employee_id: int = 0,
        team_id: int = 0,
        status: str = 'active'
    ) -> TeamAro:
        """
        Create a new TeamAro entity with basic properties.

        Args:
            id: Optional TeamAro ID (None for new entities)
            employee_id: Employee ID
            team_id: Team ID (the team the employee can ARO for)
            status: Status of the ARO relationship ('active' or 'inactive')

        Returns:
            A new TeamAro entity

        Raises:
            ValueError: If any of the parameters are invalid
        """
        # Validate inputs
        if employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if status not in ('active', 'inactive'):
            raise ValueError(f"Invalid status: {status}")

        return TeamAro(
            id=id,
            employee_id=employee_id,
            team_id=team_id,
            status=status
        )

    @staticmethod
    def create_from_model(model) -> TeamAro:
        """
        Create a TeamAro entity from a database model.

        Args:
            model: The database model to convert

        Returns:
            A new TeamAro entity populated with data from the model
        """
        return TeamAroFactory.create_team_aro(
            id=model.id,
            employee_id=model.employee_id,
            team_id=model.team_id,
            status=model.status.value if isinstance(model.status, AroTeamStatus) else model.status
        )