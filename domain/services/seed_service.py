from typing import List, Optional, Dict, Any, Tuple
from domain.entities.seed_data import (
    WorkstationSeedData, EmployeeSeedData, TeamSeedData, 
    GroupSeedData, DepartmentSeedData
)
from domain.repositories.interfaces.seed_data_repository import SeedDataRepositoryInterface
from domain.repositories.interfaces.department_repository import DepartmentRepositoryInterface
from domain.repositories.interfaces.group_repository import GroupRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.contexts.user_management.repositories.interfaces.role_repository import RoleRepositoryInterface
from domain.repositories.interfaces.line_type_repository import LineTypeRepositoryInterface
from utilities.logging_factory import get_logger


class SeedService:
    """Service for seeding the database with initial data."""

    def __init__(
        self,
        seed_data_repository: SeedDataRepositoryInterface,
        department_repository: DepartmentRepositoryInterface,
        group_repository: GroupRepositoryInterface,
        team_repository: TeamRepositoryInterface,
        workstation_repository: WorkstationRepositoryInterface,
        employee_repository: EmployeeRepositoryInterface,
        role_repository: RoleRepositoryInterface,
        line_type_repository: LineTypeRepositoryInterface
    ):
        """
        Initialize the seed service.

        Args:
            seed_data_repository: Repository for loading seed data
            department_repository: Repository for departments
            group_repository: Repository for groups
            team_repository: Repository for teams
            workstation_repository: Repository for workstations
            employee_repository: Repository for employees
            role_repository: Repository for roles
            line_type_repository: Repository for line types
        """
        self.seed_data_repository = seed_data_repository
        self.department_repository = department_repository
        self.group_repository = group_repository
        self.team_repository = team_repository
        self.workstation_repository = workstation_repository
        self.employee_repository = employee_repository
        self.role_repository = role_repository
        self.line_type_repository = line_type_repository
        self.logger = get_logger("domain.services.seed_service")

    def seed_department(self, department_name: str) -> Tuple[int, int, int, int]:
        """
        Seed a department and all its groups, teams, workstations, and employees.

        Args:
            department_name: The name of the department to seed

        Returns:
            A tuple of (groups_created, teams_created, workstations_created, employees_created)
        """
        self.logger.info(
            f"Seeding department: {department_name}",
            event_type="seed_department",
            identifier=department_name
        )

        # Load department data
        department_data = self.seed_data_repository.load_department_data(department_name)

        # Create or get department
        department = self.department_repository.get_by_name(department_name)
        if not department:
            self.logger.info(
                f"Creating department: {department_name}",
                event_type="create_department",
                identifier=department_name
            )
            department = self.department_repository.create(name=department_name)

        # Seed each group in the department
        groups_created = 0
        teams_created = 0
        workstations_created = 0
        employees_created = 0

        for group_data in department_data.groups:
            group_stats = self.seed_group(group_data.name, department.id)
            groups_created += 1
            teams_created += group_stats[0]
            workstations_created += group_stats[1]
            employees_created += group_stats[2]

        self.logger.info(
            f"Seeded department {department_name}: {groups_created} groups, {teams_created} teams, "
            f"{workstations_created} workstations, {employees_created} employees",
            event_type="seed_department_complete",
            identifier=department_name,
            extra={
                "groups_created": groups_created,
                "teams_created": teams_created,
                "workstations_created": workstations_created,
                "employees_created": employees_created
            }
        )

        return groups_created, teams_created, workstations_created, employees_created

    def seed_group(self, group_name: str, department_id: int) -> Tuple[int, int, int]:
        """
        Seed a group and all its teams, workstations, and employees.

        Args:
            group_name: The name of the group to seed
            department_id: The ID of the department the group belongs to

        Returns:
            A tuple of (teams_created, workstations_created, employees_created)
        """
        self.logger.info(
            f"Seeding group: {group_name}",
            event_type="seed_group",
            identifier=group_name
        )

        # Load group data
        group_data = self.seed_data_repository.load_group_data(group_name)

        # Create or get group
        group = self.group_repository.get_by_name(group_name)
        if not group:
            self.logger.info(
                f"Creating group: {group_name}",
                event_type="create_group",
                identifier=group_name
            )
            group = self.group_repository.create(name=group_name, department_id=department_id)

        # Seed each team in the group
        teams_created = 0
        workstations_created = 0
        employees_created = 0

        for team_data in group_data.teams:
            team_stats = self.seed_team(team_data.name, group.id)
            teams_created += 1
            workstations_created += team_stats[0]
            employees_created += team_stats[1]

        self.logger.info(
            f"Seeded group {group_name}: {teams_created} teams, "
            f"{workstations_created} workstations, {employees_created} employees",
            event_type="seed_group_complete",
            identifier=group_name,
            extra={
                "teams_created": teams_created,
                "workstations_created": workstations_created,
                "employees_created": employees_created
            }
        )

        return teams_created, workstations_created, employees_created

    def seed_team(self, team_name: str, group_id: int) -> Tuple[int, int]:
        """
        Seed a team and all its workstations and employees.

        Args:
            team_name: The name of the team to seed
            group_id: The ID of the group the team belongs to

        Returns:
            A tuple of (workstations_created, employees_created)
        """
        self.logger.info(
            f"Seeding team: {team_name}",
            event_type="seed_team",
            identifier=team_name
        )

        # Load team data
        team_data = self.seed_data_repository.load_team_data(team_name)

        # Create or get team
        team = self.team_repository.get_by_name(team_name)
        if not team:
            self.logger.info(
                f"Creating team: {team_name}",
                event_type="create_team",
                identifier=team_name
            )
            team = self.team_repository.create(name=team_name, group_id=group_id)

        # Seed workstations
        workstations_created = self.seed_workstations(team_data.workstations, team.id)

        # Seed employees
        employees_created = self.seed_employees(team_data.employees, team.id)

        # Assign workstations to employees
        self.assign_workstations_to_employees(team_data.employees, team_name)

        self.logger.info(
            f"Seeded team {team_name}: {workstations_created} workstations, {employees_created} employees",
            event_type="seed_team_complete",
            identifier=team_name,
            extra={
                "workstations_created": workstations_created,
                "employees_created": employees_created
            }
        )

        return workstations_created, employees_created

    def seed_workstations(self, workstation_data_list: List[WorkstationSeedData], team_id: int) -> int:
        """
        Seed workstations for a team.

        Args:
            workstation_data_list: List of workstation seed data
            team_id: The ID of the team the workstations belong to

        Returns:
            Number of workstations created
        """
        workstations_created = 0

        # Ensure line types exist
        line_types = set(ws.line_type for ws in workstation_data_list)
        for line_type in line_types:
            if not self.line_type_repository.get_by_name(line_type):
                self.logger.info(
                    f"Creating line type: {line_type}",
                    event_type="create_line_type",
                    identifier=line_type
                )
                self.line_type_repository.create(name=line_type, description=f"{line_type} line")

        # Create or update workstations
        for ws_data in workstation_data_list:
            workstation = self.workstation_repository.get_by_name(ws_data.name)
            if not workstation:
                self.logger.info(
                    f"Creating workstation: {ws_data.name}",
                    event_type="create_workstation",
                    identifier=ws_data.name
                )

                line_type = self.line_type_repository.get_by_name(ws_data.line_type)

                workstation = self.workstation_repository.create(
                    name=ws_data.name,
                    line_type_id=line_type.id,
                    is_loading_job=ws_data.is_loading_job,
                    is_heavy_job=ws_data.is_heavy_job,
                    is_key_skill_job=ws_data.is_key_skill_job,
                    team_id=team_id
                )
                workstations_created += 1

        return workstations_created

    def seed_employees(self, employee_data_list: List[EmployeeSeedData], team_id: int) -> int:
        """
        Seed employees for a team.

        Args:
            employee_data_list: List of employee seed data
            team_id: The ID of the team the employees belong to

        Returns:
            Number of employees created
        """
        employees_created = 0

        # Ensure roles exist
        roles = set(emp.role for emp in employee_data_list)
        for role in roles:
            if not self.role_repository.get_by_name(role):
                self.logger.info(
                    f"Creating role: {role}",
                    event_type="create_role",
                    identifier=role
                )
                self.role_repository.create(name=role)

        # Create or update employees
        for emp_data in employee_data_list:
            employee = self.employee_repository.get_by_name(emp_data.name)
            if not employee:
                self.logger.info(
                    f"Creating employee: {emp_data.name}",
                    event_type="create_employee",
                    identifier=emp_data.name
                )

                employee = self.employee_repository.create(
                    name=emp_data.name,
                    team_id=team_id,
                    is_active=emp_data.is_active
                )

                # Assign roles
                role = self.role_repository.get_by_name(emp_data.role)
                self.employee_repository.assign_role(employee.id, role.id)

                # All employees are also associates
                associate_role = self.role_repository.get_by_name("Associate")
                if associate_role and associate_role.id != role.id:
                    self.employee_repository.assign_role(employee.id, associate_role.id)

                employees_created += 1

        return employees_created

    def assign_workstations_to_employees(self, employee_data_list: List[EmployeeSeedData], team_name: str) -> None:
        """
        Assign workstations to employees based on their known stations.

        Args:
            employee_data_list: List of employee seed data
            team_name: The name of the team
        """
        for emp_data in employee_data_list:
            employee = self.employee_repository.get_by_name(emp_data.name)
            if not employee:
                continue

            for station_name in emp_data.known_stations:
                workstation = self.workstation_repository.get_by_name(station_name)
                if not workstation:
                    self.logger.warning(
                        f"Workstation {station_name} not found for employee {emp_data.name}",
                        event_type="assign_workstation",
                        identifier=f"{emp_data.name}_{station_name}"
                    )
                    continue

                # Check if the employee already knows this workstation
                if self.employee_repository.knows_workstation(employee.id, workstation.id):
                    continue

                self.logger.info(
                    f"Assigning workstation {station_name} to employee {emp_data.name}",
                    event_type="assign_workstation",
                    identifier=f"{emp_data.name}_{station_name}"
                )

                self.employee_repository.assign_workstation(employee.id, workstation.id)

    def seed_all(self) -> Dict[str, int]:
        """
        Seed all available departments.

        Returns:
            A dictionary with counts of entities created
        """
        self.logger.info(
            "Seeding all departments",
            event_type="seed_all",
            identifier="all"
        )

        departments = self.seed_data_repository.get_available_departments()

        total_departments = 0
        total_groups = 0
        total_teams = 0
        total_workstations = 0
        total_employees = 0

        for department_name in departments:
            total_departments += 1
            groups, teams, workstations, employees = self.seed_department(department_name)
            total_groups += groups
            total_teams += teams
            total_workstations += workstations
            total_employees += employees

        result = {
            "departments": total_departments,
            "groups": total_groups,
            "teams": total_teams,
            "workstations": total_workstations,
            "employees": total_employees
        }

        self.logger.info(
            f"Seeded all departments: {total_departments} departments, {total_groups} groups, "
            f"{total_teams} teams, {total_workstations} workstations, {total_employees} employees",
            event_type="seed_all_complete",
            identifier="all",
            extra=result
        )

        return result
