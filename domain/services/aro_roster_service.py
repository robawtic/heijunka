# domain/services/aro_roster_service.py
from typing import List, Dict, Set, Optional
from datetime import date
import logging

from domain.entities.employee import Employee

# Logger for this module
logger = logging.getLogger(__name__)

class ARORosterService:
    def __init__(self, aro_assignment_repository=None, team_repository=None):
        self.aro_assignment_repository = aro_assignment_repository
        self.team_repository = team_repository
    
    def handle_aro_assignments(self, employees: List[Employee], team_id: int,
                              start_date: date, prefetched_data: Optional[Dict] = None) -> List[Employee]:
        """
        Handle ARO (Assigned Relief Operator) assignments by:
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