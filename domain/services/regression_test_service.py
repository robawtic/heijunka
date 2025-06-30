# domain/services/regression_test_service.py
from typing import List, Dict, Any, Optional, Tuple
import json
import os
import logging
from datetime import date

from domain.value_objects.regression_test_scenario import RegressionTestScenario
from domain.services.scenario_simulator import ScenarioSimulator
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.schedule_repository_interface import ScheduleRepositoryInterface
from domain.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)

class RegressionTestResult:
    """Value object representing the result of a regression test."""

    def __init__(
        self,
        scenario_name: str,
        passed: bool,
        metrics_results: Dict[str, Tuple[Any, Any, bool]],
        error_message: Optional[str] = None
    ):
        self.scenario_name = scenario_name
        self.passed = passed
        self.metrics_results = metrics_results  # Dict of metric_name -> (expected, actual, passed)
        self.error_message = error_message

    def __str__(self):
        if self.error_message:
            return f"Regression Test '{self.scenario_name}': FAILED - {self.error_message}"

        status = "PASSED" if self.passed else "FAILED"
        return f"Regression Test '{self.scenario_name}': {status}"

    def get_failed_metrics(self) -> Dict[str, Tuple[Any, Any]]:
        """Get a dictionary of metrics that failed the regression test."""
        return {
            metric: (expected, actual)
            for metric, (expected, actual, passed) in self.metrics_results.items()
            if not passed
        }

class RegressionTestService:
    """Service for running regression tests and comparing results with golden outputs."""

    def __init__(
        self,
        employee_repository: EmployeeRepositoryInterface,
        workstation_repository: WorkstationRepositoryInterface,
        team_repository: TeamRepositoryInterface,
        schedule_service: ScheduleService,
        schedule_repository: Optional[ScheduleRepositoryInterface] = None,
        session_factory=None
    ):
        self.simulator = ScenarioSimulator(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            schedule_service=schedule_service,
            schedule_repository=schedule_repository,
            session_factory=session_factory
        )
        self.session_factory = session_factory

    def run_regression_tests(self, scenarios: List[RegressionTestScenario]) -> List[RegressionTestResult]:
        """
        Run regression tests for the given scenarios and return the results.

        Args:
            scenarios: List of regression test scenarios to run

        Returns:
            List of regression test results
        """
        logger.info(f"Running {len(scenarios)} regression tests")

        results = []

        for scenario in scenarios:
            try:
                # Run the scenario
                scenario_result = self.simulator.run_scenario(scenario)

                # Compare metrics with expected values
                metrics_results = {}
                all_passed = True

                for metric_name, actual_value in scenario_result['metrics'].items():
                    expected_value = scenario.expected_metrics.get(metric_name)
                    passed = scenario.is_metric_within_tolerance(metric_name, actual_value)

                    metrics_results[metric_name] = (expected_value, actual_value, passed)

                    if not passed and metric_name in scenario.expected_metrics:
                        all_passed = False

                # Create result object
                result = RegressionTestResult(
                    scenario_name=scenario.name,
                    passed=all_passed,
                    metrics_results=metrics_results
                )

                results.append(result)

                # Log result
                if all_passed:
                    logger.info(f"Regression test '{scenario.name}' passed")
                else:
                    failed_metrics = result.get_failed_metrics()
                    logger.warning(
                        f"Regression test '{scenario.name}' failed. "
                        f"Failed metrics: {failed_metrics}"
                    )

            except Exception as e:
                logger.error(f"Error running regression test '{scenario.name}': {str(e)}")

                # Create error result
                result = RegressionTestResult(
                    scenario_name=scenario.name,
                    passed=False,
                    metrics_results={},
                    error_message=str(e)
                )

                results.append(result)

        return results

    def load_regression_tests_from_file(self, file_path: str, team_name: str, start_date: date) -> List[RegressionTestScenario]:
        """
        Load regression test scenarios from a JSON file.

        Args:
            file_path: Path to the JSON file
            team_name: Name of the team to run tests for
            start_date: Start date for the tests

        Returns:
            List of regression test scenarios
        """
        logger.info(f"Loading regression tests from {file_path}")

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading regression tests from {file_path}: {str(e)}")
            raise ValueError(f"Error loading regression tests: {str(e)}")

        # Get team ID
        team = self.simulator.team_repository.get_by_name(team_name)
        if not team:
            raise ValueError(f"Team '{team_name}' not found")

        # Create scenarios
        scenarios = []

        for scenario_data in data:
            scenario = RegressionTestScenario(
                name=scenario_data.get('name', 'Unnamed Scenario'),
                team_id=team.id,
                start_date=start_date,
                periods_per_day=scenario_data.get('periods_per_day', 4),
                call_ins=scenario_data.get('call_ins', []),
                offline=scenario_data.get('offline', []),
                force_complete=scenario_data.get('force_complete', False),
                metadata=scenario_data.get('metadata', {}),
                expected_metrics=scenario_data.get('expected_metrics', {}),
                tolerance_thresholds=scenario_data.get('tolerance_thresholds', {})
            )

            scenarios.append(scenario)

        logger.info(f"Loaded {len(scenarios)} regression test scenarios")

        return scenarios

    def save_golden_outputs(self, scenarios: List[RegressionTestScenario], output_file: str):
        """
        Run the given scenarios and save the results as golden outputs.

        Args:
            scenarios: List of scenarios to run
            output_file: Path to save the golden outputs
        """
        logger.info(f"Generating golden outputs for {len(scenarios)} scenarios")

        # Run scenarios and collect results
        golden_data = []

        for scenario in scenarios:
            try:
                # Run the scenario
                result = self.simulator.run_scenario(scenario)

                # Create golden output data
                golden_scenario = {
                    'name': scenario.name,
                    'call_ins': scenario.call_ins,
                    'offline': scenario.offline,
                    'force_complete': scenario.force_complete,
                    'periods_per_day': scenario.periods_per_day,
                    'metadata': scenario.metadata,
                    'expected_metrics': result['metrics'],
                    'tolerance_thresholds': scenario.tolerance_thresholds
                }

                golden_data.append(golden_scenario)

                logger.info(f"Generated golden output for scenario '{scenario.name}'")

            except Exception as e:
                logger.error(f"Error generating golden output for scenario '{scenario.name}': {str(e)}")

        # Save to file
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(golden_data, f, indent=2)

            logger.info(f"Saved golden outputs to {output_file}")

        except Exception as e:
            logger.error(f"Error saving golden outputs to {output_file}: {str(e)}")
            raise ValueError(f"Error saving golden outputs: {str(e)}")
