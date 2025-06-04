"""
Formatting utilities for the CLI application.
"""
from typing import List, Dict, Optional, Any, Union
from datetime import date
from tabulate import tabulate

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.work_assignment import WorkAssignment
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("presentation.cli.utils.formatting", rate_limit=True)

def format_schedule_table(
    assignments: List[WorkAssignment],
    employees: List[Employee],
    workstations: List[Workstation],
    periods: int,
    date_obj: date,
    call_ins: Optional[List[str]] = None,
    offline: Optional[List[str]] = None,
    aro_assignments_by_team: Optional[Dict[int, Dict[str, List[int]]]] = None,
    aro_assignments_by_team_period: Optional[Dict[int, Dict[int, Dict[str, List[int]]]]] = None,
    aro_assignments_by_employee: Optional[Dict[int, List[Any]]] = None,
    employees_by_id: Optional[Dict[int, Employee]] = None,
    team_id: Optional[int] = None
) -> str:
    """
    Format assignments as a readable table for a specific date using tabulate.

    Args:
        assignments: List of WorkAssignment objects
        employees: List of Employee objects
        workstations: List of Workstation objects
        periods: Number of periods per day
        date_obj: The date to display
        call_ins: List of employee names who called in (unavailable)
        offline: List of strings in format "employee:periods" specifying which employees are offline for which periods
        aro_assignments_by_team: Dictionary mapping team IDs to dictionaries with 'out' and 'in' lists of employee IDs
        aro_assignments_by_team_period: Dictionary mapping team IDs and periods to dictionaries with 'out' and 'in' lists of employee IDs
        aro_assignments_by_employee: Dictionary mapping employee IDs to lists of ARO assignments
        employees_by_id: Dictionary mapping employee IDs to Employee objects
        team_id: ID of the team for which the schedule is being displayed

    Returns:
        str: Formatted schedule as a string
    """
    logger.debug(
        f"Formatting schedule table for date {date_obj}",
        event_type="format_schedule",
        identifier=str(date_obj)
    )

    # Filter assignments for the specified date
    day_assignments = [a for a in assignments if a.period.date == date_obj]

    # Create a dictionary to store the schedule: {workstation_name: {period: employee_name}}
    schedule = {}
    for ws in workstations:
        schedule[ws.name] = {p+1: "-" for p in range(periods)}

    # Add special rows
    schedule["Offline"] = {p+1: "-" for p in range(periods)}
    schedule["Called-in"] = {p+1: "-" for p in range(periods)}
    schedule["AROs"] = {p+1: "-" for p in range(periods)}

    # Fill in the schedule with assignments
    for assignment in day_assignments:
        ws_name = assignment.workstation.name
        period = assignment.period.period
        emp_name = assignment.employee.name

        # Check if workstation exists in schedule dictionary
        if ws_name not in schedule:
            logger.warning(
                f"Workstation '{ws_name}' not found in workstations list for team",
                event_type="missing_workstation",
                identifier=ws_name,
                extra={
                    "workstation_name": ws_name
                }
            )
            # Add the missing workstation to the schedule
            schedule[ws_name] = {p+1: "-" for p in range(periods)}

        schedule[ws_name][period] = emp_name

    # Parse offline parameter
    employee_offline_periods = {}
    if offline:
        for offline_str in offline:
            parts = offline_str.split(':')
            if len(parts) == 2:
                emp_name, periods_str = parts
                periods_list = [int(p) for p in periods_str.split(',')]
                employee_offline_periods[emp_name] = periods_list

    # Find offline employees (available but not assigned or explicitly marked as offline)
    for p in range(1, periods+1):
        # Get all employees assigned to a workstation in this period
        assigned_employees = {a.employee.id for a in day_assignments if a.period.period == p}

        # Find employees who are available but not assigned
        unassigned_employees = []
        for emp in employees:
            if emp.id not in assigned_employees and emp.is_available_for_period(date_obj, p):
                unassigned_employees.append(emp.name)

        # Find employees who are explicitly marked as offline for this period
        explicitly_offline = []
        for emp_name, offline_periods in employee_offline_periods.items():
            if p in offline_periods:
                explicitly_offline.append(f"{emp_name} (offline)")

        # Combine both lists
        offline_employees = explicitly_offline + unassigned_employees

        # Add to the schedule
        if offline_employees:
            schedule["Offline"][p] = ", ".join(offline_employees)

    # Add called-in employees to the Called-in row
    if call_ins:
        # Show called-in employees in all periods
        called_in_names = []
        for emp in employees:
            if emp.name in call_ins:
                called_in_names.append(emp.name)

        if called_in_names:
            for p in range(1, periods+1):
                schedule["Called-in"][p] = ", ".join(called_in_names)

    # Add ARO information to the AROs row
    if team_id is not None and (aro_assignments_by_team_period or aro_assignments_by_team) and employees_by_id:
        for p in range(1, periods+1):
            aro_info = []

            # Check for period-specific ARO assignments
            if aro_assignments_by_team_period and team_id in aro_assignments_by_team_period and p in aro_assignments_by_team_period[team_id]:
                period_data = aro_assignments_by_team_period[team_id][p]

                # Process outgoing AROs (employees leaving this team)
                for emp_id in period_data.get('out', []):
                    if emp_id in employees_by_id:
                        emp = employees_by_id[emp_id]
                        aro_info.append(f"{emp.name}[From]")

                # Process incoming AROs (employees joining this team)
                for emp_id in period_data.get('in', []):
                    if emp_id in employees_by_id:
                        emp = employees_by_id[emp_id]
                        aro_info.append(f"{emp.name}[To]")

            # Check for full-day ARO assignments if no period-specific ones were found
            elif aro_assignments_by_team and team_id in aro_assignments_by_team:
                team_data = aro_assignments_by_team[team_id]

                # Process outgoing AROs (employees leaving this team)
                for emp_id in team_data.get('out', []):
                    if emp_id in employees_by_id:
                        emp = employees_by_id[emp_id]
                        aro_info.append(f"{emp.name}[From]")

                # Process incoming AROs (employees joining this team)
                for emp_id in team_data.get('in', []):
                    if emp_id in employees_by_id:
                        emp = employees_by_id[emp_id]
                        aro_info.append(f"{emp.name}[To]")

            if aro_info:
                schedule["AROs"][p] = ", ".join(aro_info)

    # Prepare data for tabulate
    headers = ["Station"] + [f"P{p}" for p in range(1, periods+1)]
    table_data = []

    # Get all workstation names from the schedule (excluding special rows)
    regular_stations = [name for name in schedule.keys() if name not in ["Offline", "Called-in", "AROs"]]

    # Define the order: regular workstations first, then special rows
    station_order = sorted(regular_stations) + ["AROs", "Offline", "Called-in"]

    # Create a dictionary mapping workstation names to their objects for easy lookup
    workstation_dict = {ws.name: ws for ws in workstations}

    # Add rows in the specified order
    for station in station_order:
        if station in schedule:
            row = [station]

            # Apply color highlighting based on workstation properties
            color = ''
            if station in workstation_dict and station not in ["Offline", "Called-in"]:
                ws = workstation_dict[station]
                if hasattr(ws, 'is_heavy_job') and ws.is_heavy_job:
                    color = '\033[91m'  # Red for heavy jobs
                elif hasattr(ws, 'is_loading_job') and ws.is_loading_job:
                    color = '\033[93m'  # Yellow for loading jobs

            for p in range(1, periods+1):
                value = schedule[station].get(p, "-")
                if color and value != "-":
                    row.append(f"{color}{value}\033[0m")  # Add color and reset
                else:
                    row.append(value)

            table_data.append(row)

    # Format using tabulate
    table_str = tabulate(table_data, headers=headers, tablefmt="grid")

    # Add header
    return f"Schedule for {date_obj}:\n{table_str}"
