# Heijunka Analytics

This directory contains analytics functionality for the Heijunka application.

## Overview

The analytics module provides tools for analyzing employee work history data and generating reports and visualizations. It includes:

1. Work Count Reports - Shows how many times each employee worked at each station and period
2. Heatmap Visualizations - Visual representations of employee-station assignments and work patterns

## Usage

### Work Count Report

The work count report shows how many times each employee worked at each station and period. It also includes totals for each employee.

```python
from domain.models.db import Session
from domain.analytics.work_count_report import generate_work_count_report

# Create a database session
session = Session()

# Generate the report
df = generate_work_count_report(session)

# Print the report
print(df)

# Save the report to a CSV file
df.to_csv('work_count_report.csv', index=False)
```

### Heatmaps

The heatmap functionality generates two visualizations:

1. Employee-Station Heatmap - Shows the total number of assignments for each employee-station pair
2. ABC Combo Heatmap - Shows the number of days each employee worked a combination of stations from groups A, B, and C

```python
from domain.models.db import Session
from domain.analytics.heatmap import generate_heatmaps

# Create a database session
session = Session()

# Generate the heatmaps
employee_station_path, abc_combo_path = generate_heatmaps(output_dir='.', session=session)
```

For more advanced usage, you can use the `WorkloadAnalysis` class directly:

```python
from domain.models.db import Session
from domain.analytics.heatmap import WorkloadAnalysis

# Create a database session
session = Session()

# Create a workload analysis instance
wa = WorkloadAnalysis(session)

# Get the employee-station-period matrix
df_mat = wa.get_employee_station_period_matrix()

# Generate heatmaps with custom station sets
wa.generate_heatmaps(
    output_dir='./output',
    setA={'H010'},
    setB={'M050', 'M090'},
    setC={'H170', 'BW010'}
)
```

## Example Script

An example script is provided in the `examples` directory to demonstrate the analytics functionality:

```bash
python examples/analytics_demo.py --output-dir ./output
```

This script generates a work count report and heatmaps, and saves them to the specified output directory.

### Database Initialization

The analytics functionality requires the following database tables to exist:
- `employees` - Employee information
- `workstations` - Workstation information
- `employee_work_history` - Work history records

The example script `analytics_demo.py` will automatically check if these tables exist and create them if necessary. If you're using the analytics functionality in your own code, you should either:

1. Run `create.py` first to initialize the database schema, or
2. Add code to check and create the required tables:

```python
from sqlalchemy import inspect
from domain.models.db import engine
from domain.models.Base import Base

def ensure_tables_exist():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    required_tables = ['employee_work_history', 'employees', 'workstations']
    missing_tables = [table for table in required_tables if table not in existing_tables]

    if missing_tables:
        print(f"Creating required tables: {', '.join(missing_tables)}")
        Base.metadata.create_all(engine)
```

## Dependencies

The analytics functionality requires the following dependencies:

- pandas - For data manipulation and analysis
- matplotlib - For generating visualizations
- numpy - For numerical operations

These dependencies should be included in the project's requirements.txt file.
