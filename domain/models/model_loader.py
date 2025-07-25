# model_loader.py
"""
This module provides functions for loading models from the database.
"""

def load_models(team_names, config):
    """
    Load models (employees, workstations, teams) from the database.

    Args:
        team_names: The name or names of the teams to load models for
        config: Configuration dictionary

    Returns:
        A tuple of (employees, workstations, team_objs)
    """
    from infrastructure.repositories.employee_management.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
    from infrastructure.repositories.workstation_management.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
    from infrastructure.repositories.employee_management.sqlalchemy_team_repository import SqlAlchemyTeamRepository
    from domain.models.db import Session

    session = Session()

    # Convert team_names to a list if it's a string
    if isinstance(team_names, str):
        team_names = [team_names]

    # Get repositories
    employee_repo = SqlAlchemyEmployeeRepository(session)
    workstation_repo = SqlAlchemyWorkstationRepository(session)
    team_repo = SqlAlchemyTeamRepository(session)

    # Get team IDs
    team_objs = []
    for name in team_names:
        team = team_repo.get_by_name(name)
        if team:
            team_objs.append(team)

    # Get employees and workstations for the teams
    employees = []
    workstations = []
    for team in team_objs:
        employees.extend(employee_repo.get_by_team_id(team.id))
        workstations.extend(workstation_repo.get_by_team_id(team.id))

    return employees, workstations, team_objs
