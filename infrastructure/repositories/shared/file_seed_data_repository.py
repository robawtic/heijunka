import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from domain.contexts.shared.entities.seed_data import (
    WorkstationSeedData, EmployeeSeedData, TeamSeedData, 
    GroupSeedData, DepartmentSeedData
)
from domain.repositories.interfaces.seed_data_repository import SeedDataRepositoryInterface
from utilities.logging_factory import get_logger
from utilities.secure_logging import redact_log_message


class FileSeedDataRepository(SeedDataRepositoryInterface):
    """Repository implementation that loads seed data from files."""

    def __init__(self, base_path: str = "infrastructure/seeding/seed_data"):
        """
        Initialize the repository.

        Args:
            base_path: Base path for seed data files
        """
        self.base_path = base_path
        self.logger = get_logger("domain.repositories.file_seed_data_repository")

    def _load_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load data from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            The loaded JSON data as a Python object, or None if the file doesn't exist or is invalid
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(
                redact_log_message(f"File not found: {file_path}", file_paths=[file_path]),
                event_type="file_not_found",
                identifier=file_path
            )
            return None
        except json.JSONDecodeError:
            self.logger.warning(
                redact_log_message(f"Invalid JSON in file: {file_path}", file_paths=[file_path]),
                event_type="invalid_json",
                identifier=file_path
            )
            return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse a date string into a date object.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            A date object, or None if the string is invalid
        """
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    def load_workstation_data(self, team_name: str) -> List[WorkstationSeedData]:
        """
        Load workstation seed data for a team.

        Args:
            team_name: The name of the team

        Returns:
            A list of WorkstationSeedData objects
        """
        self.logger.info(
            f"Loading workstation data for team: {team_name}",
            event_type="load_workstation_data",
            identifier=team_name
        )

        # Find the team directory
        team_dir = self._find_team_directory(team_name)
        if not team_dir:
            self.logger.warning(
                f"Team directory not found for: {team_name}",
                event_type="team_not_found",
                identifier=team_name
            )
            return []

        # Load workstations.json
        workstations_path = os.path.join(team_dir, "workstations.json")
        workstations_data = self._load_json_file(workstations_path)

        if not workstations_data or "workstations" not in workstations_data:
            self.logger.warning(
                f"No workstation data found for team: {team_name}",
                event_type="no_workstation_data",
                identifier=team_name
            )
            return []

        # Convert to WorkstationSeedData objects
        result = []
        for ws_data in workstations_data["workstations"]:
            try:
                workstation = WorkstationSeedData(
                    name=ws_data["name"],
                    line_type=ws_data["line_type"],
                    is_loading_job=ws_data["is_loading_job"],
                    is_heavy_job=ws_data["is_heavy_job"],
                    is_key_skill_job=ws_data["is_key_skill_job"],
                    description=ws_data.get("description"),
                    cycle_time_minutes=ws_data.get("cycle_time_minutes"),
                    required_tools=ws_data.get("required_tools", []),
                    safety_equipment=ws_data.get("safety_equipment", []),
                    certification_required=ws_data.get("certification_required", False),
                    training_hours_required=ws_data.get("training_hours_required"),
                    precision_requirement=ws_data.get("precision_requirement"),
                    quality_checks=ws_data.get("quality_checks", [])
                )
                result.append(workstation)
            except KeyError as e:
                self.logger.warning(
                    f"Missing required field in workstation data: {e}",
                    event_type="invalid_workstation_data",
                    identifier=f"{team_name}_{ws_data.get('name', 'unknown')}"
                )

        self.logger.info(
            f"Loaded {len(result)} workstations for team: {team_name}",
            event_type="load_workstation_data_complete",
            identifier=team_name,
            extra={"count": len(result)}
        )

        return result

    def load_employee_data(self, team_name: str) -> List[EmployeeSeedData]:
        """
        Load employee seed data for a team.

        Args:
            team_name: The name of the team

        Returns:
            A list of EmployeeSeedData objects
        """
        self.logger.info(
            f"Loading employee data for team: {team_name}",
            event_type="load_employee_data",
            identifier=team_name
        )

        # Find the team directory
        team_dir = self._find_team_directory(team_name)
        if not team_dir:
            self.logger.warning(
                f"Team directory not found for: {team_name}",
                event_type="team_not_found",
                identifier=team_name
            )
            return []

        # Load employees.json
        employees_path = os.path.join(team_dir, "employees.json")
        employees_data = self._load_json_file(employees_path)

        if not employees_data or "employees" not in employees_data:
            self.logger.warning(
                f"No employee data found for team: {team_name}",
                event_type="no_employee_data",
                identifier=team_name
            )
            return []

        # Convert to EmployeeSeedData objects
        result = []
        for emp_data in employees_data["employees"]:
            try:
                # Parse hire date if present
                hire_date = None
                if "hire_date" in emp_data:
                    hire_date = self._parse_date(emp_data["hire_date"])

                employee = EmployeeSeedData(
                    name=emp_data["name"],
                    role=emp_data["role"],
                    is_active=emp_data.get("is_active", True),
                    known_stations=emp_data.get("known_stations", []),
                    hire_date=hire_date,
                    skills=emp_data.get("skills", {}),
                    availability_pattern=emp_data.get("availability_pattern", {}),
                    is_trainer=emp_data.get("is_trainer", False),
                    certifications=emp_data.get("certifications", []),
                    training_progress=emp_data.get("training_progress", {}),
                    notes=emp_data.get("notes")
                )
                result.append(employee)
            except KeyError as e:
                self.logger.warning(
                    f"Missing required field in employee data: {e}",
                    event_type="invalid_employee_data",
                    identifier=f"{team_name}_{emp_data.get('name', 'unknown')}"
                )

        self.logger.info(
            f"Loaded {len(result)} employees for team: {team_name}",
            event_type="load_employee_data_complete",
            identifier=team_name,
            extra={"count": len(result)}
        )

        return result

    def load_team_data(self, team_name: str) -> TeamSeedData:
        """
        Load all seed data for a team.

        Args:
            team_name: The name of the team

        Returns:
            A TeamSeedData object containing workstation and employee data
        """
        self.logger.info(
            f"Loading team data for: {team_name}",
            event_type="load_team_data",
            identifier=team_name
        )

        workstations = self.load_workstation_data(team_name)
        employees = self.load_employee_data(team_name)

        team_data = TeamSeedData(
            name=team_name,
            workstations=workstations,
            employees=employees
        )

        self.logger.info(
            f"Loaded team data for {team_name}: {len(workstations)} workstations, {len(employees)} employees",
            event_type="load_team_data_complete",
            identifier=team_name,
            extra={"workstations_count": len(workstations), "employees_count": len(employees)}
        )

        return team_data

    def load_group_data(self, group_name: str) -> GroupSeedData:
        """
        Load all seed data for a group.

        Args:
            group_name: The name of the group

        Returns:
            A GroupSeedData object containing team data
        """
        self.logger.info(
            f"Loading group data for: {group_name}",
            event_type="load_group_data",
            identifier=group_name
        )

        # Get teams in this group
        teams = self.get_available_teams(group_name=group_name)

        # Load data for each team
        team_data_list = []
        for team_name in teams:
            team_data = self.load_team_data(team_name)
            team_data_list.append(team_data)

        group_data = GroupSeedData(
            name=group_name,
            teams=team_data_list
        )

        self.logger.info(
            f"Loaded group data for {group_name}: {len(team_data_list)} teams",
            event_type="load_group_data_complete",
            identifier=group_name,
            extra={"teams_count": len(team_data_list)}
        )

        return group_data

    def load_department_data(self, department_name: str) -> DepartmentSeedData:
        """
        Load all seed data for a department.

        Args:
            department_name: The name of the department

        Returns:
            A DepartmentSeedData object containing group data
        """
        self.logger.info(
            f"Loading department data for: {department_name}",
            event_type="load_department_data",
            identifier=department_name
        )

        # Get groups in this department
        groups = self.get_available_groups(department_name=department_name)

        # Load data for each group
        group_data_list = []
        for group_name in groups:
            group_data = self.load_group_data(group_name)
            group_data_list.append(group_data)

        department_data = DepartmentSeedData(
            name=department_name,
            groups=group_data_list
        )

        self.logger.info(
            f"Loaded department data for {department_name}: {len(group_data_list)} groups",
            event_type="load_department_data_complete",
            identifier=department_name,
            extra={"groups_count": len(group_data_list)}
        )

        return department_data

    def get_available_departments(self) -> List[str]:
        """
        Get a list of available department names.

        Returns:
            A list of department names
        """
        departments_dir = os.path.join(self.base_path, "departments")
        if not os.path.isdir(departments_dir):
            self.logger.warning(
                f"Departments directory not found: {departments_dir}",
                event_type="departments_dir_not_found",
                identifier=departments_dir
            )
            return []

        # Get subdirectories in the departments directory
        departments = []
        for item in os.listdir(departments_dir):
            if os.path.isdir(os.path.join(departments_dir, item)) and item != "__pycache__":
                departments.append(item)

        self.logger.info(
            f"Found {len(departments)} departments",
            event_type="get_available_departments",
            identifier="all",
            extra={"departments": departments}
        )

        return departments

    def get_available_groups(self, department_name: Optional[str] = None) -> List[str]:
        """
        Get a list of available group names.

        Args:
            department_name: Optional department name to filter by

        Returns:
            A list of group names
        """
        if department_name:
            department_dir = os.path.join(self.base_path, "departments", department_name)
            if not os.path.isdir(department_dir):
                self.logger.warning(
                    f"Department directory not found: {department_dir}",
                    event_type="department_dir_not_found",
                    identifier=department_name
                )
                return []

            groups_dir = os.path.join(department_dir, "groups")
            if not os.path.isdir(groups_dir):
                self.logger.warning(
                    f"Groups directory not found for department: {department_name}",
                    event_type="groups_dir_not_found",
                    identifier=department_name
                )
                return []

            # Get subdirectories in the groups directory
            groups = []
            for item in os.listdir(groups_dir):
                if os.path.isdir(os.path.join(groups_dir, item)) and item != "__pycache__":
                    groups.append(item)

            self.logger.info(
                f"Found {len(groups)} groups for department: {department_name}",
                event_type="get_available_groups",
                identifier=department_name,
                extra={"groups": groups}
            )

            return groups
        else:
            # Get all groups from all departments
            departments = self.get_available_departments()
            all_groups = []

            for dept in departments:
                groups = self.get_available_groups(dept)
                all_groups.extend(groups)

            self.logger.info(
                f"Found {len(all_groups)} groups across all departments",
                event_type="get_available_groups",
                identifier="all",
                extra={"groups": all_groups}
            )

            return all_groups

    def get_available_teams(self, department_name: Optional[str] = None, group_name: Optional[str] = None) -> List[str]:
        """
        Get a list of available team names.

        Args:
            department_name: Optional department name to filter by
            group_name: Optional group name to filter by

        Returns:
            A list of team names
        """
        if group_name:
            # Find the group directory
            group_dir = self._find_group_directory(group_name, department_name)
            if not group_dir:
                self.logger.warning(
                    f"Group directory not found: {group_name}",
                    event_type="group_dir_not_found",
                    identifier=group_name
                )
                return []

            teams_dir = os.path.join(group_dir, "teams")
            if not os.path.isdir(teams_dir):
                self.logger.warning(
                    f"Teams directory not found for group: {group_name}",
                    event_type="teams_dir_not_found",
                    identifier=group_name
                )
                return []

            # Get subdirectories in the teams directory
            teams = []
            for item in os.listdir(teams_dir):
                if os.path.isdir(os.path.join(teams_dir, item)) and item != "__pycache__":
                    teams.append(item)

            self.logger.info(
                f"Found {len(teams)} teams for group: {group_name}",
                event_type="get_available_teams",
                identifier=group_name,
                extra={"teams": teams}
            )

            return teams
        elif department_name:
            # Get all teams from all groups in the department
            groups = self.get_available_groups(department_name)
            all_teams = []

            for group in groups:
                teams = self.get_available_teams(department_name, group)
                all_teams.extend(teams)

            self.logger.info(
                f"Found {len(all_teams)} teams for department: {department_name}",
                event_type="get_available_teams",
                identifier=department_name,
                extra={"teams": all_teams}
            )

            return all_teams
        else:
            # Get all teams from all groups from all departments
            departments = self.get_available_departments()
            all_teams = []

            for dept in departments:
                teams = self.get_available_teams(dept)
                all_teams.extend(teams)

            self.logger.info(
                f"Found {len(all_teams)} teams across all departments",
                event_type="get_available_teams",
                identifier="all",
                extra={"teams": all_teams}
            )

            return all_teams

    def _find_team_directory(self, team_name: str) -> Optional[str]:
        """
        Find the directory for a team.

        Args:
            team_name: The name of the team

        Returns:
            The path to the team directory, or None if not found
        """
        # Search in all departments and groups
        departments = self.get_available_departments()

        for dept in departments:
            dept_dir = os.path.join(self.base_path, "departments", dept)
            groups_dir = os.path.join(dept_dir, "groups")

            if not os.path.isdir(groups_dir):
                continue

            for group in os.listdir(groups_dir):
                group_dir = os.path.join(groups_dir, group)
                teams_dir = os.path.join(group_dir, "teams")

                if not os.path.isdir(teams_dir):
                    continue

                team_dir = os.path.join(teams_dir, team_name)
                if os.path.isdir(team_dir):
                    return team_dir

        # Also check the legacy structure
        legacy_path = os.path.join(self.base_path, "groups", "shortblock", "teams", team_name)
        if os.path.isdir(legacy_path):
            return legacy_path

        return None

    def _find_group_directory(self, group_name: str, department_name: Optional[str] = None) -> Optional[str]:
        """
        Find the directory for a group.

        Args:
            group_name: The name of the group
            department_name: Optional department name to filter by

        Returns:
            The path to the group directory, or None if not found
        """
        if department_name:
            # Look in the specified department
            group_dir = os.path.join(self.base_path, "departments", department_name, "groups", group_name)
            if os.path.isdir(group_dir):
                return group_dir
        else:
            # Search in all departments
            departments = self.get_available_departments()

            for dept in departments:
                dept_dir = os.path.join(self.base_path, "departments", dept)
                groups_dir = os.path.join(dept_dir, "groups")

                if not os.path.isdir(groups_dir):
                    continue

                group_dir = os.path.join(groups_dir, group_name)
                if os.path.isdir(group_dir):
                    return group_dir

        # Also check the legacy structure
        legacy_path = os.path.join(self.base_path, "groups", group_name)
        if os.path.isdir(legacy_path):
            return legacy_path

        return None
