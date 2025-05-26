# Scenario-Based Simulations for the Scheduling System

This document explains how to use the scenario-based simulation feature of the Heijunka scheduling system.

## Overview

The simulation feature allows you to test different scheduling parameters and compare the results. This is useful for:

- Testing the impact of employee absences
- Evaluating different scheduling strategies
- Preparing for anticipated staffing challenges
- Optimizing workload distribution

## Running Simulations

To run a simulation, use the `simulate` command with the following parameters:

```bash
python main.py simulate --team <team_name> --scenarios <scenarios_file> [--start-date <YYYY-MM-DD>] [--periods <num_periods>] [--output-dir <output_directory>] [--advanced]
```

### Parameters

- `--team`: (Required) The name of the team to simulate
- `--scenarios`: (Required) Path to a JSON file containing scenario definitions
- `--start-date`: (Optional) Start date for the schedule in YYYY-MM-DD format (default: current date)
- `--periods`: (Optional) Number of periods per day (default: 4)
- `--output-dir`: (Optional) Directory to save output files (default: current directory)
- `--advanced`: (Optional) Generate advanced analytics visualizations

### Example

```bash
python main.py simulate --team headsub --scenarios examples/scenarios.json --start-date 2024-08-19 --output-dir results
```

## Scenario Definition

Scenarios are defined in a JSON file. Each scenario includes:

- `name`: Name of the scenario
- `call_ins`: List of employees who are calling in (unavailable)
- `offline`: List of employees offline for specific periods in format "employee:periods" (e.g., "John:1,2")
- `force_complete`: Whether to force completion of the schedule
- `metadata`: Additional scenario-specific data (optional)

### Example Scenario File

```json
[
  {
    "name": "Baseline",
    "call_ins": [],
    "offline": [],
    "force_complete": false,
    "metadata": {
      "description": "Baseline scenario with no call-ins or offline employees"
    }
  },
  {
    "name": "High_Absenteeism",
    "call_ins": ["John Doe", "Jane Smith"],
    "offline": [],
    "force_complete": true,
    "metadata": {
      "description": "Scenario with high absenteeism (2 employees calling in)"
    }
  }
]
```

## Output

The simulation command generates the following outputs:

1. **Comparison Report**: A CSV file comparing key metrics across scenarios
2. **Employee Workload Chart**: A bar chart comparing employee workload across scenarios
3. **Workstation Utilization Chart**: A bar chart comparing workstation utilization across scenarios
4. **Total Assignments Chart**: A bar chart comparing total assignments across scenarios
5. **Scenario Metrics Heatmap**: A heatmap comparing key metrics across scenarios

### Metrics

The comparison report includes the following metrics:

- Total Assignments: Total number of assignments generated
- Min/Max/Avg Employee Assignments: Minimum, maximum, and average number of assignments per employee
- Employee Assignment Std Dev: Standard deviation of assignments per employee
- Min/Max/Avg Workstation Utilization: Minimum, maximum, and average utilization of workstations

## Interpreting Results

When comparing scenarios, look for:

1. **Workload Balance**: Compare the standard deviation of employee assignments across scenarios
2. **Coverage**: Compare the total assignments and workstation utilization
3. **Resilience**: Compare how well the schedule handles call-ins and offline employees

The baseline scenario provides a reference point for comparing other scenarios.

## Advanced Usage

### Custom Metrics

You can add custom metrics to the scenario metadata to track scenario-specific information:

```json
{
  "name": "Custom_Scenario",
  "call_ins": ["John Doe"],
  "offline": ["Jane Smith:1,2"],
  "force_complete": true,
  "metadata": {
    "description": "Custom scenario with specific metrics",
    "expected_coverage": 0.85,
    "priority_stations_covered": true
  }
}
```

### Advanced Analytics

When using the `--advanced` flag, the simulation command generates additional visualizations:

1. **Workload Distribution Chart**: Shows the distribution of workload across employees for each scenario using violin plots
2. **Station Rotation Heatmap**: Shows how many different stations each employee works at in each scenario
3. **Fatigue Distribution Chart**: Shows the distribution of consecutive assignments to the same station

Example:

```bash
python main.py simulate --team headsub --scenarios examples/scenarios.json --advanced --output-dir results
```

### Integration with Analytics

The simulation results can be further analyzed programmatically using the analytics framework:

```python
from domain.analytics.scenario_analytics import ScenarioAnalytics
from domain.services.scenario_comparator import ScenarioComparator

# Create a scenario analytics instance
analytics = ScenarioAnalytics(results, session=session)

# Generate all advanced analytics
analytics.generate_advanced_analytics("output_dir")

# Generate specific analytics
analytics._generate_workload_distribution_chart("output_dir")
analytics._generate_station_rotation_heatmap("output_dir")
analytics._generate_fatigue_distribution_chart("output_dir")
```
