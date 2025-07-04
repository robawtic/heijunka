from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from application.commands.seed_database_command import SeedDatabaseCommand
from domain.services.seed_service import SeedService
from domain.repositories.interfaces.seed_data_repository import SeedDataRepositoryInterface
from domain.repositories.interfaces.department_repository import DepartmentRepositoryInterface
from domain.repositories.interfaces.group_repository import GroupRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.contexts.user_management.repositories.interfaces.role_repository import RoleRepositoryInterface
from domain.repositories.interfaces.line_type_repository import LineTypeRepositoryInterface
from domain.models.Base import Base
from domain.models.db import engine
from utilities.logging_factory import get_logger


class SeedDatabaseHandler:
    """Handler for the SeedDatabaseCommand."""

    def __init__(
        self,
        seed_data_repository: SeedDataRepositoryInterface,
        department_repository: DepartmentRepositoryInterface,
        group_repository: GroupRepositoryInterface,
        team_repository: TeamRepositoryInterface,
        workstation_repository: WorkstationRepositoryInterface,
        employee_repository: EmployeeRepositoryInterface,
        role_repository: RoleRepositoryInterface,
        line_type_repository: LineTypeRepositoryInterface,
        session: Session
    ):
        """
        Initialize the handler.

        Args:
            seed_data_repository: Repository for loading seed data
            department_repository: Repository for departments
            group_repository: Repository for groups
            team_repository: Repository for teams
            workstation_repository: Repository for workstations
            employee_repository: Repository for employees
            role_repository: Repository for roles
            line_type_repository: Repository for line types
            session: Database session
        """
        self.seed_data_repository = seed_data_repository
        self.department_repository = department_repository
        self.group_repository = group_repository
        self.team_repository = team_repository
        self.workstation_repository = workstation_repository
        self.employee_repository = employee_repository
        self.role_repository = role_repository
        self.line_type_repository = line_type_repository
        self.session = session
        self.logger = get_logger("application.commands.seed_database_handler")

    def handle(self, command: SeedDatabaseCommand) -> Dict[str, Any]:
        """
        Handle the SeedDatabaseCommand.

        Args:
            command: The command to handle

        Returns:
            A dictionary with the results of the seeding operation
        """
        self.logger.info(
            f"Handling SeedDatabaseCommand: department={command.department}, group={command.group}, "
            f"team={command.team}, reset_database={command.reset_database}",
            event_type="seed_database",
            identifier="start",
            extra={
                "department": command.department,
                "group": command.group,
                "team": command.team,
                "reset_database": command.reset_database
            }
        )

        # Reset database if requested
        if command.reset_database:
            self._reset_database()

        # Create seed service
        seed_service = SeedService(
            seed_data_repository=self.seed_data_repository,
            department_repository=self.department_repository,
            group_repository=self.group_repository,
            team_repository=self.team_repository,
            workstation_repository=self.workstation_repository,
            employee_repository=self.employee_repository,
            role_repository=self.role_repository,
            line_type_repository=self.line_type_repository
        )

        # Seed based on command parameters
        result = {}

        try:
            if command.team:
                # Seed a specific team
                self.logger.info(
                    f"Seeding team: {command.team}",
                    event_type="seed_team",
                    identifier=command.team
                )

                # Get the group for this team
                group_id = self._get_group_id_for_team(command.team)
                if not group_id:
                    error_msg = f"Could not find group for team: {command.team}"
                    self.logger.error(
                        error_msg,
                        event_type="seed_team",
                        identifier=command.team
                    )
                    return {"status": "error", "message": error_msg}

                # Seed the team
                workstations_created, employees_created = seed_service.seed_team(command.team, group_id)

                result = {
                    "status": "success",
                    "teams_created": 1,
                    "workstations_created": workstations_created,
                    "employees_created": employees_created
                }

                self.logger.info(
                    f"Seeded team {command.team}: {workstations_created} workstations, {employees_created} employees",
                    event_type="seed_team_complete",
                    identifier=command.team,
                    extra=result
                )
            elif command.group:
                # Seed a specific group
                self.logger.info(
                    f"Seeding group: {command.group}",
                    event_type="seed_group",
                    identifier=command.group
                )

                # Get the department for this group
                department_id = self._get_department_id_for_group(command.group)
                if not department_id:
                    error_msg = f"Could not find department for group: {command.group}"
                    self.logger.error(
                        error_msg,
                        event_type="seed_group",
                        identifier=command.group
                    )
                    return {"status": "error", "message": error_msg}

                # Seed the group
                teams_created, workstations_created, employees_created = seed_service.seed_group(command.group, department_id)

                result = {
                    "status": "success",
                    "groups_created": 1,
                    "teams_created": teams_created,
                    "workstations_created": workstations_created,
                    "employees_created": employees_created
                }

                self.logger.info(
                    f"Seeded group {command.group}: {teams_created} teams, "
                    f"{workstations_created} workstations, {employees_created} employees",
                    event_type="seed_group_complete",
                    identifier=command.group,
                    extra=result
                )
            elif command.department:
                # Seed a specific department
                self.logger.info(
                    f"Seeding department: {command.department}",
                    event_type="seed_department",
                    identifier=command.department
                )

                # Seed the department
                groups_created, teams_created, workstations_created, employees_created = seed_service.seed_department(command.department)

                result = {
                    "status": "success",
                    "departments_created": 1,
                    "groups_created": groups_created,
                    "teams_created": teams_created,
                    "workstations_created": workstations_created,
                    "employees_created": employees_created
                }

                self.logger.info(
                    f"Seeded department {command.department}: {groups_created} groups, {teams_created} teams, "
                    f"{workstations_created} workstations, {employees_created} employees",
                    event_type="seed_department_complete",
                    identifier=command.department,
                    extra=result
                )
            else:
                # Seed all departments
                self.logger.info(
                    "Seeding all departments",
                    event_type="seed_all",
                    identifier="all"
                )

                # Seed all departments
                result = seed_service.seed_all()
                result["status"] = "success"

                self.logger.info(
                    f"Seeded all departments: {result['departments']} departments, {result['groups']} groups, "
                    f"{result['teams']} teams, {result['workstations']} workstations, {result['employees']} employees",
                    event_type="seed_all_complete",
                    identifier="all",
                    extra=result
                )

            # Commit the session
            self.session.commit()

            return result
        except Exception as e:
            # Rollback the session on error
            self.session.rollback()

            error_msg = f"Error seeding database: {str(e)}"
            self.logger.error(
                error_msg,
                event_type="seed_database",
                identifier="error",
                extra={"exception": str(e)}
            )

            return {"status": "error", "message": error_msg}

    def _reset_database(self) -> None:
        """Reset the database by dropping and recreating all tables."""
        self.logger.info(
            "Resetting database",
            event_type="reset_database",
            identifier="start"
        )

        try:
            # Drop all tables
            Base.metadata.drop_all(engine)

            # Create all tables
            Base.metadata.create_all(engine)

            self.logger.info(
                "Database reset complete",
                event_type="reset_database",
                identifier="complete"
            )
        except Exception as e:
            error_msg = f"Error resetting database: {str(e)}"
            self.logger.error(
                error_msg,
                event_type="reset_database",
                identifier="error",
                extra={"exception": str(e)}
            )
            raise

    def _get_group_id_for_team(self, team_name: str) -> Optional[int]:
        """
        Get the group ID for a team.

        Args:
            team_name: The name of the team

        Returns:
            The group ID, or None if not found
        """
        team = self.team_repository.get_by_name(team_name)
        if team:
            return team.group_id

        # If team doesn't exist, try to find the group from the seed data
        teams = self.seed_data_repository.get_available_teams()
        if team_name not in teams:
            return None

        # Find the group that contains this team
        departments = self.seed_data_repository.get_available_departments()
        for dept in departments:
            groups = self.seed_data_repository.get_available_groups(dept)
            for group in groups:
                group_teams = self.seed_data_repository.get_available_teams(dept, group)
                if team_name in group_teams:
                    # Create the department if it doesn't exist
                    department = self.department_repository.get_by_name(dept)
                    if not department:
                        department = self.department_repository.create(name=dept)

                    # Create the group if it doesn't exist
                    group_obj = self.group_repository.get_by_name(group)
                    if not group_obj:
                        group_obj = self.group_repository.create(name=group, department_id=department.id)

                    return group_obj.id

        return None

    def _get_department_id_for_group(self, group_name: str) -> Optional[int]:
        """
        Get the department ID for a group.

        Args:
            group_name: The name of the group

        Returns:
            The department ID, or None if not found
        """
        group = self.group_repository.get_by_name(group_name)
        if group:
            return group.department_id

        # If group doesn't exist, try to find the department from the seed data
        groups = self.seed_data_repository.get_available_groups()
        if group_name not in groups:
            return None

        # Find the department that contains this group
        departments = self.seed_data_repository.get_available_departments()
        for dept in departments:
            dept_groups = self.seed_data_repository.get_available_groups(dept)
            if group_name in dept_groups:
                # Create the department if it doesn't exist
                department = self.department_repository.get_by_name(dept)
                if not department:
                    department = self.department_repository.create(name=dept)

                return department.id

        return None
