#!/usr/bin/env python
# examples/regression_test_example.py
"""
Example script demonstrating how to use the regression testing framework programmatically.
"""
import sys
import os
import logging
from datetime import date
from tabulate import tabulate

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from domain.models.db import Session
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.services.schedule_service import ScheduleService
from domain.services.regression_test_service import RegressionTestService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function demonstrating regression testing."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run regression tests for scheduling rules')
    parser.add_argument('--team', type=str, required=True, help='Team name')
    parser.add_argument('--tests', type=str, required=True, help='Path to regression tests JSON file')
    parser.add_argument('--start-date', type=str, default=date.today().isoformat(), help='Start date (YYYY-MM-DD)')
    parser.add_argument('--generate-golden', action='store_true', help='Generate golden outputs')
    parser.add_argument('--golden-output', type=str, help='Path to save golden outputs')
    parser.add_argument('--output-dir', type=str, default='.', help='Directory to save output files')
    args = parser.parse_args()
    
    # Parse start date
    try:
        start_date = date.fromisoformat(args.start_date)
    except ValueError:
        logger.error(f"Invalid date format: {args.start_date}. Use YYYY-MM-DD.")
        return 1
    
    # Create database session
    session = Session()
    
    try:
        # Setup repositories
        employee_repository = SqlAlchemyEmployeeRepository(session)
        workstation_repository = SqlAlchemyWorkstationRepository(session)
        team_repository = SqlAlchemyTeamRepository(session)
        schedule_repository = SqlAlchemyScheduleRepository(session)
        schedule_service = ScheduleService()
        
        # Get team by name
        team = team_repository.get_by_name(args.team)
        if not team:
            logger.error(f"Team '{args.team}' not found")
            return 1
        
        # Create regression test service
        regression_service = RegressionTestService(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            schedule_service=schedule_service,
            schedule_repository=schedule_repository,
            session=session
        )
        
        # Check if we're generating golden outputs
        if args.generate_golden:
            if not args.golden_output:
                logger.error("--golden-output is required when using --generate-golden")
                return 1
            
            # Load scenarios from the tests file
            try:
                scenarios = regression_service.load_regression_tests_from_file(args.tests, args.team, start_date)
            except Exception as e:
                logger.error(f"Error loading regression tests: {e}")
                return 1
            
            # Generate golden outputs
            try:
                regression_service.save_golden_outputs(scenarios, args.golden_output)
                logger.info(f"Generated golden outputs for {len(scenarios)} scenarios and saved to {args.golden_output}")
                return 0
            except Exception as e:
                logger.error(f"Error generating golden outputs: {e}")
                return 1
        
        # Run regression tests
        try:
            # Load regression tests
            scenarios = regression_service.load_regression_tests_from_file(args.tests, args.team, start_date)
            
            logger.info(f"Running {len(scenarios)} regression tests for team '{args.team}'...")
            
            # Run tests
            results = regression_service.run_regression_tests(scenarios)
            
            # Count passed/failed tests
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed
            
            logger.info(f"Regression Test Results: {passed} passed, {failed} failed")
            
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
                os.makedirs(args.output_dir, exist_ok=True)
                
                # Save summary to file
                summary_file = os.path.join(args.output_dir, "regression_test_summary.txt")
                with open(summary_file, 'w') as f:
                    f.write(f"Regression Test Results: {passed} passed, {failed} failed\n\n")
                    f.write(tabulate(
                        table_data,
                        headers=["Scenario", "Status", "Reason"],
                        tablefmt="grid"
                    ))
                
                logger.info(f"Saved summary to {summary_file}")
                
                # Save detailed results for each scenario
                for i, result in enumerate(results):
                    if not result.passed:
                        detail_file = os.path.join(args.output_dir, f"regression_test_{result.scenario_name}.txt")
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
                        
                        logger.info(f"Saved detailed results for '{result.scenario_name}' to {detail_file}")
            
            # Return 0 if all tests passed, 1 otherwise
            return 0 if passed == len(results) else 1
            
        except Exception as e:
            logger.error(f"Error running regression tests: {e}")
            return 1
    
    finally:
        session.close()

if __name__ == '__main__':
    sys.exit(main())