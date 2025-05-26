# Automated Regression Testing for the Scheduling System

This document explains how to use the automated regression testing feature of the Heijunka scheduling system.

## Overview

The regression testing feature allows you to:

1. Define expected metrics for scheduling scenarios
2. Run scheduling rules against these scenarios
3. Compare the results with expected metrics
4. Alert when metrics deviate too much from expected values

This is particularly useful when making changes to scheduling rules, as it helps ensure that the changes don't negatively impact the scheduling outcomes.

## Running Regression Tests

To run regression tests, use the `regression-test` command with the following parameters:

```bash
python main.py regression-test --team <team_name> --tests <tests_file> [--start-date <YYYY-MM-DD>] [--periods <num_periods>] [--output-dir <output_directory>] [--threshold <global_threshold>]
```

### Parameters

- `--team`: (Required) The name of the team to test
- `--tests`: (Required) Path to a JSON file containing regression test definitions
- `--start-date`: (Optional) Start date for the schedule in YYYY-MM-DD format (default: current date)
- `--periods`: (Optional) Number of periods per day (default: 4)
- `--output-dir`: (Optional) Directory to save output files (default: current directory)
- `--threshold`: (Optional) Global threshold for all metrics (overrides defaults)

### Example

```bash
python main.py regression-test --team headsub --tests examples/regression_tests.json --start-date 2024-08-19 --output-dir results
```

## Generating Golden Outputs

Before running regression tests, you need to generate "golden" outputs that serve as the baseline for comparison. To generate golden outputs, use the `--generate-golden` flag:

```bash
python main.py regression-test --team <team_name> --tests <tests_file> --generate-golden --golden-output <output_file> [--start-date <YYYY-MM-DD>] [--periods <num_periods>]
```

### Parameters

- `--generate-golden`: Flag to generate golden outputs instead of running tests
- `--golden-output`: (Required with --generate-golden) Path to save golden outputs

### Example

```bash
python main.py regression-test --team headsub --tests examples/regression_tests.json --generate-golden --golden-output examples/golden_outputs.json --start-date 2024-08-19
```

## Regression Test Definition

Regression tests are defined in a JSON file. Each test includes:

- `name`: Name of the test
- `call_ins`: List of employees who are calling in (unavailable)
- `offline`: List of employees offline for specific periods in format "employee:periods" (e.g., "John:1,2")
- `force_complete`: Whether to force completion of the schedule
- `periods_per_day`: Number of periods per day
- `metadata`: Additional test-specific data (optional)
- `expected_metrics`: Expected values for metrics
- `tolerance_thresholds`: Tolerance thresholds for metrics

### Example Regression Test File

```json
[
  {
    "name": "Baseline_Regression",
    "call_ins": [],
    "offline": [],
    "force_complete": false,
    "periods_per_day": 4,
    "metadata": {
      "description": "Baseline scenario for regression testing"
    },
    "expected_metrics": {
      "total_assignments": 16,
      "min_employee_assignments": 2,
      "max_employee_assignments": 4,
      "avg_employee_assignments": 3.2,
      "std_dev_employee_assignments": 0.8,
      "min_workstation_utilization": 2,
      "max_workstation_utilization": 4,
      "avg_workstation_utilization": 3.2
    },
    "tolerance_thresholds": {
      "total_assignments": 0,
      "min_employee_assignments": 0,
      "max_employee_assignments": 0,
      "avg_employee_assignments": 0.1,
      "std_dev_employee_assignments": 0.2,
      "min_workstation_utilization": 0,
      "max_workstation_utilization": 0,
      "avg_workstation_utilization": 0.1
    }
  }
]
```

## Metrics and Thresholds

The regression testing framework compares the following metrics:

- `total_assignments`: Total number of assignments generated
- `min_employee_assignments`: Minimum number of assignments per employee
- `max_employee_assignments`: Maximum number of assignments per employee
- `avg_employee_assignments`: Average number of assignments per employee
- `std_dev_employee_assignments`: Standard deviation of assignments per employee
- `min_workstation_utilization`: Minimum utilization of workstations
- `max_workstation_utilization`: Maximum utilization of workstations
- `avg_workstation_utilization`: Average utilization of workstations

For each metric, you can specify a tolerance threshold. The threshold is a percentage (0.0 to 1.0) that determines how much the actual value can deviate from the expected value. For example, a threshold of 0.1 means the actual value can be up to 10% different from the expected value.

For metrics where exact matches are required (like total_assignments), set the threshold to 0.

## Interpreting Results

When you run regression tests, the system will:

1. Run each test scenario
2. Compare the actual metrics with the expected metrics
3. Report which tests passed and which failed
4. For failed tests, show which metrics were outside the tolerance thresholds

A summary table will be displayed showing the status of each test:

```
Regression Test Results: 2 passed, 1 failed

+---------------------------+---------+-----------------------------------------------------+
| Scenario                  | Status  | Reason                                              |
+---------------------------+---------+-----------------------------------------------------+
| Baseline_Regression       | PASSED  |                                                     |
| High_Absenteeism_Regression | PASSED  |                                                     |
| Partial_Offline_Regression | FAILED  | avg_employee_assignments: expected=3.2, actual=3.5 |
+---------------------------+---------+-----------------------------------------------------+
```

If you specify an output directory, detailed results will be saved to files in that directory.

## Best Practices

1. **Start with Golden Outputs**: Always generate golden outputs first to establish a baseline.
2. **Include a Baseline Test**: Always include a baseline test with no call-ins or offline employees.
3. **Set Appropriate Thresholds**: Set tight thresholds for critical metrics and looser thresholds for metrics that can vary more.
4. **Run Tests After Changes**: Run regression tests after making changes to scheduling rules to ensure they don't negatively impact scheduling outcomes.
5. **Version Control Golden Outputs**: Keep golden outputs under version control to track changes over time.

## Integration with CI/CD

You can integrate regression testing into your CI/CD pipeline to automatically run tests after changes to scheduling rules. For example, in a GitHub Actions workflow:

```yaml
name: Regression Tests

on:
  push:
    paths:
      - 'domain/rules/**'
      - 'domain/services/schedule_service.py'

jobs:
  regression-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run regression tests
        run: |
          python main.py regression-test --team headsub --tests examples/regression_tests.json --output-dir results
      - name: Upload test results
        uses: actions/upload-artifact@v2
        with:
          name: regression-test-results
          path: results/
```

This will automatically run regression tests whenever changes are made to scheduling rules or the schedule service.