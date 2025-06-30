# infrastructure/scheduling/schedule_data_service.py
from typing import List, Dict, Set, Any, Optional, Tuple
from datetime import date
import logging
from sqlalchemy.orm import Session

from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.aro_assignment_repository import AROAssignmentRepositoryInterface
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.entities.team import Team
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("infrastructure.scheduling.schedule_data_service", rate_limit=True)


class ScheduleDataService:
    """
    Service responsible for prefetching and organizing data needed for schedule generation.

    This service handles all data access operations required for schedule generation,
    optimizing database queries and providing structured data to the application layer.
    """

    def __init__(
            self,
            employee_repository: EmployeeRepositoryInterface,
            workstation_repository: WorkstationRepositoryInterface,
            team_repository: TeamRepositoryInterface,
            aro_repository: AROAssignmentRepositoryInterface,
            session_factory=None,
            work_history_repository=None
    ):
        """
        Initialize the ScheduleDataService with required repositories.

        Args:
            employee_repository: Repository for employee data
            workstation_repository: Repository for workstation data
            team_repository: Repository for team data
            aro_repository: Repository for ARO assignment data
            session_factory: Factory function to create database sessions
            work_history_repository: Repository for work history data (optional)
        """
        self.employee_repository = employee_repository
        self.workstation_repository = workstation_repository
        self.team_repository = team_repository
        self.aro_repository = aro_repository
        self.session_factory = session_factory
        self.work_history_repository = work_history_repository

    def prefetch_for_teams(
            self,
            team_ids: List[int],
            start_date: date,
            periods: int
    ) -> Dict[str, Any]:
        """
        Prefetch all data needed for schedule generation for multiple teams.

        Args:
            team_ids: List of team IDs to prefetch data for
            start_date: The date to generate schedules for
            periods: Number of periods per day

        Returns:
            Dictionary containing all prefetched data
        """
        logger.info(
            f"Prefetching data for {len(team_ids)} teams",
            event_type="bulk_data_fetch",
            identifier="start"
        )

        # Batch fetch all employees and workstations
        all_employees = self.employee_repository.get_by_team_ids(team_ids)
        all_workstations = self.workstation_repository.get_by_team_ids(team_ids)

        # Create lookup dictionaries for employees and workstations
        employees_by_team = {}
        workstations_by_team = {}
        employees_by_id = {}

        for employee in all_employees:
            # Add to employees_by_team
            if employee.team_id not in employees_by_team:
                employees_by_team[employee.team_id] = []
            employees_by_team[employee.team_id].append(employee)

            # Add to employees_by_id
            employees_by_id[employee.id] = employee

        for workstation in all_workstations:
            if workstation.team_id not in workstations_by_team:
                workstations_by_team[workstation.team_id] = []
            workstations_by_team[workstation.team_id].append(workstation)

        # Prefetch teams, groups, and departments
        logger.info(
            "Prefetching teams, groups, and departments",
            event_type="bulk_data_fetch",
            identifier="teams_groups"
        )

        # Get all teams
        teams = [self.team_repository.get(team_id) for team_id in team_ids]
        teams = [team for team in teams if team]  # Filter out None values

        # Create lookup dictionaries for teams
        teams_by_id = {team.id: team for team in teams}
        teams_by_name = {team.name: team for team in teams}

        # Prefetch groups for all teams
        groups_by_team = {}
        for team_id in team_ids:
            group = self.team_repository.get_group(team_id)
            if group:
                groups_by_team[team_id] = group

        # Prefetch departments for all groups
        departments_by_group = {}
        teams_by_department = {}
        for group in groups_by_team.values():
            if hasattr(group, 'department_id'):
                department = self.team_repository.get_department(group.department_id)
                if department:
                    departments_by_group[group.id] = department

                    # Create teams_by_department lookup
                    if department.id not in teams_by_department:
                        teams_by_department[department.id] = []
                    for team in teams:
                        team_group = groups_by_team.get(team.id)
                        if team_group and hasattr(team_group,
                                                  'department_id') and team_group.department_id == department.id:
                            teams_by_department[department.id].append(team)

        # Prefetch ARO assignments for the date
        logger.info(
            f"Prefetching ARO assignments for date {start_date}",
            event_type="bulk_data_fetch",
            identifier="aro_assignments"
        )

        # Prefetch ARO assignments for each period
        aro_assignments_by_team = {}
        aro_assignments_by_team_period = {}

        for team_id in team_ids:
            # Get employees leaving as AROs (full day)
            aro_out_ids = self.aro_repository.get_employees_leaving(team_id, start_date)
            # Get employees joining as AROs (full day)
            aro_in_ids = self.aro_repository.get_employees_joining(team_id, start_date)

            # Store full-day assignments
            aro_assignments_by_team[team_id] = {
                'out': aro_out_ids,
                'in': aro_in_ids
            }

            # Initialize period-specific assignments
            aro_assignments_by_team_period[team_id] = {}

            # Get period-specific assignments for each period
            for period in range(1, periods + 1):
                try:
                    # Get employees leaving as AROs for this period
                    period_out_ids = self.aro_repository.get_employees_leaving(team_id, start_date, period)
                    # Get employees joining as AROs for this period
                    period_in_ids = self.aro_repository.get_employees_joining(team_id, start_date, period)

                    aro_assignments_by_team_period[team_id][period] = {
                        'out': period_out_ids,
                        'in': period_in_ids
                    }
                except Exception as e:
                    logger.error(
                        f"Error prefetching period-specific ARO assignments for team {team_id}, period {period}: {str(e)}",
                        event_type="bulk_data_fetch",
                        identifier="aro_assignments_error"
                    )
                    # Use empty lists as fallback
                    aro_assignments_by_team_period[team_id][period] = {
                        'out': [],
                        'in': []
                    }

        # Prefetch all ARO assignments by employee
        aro_assignments_by_employee = {}

        # Collect all employee IDs that need ARO assignments
        all_aro_employee_ids = set()

        # Add employees from full-day assignments
        for team_id, assignments in aro_assignments_by_team.items():
            for employee_id in assignments['in']:
                all_aro_employee_ids.add(employee_id)
            for employee_id in assignments['out']:
                all_aro_employee_ids.add(employee_id)

        # Add employees from period-specific assignments
        for team_id, periods_dict in aro_assignments_by_team_period.items():
            for period, assignments in periods_dict.items():
                for employee_id in assignments['in']:
                    all_aro_employee_ids.add(employee_id)
                for employee_id in assignments['out']:
                    all_aro_employee_ids.add(employee_id)

        # Fetch ARO assignments for all collected employee IDs
        for employee_id in all_aro_employee_ids:
            try:
                aro_assignments = self.aro_repository.get_by_employee_id(employee_id, start_date)
                aro_assignments_by_employee[employee_id] = aro_assignments
            except Exception as e:
                logger.error(
                    f"Error prefetching ARO assignments for employee {employee_id}: {str(e)}",
                    event_type="bulk_data_fetch",
                    identifier="aro_assignments_error"
                )
                # Use empty list as fallback
                aro_assignments_by_employee[employee_id] = []

        logger.info(
            f"Prefetched {len(all_employees)} employees, {len(all_workstations)} workstations, {len(teams)} teams, {len(groups_by_team)} groups, and ARO assignments for {len(team_ids)} teams",
            event_type="bulk_data_fetch",
            identifier="complete"
        )

        # Fetch work history data if repository is available
        work_history_data = {}
        if self.work_history_repository:
            try:
                logger.info(
                    "Prefetching work history data",
                    event_type="bulk_data_fetch",
                    identifier="work_history"
                )
                # Get all employee IDs
                employee_ids = [employee.id for employee in all_employees]

                # Fetch work history for these employees
                # We need to fetch work history for each employee individually since get_filtered doesn't support multiple employee IDs
                entries = []
                for employee_id in employee_ids:
                    # Get work history entries for this employee on or before the start date
                    employee_entries, _ = self.work_history_repository.get_filtered(
                        employee_id=employee_id,
                        end_date=start_date  # Include entries up to and including start_date
                    )
                    entries.extend(employee_entries)

                # Organize by employee ID
                for entry in entries:
                    if entry.employee_id not in work_history_data:
                        work_history_data[entry.employee_id] = []
                    work_history_data[entry.employee_id].append(entry)

                logger.info(
                    f"Prefetched work history data for {len(work_history_data)} employees",
                    event_type="bulk_data_fetch",
                    identifier="work_history"
                )
            except Exception as e:
                logger.error(
                    f"Error prefetching work history data: {str(e)}",
                    event_type="bulk_data_fetch",
                    identifier="work_history_error"
                )
                # Use empty dictionary as fallback
                work_history_data = {}

        # Create a shared prefetched data dictionary
        prefetched_data = {
            'teams_by_name': teams_by_name,
            'teams_by_id': teams_by_id,
            'groups_by_team': groups_by_team,
            'departments_by_group': departments_by_group,
            'teams_by_department': teams_by_department,
            'aro_assignments_by_team': aro_assignments_by_team,
            'aro_assignments_by_team_period': aro_assignments_by_team_period,
            'aro_assignments_by_employee': aro_assignments_by_employee,
            'employees_by_id': employees_by_id,
            'employees_by_team': employees_by_team,
            'workstations_by_team': workstations_by_team,
            'periods_per_day': periods,
            'work_history_data': work_history_data
        }

        return prefetched_data

    def process_availability(
            self,
            team_ids: List[int],
            prefetched_data: Dict[str, Any],
            call_ins: Optional[List[str]] = None,
            periods: Optional[int] = None
    ) -> Dict[int, Dict[int, Set[int]]]:
        """
        Process employee availability based on team leaders, call-ins, and ARO assignments.

        Args:
            team_ids: List of team IDs to process availability for
            prefetched_data: Dictionary containing prefetched data
            call_ins: List of employee names who are called in (unavailable)
            periods: Number of periods per day (if None, uses the value from prefetched_data)

        Returns:
            Dictionary mapping team_id -> period -> set of available employee IDs
        """
        # Use periods from prefetched_data if not provided
        if periods is None:
            periods = prefetched_data.get('periods_per_day', 4)
        employees_by_team = prefetched_data['employees_by_team']
        employees_by_id = prefetched_data['employees_by_id']
        aro_assignments_by_team = prefetched_data['aro_assignments_by_team']
        aro_assignments_by_team_period = prefetched_data['aro_assignments_by_team_period']

        # Build initial available_by_team_and_period
        available_by_team_and_period = {}
        for team_id in team_ids:
            available_by_team_and_period[team_id] = {}
            for period in range(1, periods + 1):
                # Start with all employees for the team
                available_by_team_and_period[team_id][period] = set(
                    emp.id for emp in employees_by_team.get(team_id, [])
                )

        # Filter out team leaders from every roster & period
        for team_id in team_ids:
            team_leaders = [emp.id for emp in employees_by_team.get(team_id, [])
                            if emp.has_role("Team Lead")]
            if team_leaders:
                logger.info(
                    f"Filtering out {len(team_leaders)} team leaders from team {team_id}",
                    event_type="filter_team_leaders",
                    identifier=f"team_{team_id}"
                )
                for period in range(1, periods + 1):
                    for leader_id in team_leaders:
                        available_by_team_and_period[team_id][period].discard(leader_id)

        # Remove any call-ins from every roster & period
        if call_ins:
            for call_in in call_ins:
                # Find employee ID by name
                emp_id = None
                for emp_id, emp in employees_by_id.items():
                    if emp.name == call_in:
                        emp_id = emp.id
                        break

                if emp_id:
                    for t_id in team_ids:
                        for p in range(1, periods + 1):
                            available_by_team_and_period[t_id][p].discard(emp_id)
                else:
                    logger.warning(f"Call-in employee '{call_in}' not found in any team")

        # Process ARO assignments that are already in the system
        for team_id in team_ids:
            # Process full-day ARO assignments
            if team_id in aro_assignments_by_team:
                aro_data = aro_assignments_by_team[team_id]

                # Remove employees leaving as AROs from all periods
                for emp_id in aro_data.get('out', []):
                    for period in range(1, periods + 1):
                        available_by_team_and_period[team_id][period].discard(emp_id)

                # Add employees joining as AROs to all periods
                for emp_id in aro_data.get('in', []):
                    for period in range(1, periods + 1):
                        available_by_team_and_period[team_id][period].add(emp_id)

            # Process period-specific ARO assignments
            if team_id in aro_assignments_by_team_period:
                for period, period_data in aro_assignments_by_team_period[team_id].items():
                    # Remove employees leaving as AROs for this period
                    for emp_id in period_data.get('out', []):
                        available_by_team_and_period[team_id][period].discard(emp_id)

                    # Add employees joining as AROs for this period
                    for emp_id in period_data.get('in', []):
                        available_by_team_and_period[team_id][period].add(emp_id)

        return available_by_team_and_period

    def extract_team_data(
            self,
            prefetched_data: Dict[str, Any],
            team_id: int,
            period: Optional[int] = None,
            available_by_team_and_period: Optional[Dict[int, Dict[int, Set[int]]]] = None
    ) -> Dict[str, Any]:
        """
        Extract data for a specific team from the prefetched data.

        Args:
            prefetched_data: Dictionary containing all prefetched data
            team_id: ID of the team to extract data for
            period: Optional period to filter employees by availability
                   (if None, all employees for the team are included)
            available_by_team_and_period: Optional dictionary of available employees by team and period
                                         (required if period is specified)

        Returns:
            Dictionary containing team-specific data
        """
        employees_by_id = prefetched_data['employees_by_id']
        workstations_by_team = prefetched_data['workstations_by_team']

        # Get workstations for this team
        workstations = workstations_by_team.get(team_id, [])

        # Get employees for this team
        if period is not None and available_by_team_and_period is not None:
            # Get available employees for this period
            available_ids = available_by_team_and_period.get(team_id, {}).get(period, set())
            employees = [employees_by_id[emp_id] for emp_id in available_ids if emp_id in employees_by_id]
        else:
            # Get all employees for this team
            employees = prefetched_data['employees_by_team'].get(team_id, [])

        # Create team-specific data dictionary
        team_data = {
            'employees': employees,
            'workstations': workstations,
            'team': prefetched_data['teams_by_id'].get(team_id),
            'aro_data': prefetched_data['aro_assignments_by_employee']
        }

        return team_data
