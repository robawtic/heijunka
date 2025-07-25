# domain/value_objects/regression_test_scenario.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import date

from domain.contexts.shared.value_objects.scenario import Scenario

@dataclass
class RegressionTestScenario(Scenario):
    """
    Represents a regression test scenario with expected metrics.

    This extends the base Scenario class to include expected metrics
    and tolerance thresholds for regression testing.
    """
    expected_metrics: Dict[str, Any] = field(default_factory=dict)
    tolerance_thresholds: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()

        # Set default tolerance thresholds if not provided
        default_thresholds = {
            'total_assignments': 0,  # Exact match required
            'min_employee_assignments': 0,  # Exact match required
            'max_employee_assignments': 0,  # Exact match required
            'avg_employee_assignments': 0.1,  # 10% tolerance
            'std_dev_employee_assignments': 0.2,  # 20% tolerance
            'min_workstation_utilization': 0,  # Exact match required
            'max_workstation_utilization': 0,  # Exact match required
            'avg_workstation_utilization': 0.1,  # 10% tolerance
        }

        # Apply default thresholds for any metrics not explicitly set
        for metric, threshold in default_thresholds.items():
            if metric not in self.tolerance_thresholds:
                self.tolerance_thresholds[metric] = threshold

    def is_metric_within_tolerance(self, metric_name: str, actual_value: Any) -> bool:
        """
        Check if the actual metric value is within the tolerance threshold
        of the expected value.

        Args:
            metric_name: Name of the metric to check
            actual_value: Actual value of the metric

        Returns:
            True if the metric is within tolerance, False otherwise
        """
        if metric_name not in self.expected_metrics:
            return True  # No expected value, so always within tolerance

        expected_value = self.expected_metrics[metric_name]
        threshold = self.tolerance_thresholds.get(metric_name, 0)

        # Handle different types of metrics
        if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
            # For numeric metrics, check if within percentage threshold
            if expected_value == 0:
                return actual_value == 0

            percentage_diff = abs(actual_value - expected_value) / abs(expected_value)
            return percentage_diff <= threshold
        else:
            # For non-numeric metrics, require exact match
            return actual_value == expected_value

    def __str__(self):
        return f"Regression Test Scenario '{self.name}' for team {self.team_id} starting {self.start_date}"
