"""
Simulation command handling for the CLI application.
"""
import sys
import os
from typing import Optional, Any, Dict, List, Tuple, Union
from datetime import datetime
from sqlalchemy.orm import Session
from tabulate import tabulate

from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.services.schedule_service import ScheduleService
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("presentation.cli.commands.simulation_command", rate_limit=True)

def handle_simulation(args: Any, session_factory: Any) -> bool:
    """
    Handle the simulation command.

    Args:
        args: Command line arguments
        session_factory: Database session factory

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    try:
        import json
        from domain.value_objects.scenario import Scenario
        from domain.services.scenario_simulator import ScenarioSimulator
        from domain.services.scenario_comparator import ScenarioComparator

        logger.info(
            f"Handling simulation command for team '{args.team}'", 
            event_type="simulation", 
            identifier="start"
        )

        # Setup repositories
        logger.debug(
            "Setting up repositories for simulation", 
            event_type="simulation", 
            identifier="setup"
        )
        
        employee_repository = SqlAlchemyEmployeeRepository(session_factory)
        workstation_repository = SqlAlchemyWorkstationRepository(session_factory)
        team_repository = SqlAlchemyTeamRepository(session_factory)
        schedule_repository = SqlAlchemyScheduleRepository(session_factory)
        schedule_service = ScheduleService()

        # Get team by name
        logger.debug(
            f"Looking up team: {args.team}", 
            event_type="simulation", 
            identifier="team_lookup"
        )
        
        team = team_repository.get_by_name(args.team)
        if not team:
            error_msg = f"Error: Team '{args.team}' not found"
            logger.error(
                error_msg, 
                event_type="simulation", 
                identifier="team_lookup"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Parse start date
        logger.debug(
            f"Parsing date: {args.start_date}", 
            event_type="simulation", 
            identifier="date_parsing"
        )
        
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            error_msg = f"Error: Invalid date format. Use YYYY-MM-DD"
            logger.error(
                error_msg, 
                event_type="simulation", 
                identifier="date_parsing"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Load scenarios from JSON file
        logger.debug(
            f"Loading scenarios from file: {args.scenarios}", 
            event_type="simulation", 
            identifier="load_scenarios"
        )
        
        try:
            with open(args.scenarios, 'r') as f:
                scenarios_data = json.load(f)
        except Exception as e:
            error_msg = f"Error loading scenarios file: {e}"
            logger.error(
                error_msg, 
                event_type="simulation", 
                identifier="load_scenarios",
                extra={"exception": str(e)}
            )
            print(error_msg, file=sys.stderr)
            return False

        # Create scenario objects
        scenarios = []
        for i, scenario_data in enumerate(scenarios_data):
            scenario = Scenario(
                name=scenario_data.get('name', f"Scenario_{i+1}"),
                team_id=team.id,
                start_date=start_date,
                periods_per_day=args.periods,
                call_ins=scenario_data.get('call_ins', []),
                offline=scenario_data.get('offline', []),
                force_complete=scenario_data.get('force_complete', False),
                metadata=scenario_data.get('metadata', {})
            )
            scenarios.append(scenario)

        logger.info(
            f"Running {len(scenarios)} scenarios for team '{args.team}'", 
            event_type="simulation", 
            identifier="run_scenarios"
        )
        print(f"Running {len(scenarios)} scenarios for team '{args.team}'...")

        # Create simulator and run scenarios
        simulator = ScenarioSimulator(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            schedule_service=schedule_service,
            schedule_repository=schedule_repository,
            session_factory=session_factory
        )

        results = simulator.run_scenarios(scenarios)

        logger.info(
            f"Successfully ran {len(results)} scenarios", 
            event_type="simulation", 
            identifier="scenarios_complete"
        )
        print(f"Successfully ran {len(results)} scenarios.")

        # Compare results
        if args.advanced:
            # Use advanced analytics
            logger.info(
                "Generating advanced analytics", 
                event_type="simulation", 
                identifier="advanced_analytics"
            )
            
            from domain.analytics.scenario_analytics import ScenarioAnalytics
            analytics = ScenarioAnalytics(results, session_factory=session_factory)
            analytics.generate_advanced_analytics(args.output_dir)
            print(f"Generated advanced analytics in: {args.output_dir}")

            # Get comparison report for summary table
            comparison_df = analytics.comparator.generate_comparison_report(
                os.path.join(args.output_dir, "scenario_comparison.csv")
            )
        else:
            # Use basic comparator
            logger.info(
                "Generating basic comparison report", 
                event_type="simulation", 
                identifier="basic_comparison"
            )
            
            comparator = ScenarioComparator(results)

            # Generate comparison report
            report_path = os.path.join(args.output_dir, "scenario_comparison.csv")
            comparison_df = comparator.generate_comparison_report(report_path)
            print(f"Generated comparison report: {report_path}")

            # Generate comparison charts
            comparator.generate_comparison_charts(args.output_dir)
            print(f"Generated comparison charts in: {args.output_dir}")

            # Generate scenario heatmap
            comparator.generate_scenario_heatmap(args.output_dir)
            print(f"Generated scenario heatmap in: {args.output_dir}")

        # Print summary table
        logger.info(
            "Generating summary table", 
            event_type="simulation", 
            identifier="summary_table"
        )
        
        print("\nScenario Comparison Summary:")
        summary_cols = ['Scenario', 'Total Assignments']
        if 'Min Employee Assignments' in comparison_df.columns:
            summary_cols.extend(['Min Employee Assignments', 'Max Employee Assignments', 'Avg Employee Assignments'])
        
        print(tabulate(
            comparison_df[summary_cols].values.tolist(),
            headers=summary_cols,
            tablefmt="grid"
        ))

        logger.info(
            "Simulation completed successfully", 
            event_type="simulation", 
            identifier="complete"
        )
        return True

    except Exception as e:
        error_msg = f"Error running simulations: {e}"
        logger.error(
            error_msg, 
            event_type="simulation", 
            identifier="exception",
            extra={"exception": str(e)}
        )
        print(error_msg, file=sys.stderr)
        return False