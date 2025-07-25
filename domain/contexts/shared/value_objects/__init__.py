"""
Shared Context - Value Objects

This module contains all value objects that are shared across multiple contexts including:
- RegressionTestScenario: Value object for regression testing scenarios
- Scenario: Value object for general scenario definitions
"""

from .regression_test_scenario import RegressionTestScenario
from .scenario import Scenario

__all__ = [
    'RegressionTestScenario',
    'Scenario',
]