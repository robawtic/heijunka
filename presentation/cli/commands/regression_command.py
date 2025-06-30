"""
Regression test command handling for the CLI application.
"""
import sys
import os
from typing import Optional, Any, Dict, List, Tuple, Union, cast
from datetime import datetime, date
from sqlalchemy.orm import Session
from tabulate import tabulate

from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.services.schedule_service import ScheduleService
from utilities.logging_factory import get_logger, RateLimitedLogger

# Create a logger for this module
logger = cast(RateLimitedLogger, get_logger("presentation.cli.commands.regression_command", rate_limit=True))

def handle_regression_test(args: Any, session_factory: Any) -> bool:
    """
    Handle the regression test command.

    Args:
        args: Command line arguments
        session_factory: Database session factory

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    try:
        from domain.services.regression_test_service import RegressionTestService
        from domain.value_objects.regression_test_scenario import RegressionTestScenario

        logger.info(
            f"Handling regression test command for team '{args.team}'", 
            event_type="regression_test", 
            identifier="start"
        )

        # Setup repositories
        logger.debug(
            "Setting up repositories for regression test", 
            event_type="regression_test", 
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
            event_type="regression_test", 
            identifier="team_lookup"
        )

        team = team_repository.get_by_name(args.team)
        if not team:
            error_msg = f"Error: Team '{args.team}' not found"
            logger.error(
                error_msg, 
                event_type="regression_test", 
                identifier="team_lookup"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Parse start date
        logger.debug(
            f"Parsing date: {args.start_date}", 
            event_type="regression_test", 
            identifier="date_parsing"
        )

        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            error_msg = f"Error: Invalid date format. Use YYYY-MM-DD"
            logger.error(
                error_msg, 
                event_type="regression_test", 
                identifier="date_parsing"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Create regression test service
        regression_service = RegressionTestService(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            schedule_service=schedule_service,
            schedule_repository=schedule_repository,
            session_factory=session_factory
        )

        # Check if we're generating golden outputs
        if args.generate_golden:
            return handle_generate_golden(args, regression_service, team, start_date)

        # Run regression tests
        return handle_run_regression_tests(args, regression_service, team, start_date)

    except Exception as e:
        error_msg = f"Error handling regression test command: {e}"
        logger.error(
            error_msg, 
            event_type="regression_test", 
            identifier="exception",
            extra={"exception": str(e)}
        )
        print(error_msg, file=sys.stderr)
        return False

def handle_generate_golden(
    args: Any, 
    regression_service: Any, 
    team: Any, 
    start_date: date
) -> bool:
    """
    Handle generating golden outputs for regression tests.

    Args:
        args: Command line arguments
        regression_service: Regression test service
        team: Team object
        start_date: Start date for the tests

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    if not args.golden_output:
        error_msg = "Error: --golden-output is required when using --generate-golden"
        logger.error(
            error_msg, 
            event_type="regression_test", 
            identifier="missing_golden_output"
        )
        print(error_msg, file=sys.stderr)
        return False

    # Load scenarios from the tests file
    logger.info(
        f"Loading regression tests from file: {args.tests}", 
        event_type="regression_test", 
        identifier="load_tests"
    )

    try:
        scenarios = regression_service.load_regression_tests_from_file(args.tests, args.team, start_date)
    except Exception as e:
        error_msg = f"Error loading regression tests: {e}"
        logger.error(
            error_msg, 
            event_type="regression_test", 
            identifier="load_tests",
            extra={"exception": str(e)}
        )
        print(error_msg, file=sys.stderr)
        return False

    # Apply global threshold if specified
    if args.threshold > 0:
        logger.info(
            f"Applying global threshold: {args.threshold}", 
            event_type="regression_test", 
            identifier="apply_threshold"
        )

        for scenario in scenarios:
            for metric in scenario.tolerance_thresholds:
                scenario.tolerance_thresholds[metric] = args.threshold

    # Generate golden outputs
    logger.info(
        f"Generating golden outputs for {len(scenarios)} scenarios", 
        event_type="regression_test", 
        identifier="generate_golden"
    )

    try:
        regression_service.save_golden_outputs(scenarios, args.golden_output)
        success_msg = f"Generated golden outputs for {len(scenarios)} scenarios and saved to {args.golden_output}"
        logger.info(
            success_msg, 
            event_type="regression_test", 
            identifier="golden_success"
        )
        print(success_msg)
        return True
    except Exception as e:
        error_msg = f"Error generating golden outputs: {e}"
        logger.error(
            error_msg, 
            event_type="regression_test", 
            identifier="golden_error",
            extra={"exception": str(e)}
        )
        print(error_msg, file=sys.stderr)
        return False

def handle_run_regression_tests(
    args: Any, 
    regression_service: Any, 
    team: Any, 
    start_date: date
) -> bool:
    """
    Handle running regression tests against golden outputs.

    Args:
        args: Command line arguments
        regression_service: Regression test service
        team: Team object
        start_date: Start date for the tests

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    try:
        # Load regression tests
        logger.info(
            f"Loading regression tests from file: {args.tests}", 
            event_type="regression_test", 
            identifier="load_tests"
        )

        scenarios = regression_service.load_regression_tests_from_file(args.tests, args.team, start_date)

        # Apply global threshold if specified
        if args.threshold > 0:
            logger.info(
                f"Applying global threshold: {args.threshold}", 
                event_type="regression_test", 
                identifier="apply_threshold"
            )

            for scenario in scenarios:
                for metric in scenario.tolerance_thresholds:
                    scenario.tolerance_thresholds[metric] = args.threshold

        logger.info(
            f"Running {len(scenarios)} regression tests for team '{args.team}'", 
            event_type="regression_test", 
            identifier="run_tests"
        )
        print(f"Running {len(scenarios)} regression tests for team '{args.team}'...")

        # Run tests
        results = regression_service.run_regression_tests(scenarios)

        # Count passed/failed tests
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        logger.info(
            f"Regression test results: {passed} passed, {failed} failed", 
            event_type="regression_test", 
            identifier="test_results",
            extra={"passed": passed, "failed": failed}
        )
        print(f"\nRegression Test Results: {passed} passed, {failed} failed")

        # Create results table
        table_data = []
        for result in results:
            status = "PASSED" if result.passed else "FAILED"
            if result.error_message:
                reason = result.error_message
            elif not result.passed:
                failed_metrics = result.get_failed_metrics()
                reason = ", ".join(f"{m}: expected={e}, actual={a}" for m, (e, a) in failed_metrics.items())
            else:
                reason = ""

            table_data.append([result.scenario_name, status, reason])

        # Print results table
        print("\n" + tabulate(
            table_data,
            headers=["Scenario", "Status", "Reason"],
            tablefmt="grid"
        ))

        # Save detailed results to file if output directory is specified
        if args.output_dir:
            save_detailed_results(args.output_dir, results, passed, failed, table_data)

        # Return True if all tests passed, False otherwise
        return passed == len(results)

    except Exception as e:
        error_msg = f"Error running regression tests: {e}"
        logger.error(
            error_msg, 
            event_type="regression_test", 
            identifier="run_error",
            extra={"exception": str(e)}
        )
        print(error_msg, file=sys.stderr)
        return False

def save_detailed_results(
    output_dir: str, 
    results: List[Any], 
    passed: int, 
    failed: int, 
    table_data: List[List[str]]
) -> None:
    """
    Save detailed regression test results to files.

    Args:
        output_dir: Directory to save results
        results: List of test results
        passed: Number of passed tests
        failed: Number of failed tests
        table_data: Table data for summary
    """
    logger.info(
        f"Saving detailed results to directory: {output_dir}", 
        event_type="regression_test", 
        identifier="save_results"
    )

    os.makedirs(output_dir, exist_ok=True)

    # Save summary to file
    summary_file = os.path.join(output_dir, "regression_test_summary.txt")
    with open(summary_file, 'w') as f:
        f.write(f"Regression Test Results: {passed} passed, {failed} failed\n\n")
        f.write(tabulate(
            table_data,
            headers=["Scenario", "Status", "Reason"],
            tablefmt="grid"
        ))

    logger.debug(
        f"Saved summary to {summary_file}", 
        event_type="regression_test", 
        identifier="save_summary"
    )
    print(f"\nSaved summary to {summary_file}")

    # Save detailed results for each scenario
    for i, result in enumerate(results):
        if not result.passed:
            detail_file = os.path.join(output_dir, f"regression_test_{result.scenario_name}.txt")
            with open(detail_file, 'w') as f:
                f.write(f"Regression Test: {result.scenario_name}\n")
                f.write(f"Status: {'PASSED' if result.passed else 'FAILED'}\n")

                if result.error_message:
                    f.write(f"Error: {result.error_message}\n")
                else:
                    f.write("\nMetrics Comparison:\n")
                    metrics_table = []
                    for metric, (expected, actual, passed) in result.metrics_results.items():
                        if expected is not None:  # Only include metrics with expected values
                            status = "PASSED" if passed else "FAILED"
                            metrics_table.append([metric, expected, actual, status])

                    f.write(tabulate(
                        metrics_table,
                        headers=["Metric", "Expected", "Actual", "Status"],
                        tablefmt="grid"
                    ))

            logger.debug(
                f"Saved detailed results for '{result.scenario_name}' to {detail_file}", 
                event_type="regression_test", 
                identifier="save_detail"
            )
            print(f"Saved detailed results for '{result.scenario_name}' to {detail_file}")
