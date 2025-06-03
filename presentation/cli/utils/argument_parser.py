"""
Command-line argument parsing utilities for the CLI application.
"""
import argparse
from datetime import date
from typing import Any
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("presentation.cli.utils.argument_parser", rate_limit=True)

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments
    """
    logger.debug("Parsing command line arguments", event_type="arguments", identifier="parse_start")
    
    parser = argparse.ArgumentParser(description='Heijunka Scheduling System')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Generate schedule command
    generate_parser = subparsers.add_parser('generate', help='Generate a schedule')
    team_group = generate_parser.add_mutually_exclusive_group(required=True)
    team_group.add_argument('--team', type=str, help='Team name')
    team_group.add_argument('--group', type=str, help='Group name (generates schedules for all teams in the group)')
    team_group.add_argument('--department', type=str, help='Department name (generates schedules for all teams in the department)')
    generate_parser.add_argument('--start-date', type=str, default=date.today().isoformat(), help='Start date for the schedule (YYYY-MM-DD)')
    generate_parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    generate_parser.add_argument('--call-ins', type=str, nargs='*', help='Employees calling in')
    generate_parser.add_argument('--offline', type=str, nargs='*', help='Employees offline for specific periods in format "employee:periods" (e.g., "John:1,2")')
    generate_parser.add_argument('--force-complete', action='store_true', help='Force complete the schedule')

    # Simulation command
    simulate_parser = subparsers.add_parser('simulate', help='Run scheduling simulations')
    simulate_parser.add_argument('--team', type=str, required=True, help='Team name')
    simulate_parser.add_argument('--start-date', type=str, default=date.today().isoformat(), help='Start date for the schedule (YYYY-MM-DD)')
    simulate_parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    simulate_parser.add_argument('--scenarios', type=str, required=True, help='Path to scenarios JSON file')
    simulate_parser.add_argument('--output-dir', type=str, default='.', help='Directory to save output files')
    simulate_parser.add_argument('--advanced', action='store_true', help='Generate advanced analytics')

    # Regression test command
    regression_parser = subparsers.add_parser('regression-test', help='Run regression tests against golden outputs')
    regression_parser.add_argument('--team', type=str, required=True, help='Team name')
    regression_parser.add_argument('--start-date', type=str, default=date.today().isoformat(), help='Start date for the schedule (YYYY-MM-DD)')
    regression_parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    regression_parser.add_argument('--tests', type=str, required=True, help='Path to regression tests JSON file')
    regression_parser.add_argument('--output-dir', type=str, default='.', help='Directory to save output files')
    regression_parser.add_argument('--generate-golden', action='store_true', help='Generate golden outputs instead of running tests')
    regression_parser.add_argument('--golden-output', type=str, help='Path to save golden outputs (required if --generate-golden is used)')
    regression_parser.add_argument('--threshold', type=float, default=0.0, help='Global threshold for all metrics (overrides defaults)')

    # Manual assignment command
    assign_parser = subparsers.add_parser('assign', help='Create a manual assignment')
    assign_parser.add_argument('--employee', type=str, required=True, help='Employee name')
    assign_parser.add_argument('--workstation', type=str, required=True, help='Workstation name')
    assign_parser.add_argument('--date', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    assign_parser.add_argument('--period', type=int, required=True, help='Work period (1-4)')
    assign_parser.add_argument('--schedule-id', type=int, help='Schedule ID (optional)')

    # ARO assignment commands
    aro_subparsers = subparsers.add_parser('aro', help='ARO management commands')
    aro_subparsers = aro_subparsers.add_subparsers(dest='aro_command', help='ARO command to execute')

    # ARO assign command
    aro_assign_parser = aro_subparsers.add_parser('assign', help='Assign an employee as an ARO to another team')
    aro_assign_parser.add_argument('--employee', '-e', type=str, required=True, help='Employee name')
    aro_assign_parser.add_argument('--from-team', '-f', type=str, required=True, help='From team name')
    aro_assign_parser.add_argument('--to-team', '-t', type=str, required=True, help='To team name')
    aro_assign_parser.add_argument('--date', '-d', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    aro_assign_parser.add_argument('--period', '-p', type=int, default=None, help='Period (1-4, omit for full day)')

    # ARO remove command
    aro_remove_parser = aro_subparsers.add_parser('remove', help='Remove an ARO assignment')
    aro_remove_parser.add_argument('--employee', '-e', type=str, required=True, help='Employee name')
    aro_remove_parser.add_argument('--date', '-d', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    aro_remove_parser.add_argument('--period', '-p', type=int, default=None, help='Period (1-4, omit for full day)')

    # ARO optimize command
    aro_optimize_parser = aro_subparsers.add_parser('optimize', help='Optimize ARO assignments using graph theory')
    aro_optimize_parser.add_argument('--team', '-t', type=str, required=True, help='Understaffed team name')
    aro_optimize_parser.add_argument('--count', '-c', type=int, required=True, help='Number of AROs needed')
    aro_optimize_parser.add_argument('--date', '-d', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    aro_optimize_parser.add_argument('--period', '-p', type=int, default=None, help='Period (1-4, omit for full day)')
    aro_optimize_parser.add_argument('--max-hops', '-m', type=int, default=2, help='Maximum number of intermediate teams (default: 2)')

    args = parser.parse_args()
    logger.debug(f"Parsed arguments: {args}", event_type="arguments", identifier="parse_complete")
    
    return args