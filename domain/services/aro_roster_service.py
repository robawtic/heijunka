# domain/services/aro_roster_service.py
from typing import List, Dict, Set, Optional, Any
from datetime import date
import logging

from domain.contexts.employee_management.entities.employee import Employee

# Logger for this module
logger = logging.getLogger(__name__)

class ARORosterService:
    def __init__(self, aro_assignment_repository=None, team_repository=None):
        self.aro_assignment_repository = aro_assignment_repository
        self.team_repository = team_repository

    def handle_aro_assignments(self, employees: List[Employee], team_id: int,
                              start_date: date, prefetched_data: Optional[Dict] = None) -> List[Employee]:
        """
        Handle ARO (Auxiliary  Relief Operator) assignments by:
        1. Removing employees leaving the team
        2. Adding employees joining the team

        Args:
            employees: List of employees to filter
            team_id: ID of the team
            start_date: Start date of the schedule
            prefetched_data: Optional dictionary containing prefetched data

        Returns:
            List of available employees after ARO processing
        """
        # If no employees, return empty list
        if not employees:
            logger.warning(f"No employees provided for team {team_id}, skipping ARO processing")
            return []

        # If prefetched ARO data is available, use it
        if prefetched_data and prefetched_data.get('aro_assignments_by_team') and team_id in prefetched_data.get('aro_assignments_by_team', {}):
            try:
                logger.debug(f"Using prefetched ARO data for team {team_id}")

                # Initialize available employees with a copy of the original list
                available_employees = employees.copy()

                # Track which employees were processed for validation
                processed_employees = set()

                # Process full-day ARO assignments
                self.process_full_day_aro_assignments(
                    team_id, 
                    available_employees, 
                    prefetched_data, 
                    processed_employees
                )

                # Process period-specific ARO assignments if available
                if (prefetched_data.get('aro_assignments_by_team_period') and 
                    team_id in prefetched_data.get('aro_assignments_by_team_period', {}) and
                    prefetched_data.get('periods_per_day')):

                    self.process_period_specific_aro_assignments(
                        team_id, 
                        available_employees, 
                        prefetched_data, 
                        processed_employees
                    )

                # Validate ARO assignments
                if not available_employees:
                    logger.warning(
                        f"No available employees after ARO processing for team {team_id}. "
                        f"This may indicate an issue with ARO assignments."
                    )

                logger.info(
                    f"Processed ARO assignments for team {team_id}: "
                    f"{len(processed_employees)} employees processed, "
                    f"{len(available_employees)} employees available"
                )

                return available_employees

            except Exception as e:
                logger.error(
                    f"Error processing prefetched ARO assignments for team {team_id}: {str(e)}. "
                    f"Falling back to non-prefetched path."
                )
                # Fall through to non-prefetched path

        # If no prefetched data or ARO repository, return original employees
        if not self.aro_assignment_repository:
            logger.debug("No ARO assignment repository provided, skipping ARO processing")
            return employees.copy()

        # Get employees leaving as AROs
        aro_out_ids = []
        try:
            aro_out_ids = self.aro_assignment_repository.get_employees_leaving(team_id, start_date)
            if aro_out_ids:
                logger.info(f"Found {len(aro_out_ids)} employees leaving team {team_id} as AROs")
        except Exception as e:
            logger.error(f"Error getting employees leaving as AROs: {str(e)}")

        # Get employees joining as AROs
        aro_in_ids = []
        try:
            aro_in_ids = self.aro_assignment_repository.get_employees_joining(team_id, start_date)
            if aro_in_ids:
                logger.info(f"Found {len(aro_in_ids)} employees joining team {team_id} as AROs")
        except Exception as e:
            logger.error(f"Error getting employees joining as AROs: {str(e)}")

        # Filter out employees leaving as AROs
        available_employees = [e for e in employees if e.id not in aro_out_ids]

        # Add employees joining as AROs
        if aro_in_ids and self.team_repository:
            processed_employees = set()
            self.add_aro_employees(aro_in_ids, available_employees, {}, processed_employees)

        # Validate ARO assignments
        if not available_employees:
            logger.warning(
                f"No available employees after ARO processing for team {team_id}. "
                f"This may indicate an issue with ARO assignments."
            )

        return available_employees

    def process_full_day_aro_assignments(
        self, 
        team_id: int, 
        available_employees: List[Employee], 
        prefetched_data: Dict, 
        processed_employees: Set[int]
    ) -> None:
        """
        Process full-day ARO assignments for a team.

        Args:
            team_id: ID of the team
            available_employees: List of available employees to modify
            prefetched_data: Dictionary containing prefetched data
            processed_employees: Set to track which employees were processed
        """
        # Safely get ARO data
        if 'aro_assignments_by_team' not in prefetched_data or team_id not in prefetched_data['aro_assignments_by_team']:
            logger.warning(f"No ARO data found for team {team_id} in prefetched data")
            return

        aro_data = prefetched_data['aro_assignments_by_team'][team_id]

        # Get employees leaving as AROs from prefetched data
        aro_out_ids = aro_data.get('out', [])
        if aro_out_ids:
            logger.info(f"Found {len(aro_out_ids)} employees leaving team {team_id} as AROs (from prefetched data)")

            # Filter out employees leaving as AROs
            available_employees[:] = [e for e in available_employees if e.id not in aro_out_ids]

            # Add to processed employees
            processed_employees.update(aro_out_ids)

        # Get employees joining as AROs from prefetched data
        aro_in_ids = aro_data.get('in', [])
        if aro_in_ids:
            logger.info(f"Found {len(aro_in_ids)} employees joining team {team_id} as AROs (from prefetched data)")

            # Add employees joining as AROs
            self.add_aro_employees(aro_in_ids, available_employees, prefetched_data, processed_employees)

    def process_period_specific_aro_assignments(
        self, 
        team_id: int, 
        available_employees: List[Employee], 
        prefetched_data: Dict, 
        processed_employees: Set[int]
    ) -> None:
        """
        Process period-specific ARO assignments for a team.

        Args:
            team_id: ID of the team
            available_employees: List of available employees to modify
            prefetched_data: Dictionary containing prefetched data
            processed_employees: Set to track which employees were processed
        """
        # Safely get period-specific ARO data
        if 'aro_assignments_by_team_period' not in prefetched_data or team_id not in prefetched_data['aro_assignments_by_team_period']:
            logger.warning(f"No period-specific ARO data found for team {team_id} in prefetched data")
            return

        if 'periods_per_day' not in prefetched_data:
            logger.warning(f"No periods_per_day found in prefetched data")
            return

        periods_data = prefetched_data['aro_assignments_by_team_period'][team_id]
        periods_per_day = prefetched_data['periods_per_day']

        for period in range(1, periods_per_day + 1):
            if period not in periods_data:
                continue

            period_data = periods_data[period]

            # Get employees leaving as AROs for this period
            period_out_ids = period_data.get('out', [])
            if period_out_ids:
                logger.info(f"Found {len(period_out_ids)} employees leaving team {team_id} as AROs for period {period} (from prefetched data)")

                # Filter out employees leaving as AROs for this period
                # Note: For period-specific assignments, we don't remove the employee entirely,
                # but this information would be used during the actual scheduling
                processed_employees.update(period_out_ids)

            # Get employees joining as AROs for this period
            period_in_ids = period_data.get('in', [])
            if period_in_ids:
                logger.info(f"Found {len(period_in_ids)} employees joining team {team_id} as AROs for period {period} (from prefetched data)")

                # Add employees joining as AROs for this period
                self.add_aro_employees(period_in_ids, available_employees, prefetched_data, processed_employees)

    def add_aro_employees(
        self, 
        aro_ids: List[int], 
        available_employees: List[Employee], 
        prefetched_data: Dict,
        processed_employees: Set[int]
    ) -> None:
        """
        Add ARO employees to the list of available employees.

        Args:
            aro_ids: List of ARO employee IDs to add
            available_employees: List of available employees to modify
            prefetched_data: Dictionary containing prefetched data
            processed_employees: Set to track which employees were processed
        """
        # Track existing employee IDs to avoid duplicates
        existing_employee_ids = {e.id for e in available_employees}

        for aro_id in aro_ids:
            # Skip if already processed
            if aro_id in processed_employees:
                continue

            try:
                # First try to get employee from prefetched employees_by_id
                if prefetched_data.get('employees_by_id') and aro_id in prefetched_data.get('employees_by_id', {}):
                    emp = prefetched_data['employees_by_id'][aro_id]

                    # Add only if not already in the list
                    if emp.id not in existing_employee_ids:
                        available_employees.append(emp)
                        existing_employee_ids.add(emp.id)
                        logger.debug(f"Added ARO employee {emp.name} (ID: {emp.id}) from prefetched data")

                # If not found, try to get from ARO assignments and team repository
                elif prefetched_data.get('aro_assignments_by_employee') and aro_id in prefetched_data.get('aro_assignments_by_employee', {}):
                    aro_assignments = prefetched_data['aro_assignments_by_employee'][aro_id]

                    if aro_assignments and aro_id not in existing_employee_ids:
                        assignment = aro_assignments[0]  # Take the first assignment if multiple exist

                        # Try to get the team from prefetched data first
                        from_team = None
                        if prefetched_data.get('teams_by_id') and assignment.from_team_id in prefetched_data.get('teams_by_id', {}):
                            from_team = prefetched_data['teams_by_id'][assignment.from_team_id]
                        elif self.team_repository:
                            from_team = self.team_repository.get(assignment.from_team_id)

                        if from_team and hasattr(from_team, 'members'):
                            for emp in from_team.members:
                                if emp.id == aro_id and emp.id not in existing_employee_ids:
                                    available_employees.append(emp)
                                    existing_employee_ids.add(emp.id)
                                    logger.debug(f"Added ARO employee {emp.name} (ID: {emp.id}) from team {from_team.name}")
                                    break

                # If not found in prefetched data but we have a team repository, try to find the employee
                elif self.team_repository and self.aro_assignment_repository:
                    # Get the ARO assignment to find the from_team_id
                    aro_assignments = self.aro_assignment_repository.get_by_employee_id(aro_id, None)  # No date filter
                    if aro_assignments:
                        assignment = aro_assignments[0]  # Take the first assignment if multiple exist
                        from_team = self.team_repository.get(assignment.from_team_id)
                        if from_team and hasattr(from_team, 'members'):
                            for emp in from_team.members:
                                if emp.id == aro_id and emp.id not in existing_employee_ids:
                                    available_employees.append(emp)
                                    existing_employee_ids.add(emp.id)
                                    logger.debug(f"Added ARO employee {emp.name} (ID: {emp.id}) from team {from_team.name}")
                                    break

                # Mark as processed
                processed_employees.add(aro_id)

            except Exception as e:
                logger.error(f"Error adding ARO employee {aro_id}: {str(e)}")

    def handle_understaffed_teams(self, available_by_team_and_period: Dict, 
                                 teams: List[Any], period: int, 
                                 prefetched_data: Dict) -> Set[int]:
        """
        Handle understaffed teams by assigning AROs.

        This method identifies teams that are understaffed for a specific period
        and attempts to assign AROs from other teams with excess staff.

        Args:
            available_by_team_and_period: Dictionary mapping (team_id, period) to lists of available employees
            teams: List of team objects
            period: The current period being processed
            prefetched_data: Dictionary containing prefetched data

        Returns:
            Set of team IDs that were influenced (either provided or received AROs)
        """
        influenced_teams = set()

        # Create a mapping of team_id to team object for easier lookup
        teams_by_id = {team.id: team for team in teams}

        # Identify understaffed teams
        understaffed_teams = {}
        overstaffed_teams = {}

        for team in teams:
            team_id = team.id
            key = (team_id, period)

            if key not in available_by_team_and_period:
                logger.warning(f"No availability data for team {team_id} in period {period}")
                continue

            available_employees = available_by_team_and_period[key]

            # Get the number of workstations (required staff)
            required_staff = len(team.workstations)
            available_staff = len(available_employees)

            # Calculate staffing difference
            staffing_difference = available_staff - required_staff

            if staffing_difference < 0:
                # Team is understaffed
                understaffed_teams[team_id] = {
                    'team': team,
                    'shortage': abs(staffing_difference),
                    'available': available_employees
                }
                logger.info(f"Team {team.name} (ID: {team_id}) is understaffed by {abs(staffing_difference)} employees in period {period}")
            elif staffing_difference > 0:
                # Team has excess staff that could be used as AROs
                overstaffed_teams[team_id] = {
                    'team': team,
                    'excess': staffing_difference,
                    'available': available_employees
                }
                logger.info(f"Team {team.name} (ID: {team_id}) has {staffing_difference} excess employees in period {period}")

        # If no understaffed teams, return empty set
        if not understaffed_teams:
            logger.info(f"No understaffed teams found for period {period}")
            return influenced_teams

        # If no overstaffed teams, return empty set
        if not overstaffed_teams:
            logger.warning(f"No overstaffed teams found to provide AROs for period {period}")
            return influenced_teams

        # Assign AROs from overstaffed teams to understaffed teams
        for understaffed_id, understaffed_data in understaffed_teams.items():
            shortage = understaffed_data['shortage']
            understaffed_team = understaffed_data['team']

            # Sort overstaffed teams by excess staff (descending)
            sorted_overstaffed = sorted(
                overstaffed_teams.items(),
                key=lambda x: x[1]['excess'],
                reverse=True
            )

            for overstaffed_id, overstaffed_data in sorted_overstaffed:
                if shortage <= 0:
                    break

                excess = overstaffed_data['excess']
                overstaffed_team = overstaffed_data['team']
                available_employees = overstaffed_data['available']

                # Determine how many AROs to assign from this team
                aro_count = min(excess, shortage)

                if aro_count <= 0:
                    continue

                # Select employees to assign as AROs (prefer those with most qualifications)
                potential_aros = sorted(
                    available_employees,
                    key=lambda e: len(getattr(e, 'qualifications', [])),
                    reverse=True
                )[:aro_count]

                # Create ARO assignments
                for employee in potential_aros:
                    try:
                        # Check if we have the repository to create assignments
                        if self.aro_assignment_repository:
                            # Get the current date from prefetched data or use today's date
                            assignment_date = prefetched_data.get('schedule_date', date.today())

                            # Create a new ARO assignment
                            aro_assignment = AROAssignment.create(
                                employee_id=employee.id,
                                from_team_id=overstaffed_id,
                                to_team_id=understaffed_id,
                                assignment_date=assignment_date,
                                period=period
                            )

                            # Save the assignment
                            self.aro_assignment_repository.add(aro_assignment)

                            logger.info(
                                f"Created ARO assignment: Employee {employee.name} (ID: {employee.id}) "
                                f"from team {overstaffed_team.name} (ID: {overstaffed_id}) "
                                f"to team {understaffed_team.name} (ID: {understaffed_id}) "
                                f"for period {period}"
                            )

                            # Update the available employees for the understaffed team
                            key = (understaffed_id, period)
                            if key in available_by_team_and_period:
                                available_by_team_and_period[key].append(employee)

                            # Mark both teams as influenced
                            influenced_teams.add(overstaffed_id)
                            influenced_teams.add(understaffed_id)

                            # Reduce the shortage and excess counts
                            shortage -= 1
                            overstaffed_data['excess'] -= 1

                    except Exception as e:
                        logger.error(
                            f"Error creating ARO assignment for employee {employee.id} "
                            f"from team {overstaffed_id} to team {understaffed_id}: {str(e)}"
                        )

        return influenced_teams
