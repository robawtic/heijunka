# Heijunka Project Development Guidelines

This document provides essential information for developers working on the Heijunka project.

## Build/Configuration Instructions

### Dependencies

The project requires the following dependencies:
- ortools (~=9.12.4544) - Google's Operations Research tools for optimization/scheduling
- pyyaml (~=6.0.2) - For YAML configuration file parsing
- sqlalchemy (~=2.0.41) - For database ORM

Install dependencies using:
```bash
pip install -r requirements.txt
```

### Configuration

The project uses a YAML configuration file (`config.yaml`) with the following key settings:
- `periods`: Number of work periods in a day (default: 4)
- `database_url`: Database connection string (default: "sqlite:///schedule.db")
- `max_solve_time`: Maximum time in seconds for the solver (default: 60)
- `start_date`: Start date for scheduling (default: None, uses current date)
- `lookback`: Number of days to look back for history (default: 3)
- `offline_periods`: Dictionary of periods when workstations are offline (default: {})

You can modify these settings in the `config.yaml` file or provide a custom configuration file path when running the application.

The configuration is validated against a schema defined in `utilities/utility.py`. If required fields are missing, default values will be used. If fields have incorrect types, a ValueError will be raised. Unknown fields will generate a warning but won't cause an error.

### Database Setup

The project uses SQLAlchemy with an SQLite database by default. The database schema is managed using Alembic migrations.

To initialize or update the database schema:
```bash
alembic upgrade head
```

To create a new migration after schema changes:
```bash
alembic revision -m "description of changes"
```

### CLI Usage

The application provides a command-line interface for generating schedules. The main script is `main.py` with the following arguments:

- `generate`: Command to generate a schedule
  - `--team`: Team name (required)
  - `--start-date`: Start date for the schedule in YYYY-MM-DD format (default: current date)
  - `--days`: Number of days to schedule (default: 1)
  - `--periods`: Number of periods per day (default: 4)
  - `--call-ins`: List of employees calling in (unavailable)
  - `--offline`: List of employees offline for specific periods in format "employee:periods" (e.g., "John:1,2")
  - `--force-complete`: Flag to force complete the schedule

- `assign`: Command to create a manual assignment
  - `--employee`: Employee name (required)
  - `--workstation`: Workstation name (required)
  - `--date`: Assignment date in YYYY-MM-DD format (default: current date)
  - `--period`: Work period (1-4) (required)
  - `--schedule-id`: Schedule ID (optional)

Example usage:
```bash
python main.py generate --team headsub --days 3 --periods 4
```

For scheduling with a specific start date:
```bash
python main.py generate --team headsub --start-date 2024-08-19 --days 5
```

For scheduling with call-ins:
```bash
python main.py generate --team headsub --days 2 --call-ins "John Doe" "Jane Smith"
```

For scheduling with offline employees:
```bash
python main.py generate --team headsub --days 2 --offline "John:1,2" "Jane:3,4"
```

To force completion of the schedule:
```bash
python main.py generate --team headsub --days 1 --force-complete
```

For manual assignment:
```bash
python main.py assign --employee "John Doe" --workstation "H010" --date 2024-08-19 --period 2
```

## Testing Information

### Testing Framework

The project uses Python's built-in `unittest` framework for testing. Tests are organized in a modular structure:
- Each module has its own `tests` directory (e.g., `rules/tests`, `utilities/tests`)
- Test files follow the naming convention `test_*.py`
- Mock repositories are provided for testing in `domain/repositories/tests/mock_*_repository.py`

### Running Tests

To run all tests:
```bash
python -m unittest discover
```

To run tests for a specific module:
```bash
python -m unittest <module_path>
```

Example:
```bash
python -m unittest rules.tests.test_hard
```

To run a specific test case:
```bash
python -m unittest <module_path>.<TestClass>.<test_method>
```

Example:
```bash
python -m unittest rules.tests.test_hard.TestHardRules.test_forbid_unavailable
```

### Adding New Tests

1. Create a test file in the appropriate `tests` directory following the naming convention `test_*.py`
2. Create a test class that inherits from `unittest.TestCase`
3. Add test methods that start with `test_`
4. Use assertions to verify expected behavior

Example:
```python
import unittest
from unittest.mock import patch, mock_open

from utilities.utility import load_config

class TestUtility(unittest.TestCase):
    def test_load_config(self):
        """Test that load_config correctly loads a YAML file."""
        yaml_content = """
        periods: 4
        database_url: "sqlite:///test.db"
        """

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = load_config("dummy_path.yaml")

        self.assertEqual(config["periods"], 4)
        self.assertEqual(config["database_url"], "sqlite:///test.db")

if __name__ == "__main__":
    unittest.main()
```

## Additional Development Information

### Project Structure

The project follows a domain-driven design approach with the following key components:

- `application/`: Application layer with commands and handlers
  - `commands/`: Command objects and their handlers
  - `queries/`: Query objects and their handlers
  - `services/`: Application-specific services
- `domain/`: Domain layer with entities, repositories, and services
  - `entities/`: Domain entities
  - `repositories/`: Repository interfaces and implementations
  - `rules/`: Business rules for scheduling (planned location, currently in root)
  - `services/`: Domain services including the scheduling service
  - `value_objects/`: Value objects used in the domain
  - `analytics/`: Analytics functionality for generating reports and visualizations
- `infrastructure/`: Infrastructure layer with database and external services
- `presentation/`: Presentation layer
  - `cli/`: Command-line interface
  - `api/`: API endpoints and models
- `rules/`: Business rules for scheduling (should be moved to domain/rules)
- `scheduler/`: Contains an alternative implementation of the scheduling engine (not currently used)
- `utilities/`: Utility functions
- `examples/`: Example scripts demonstrating functionality

### Rules Refactoring Plan

The `rules/` directory should be moved to `domain/rules/` to better align with the domain-driven design approach. Here's a plan for this refactoring:

#### Step 1: Create the new directory structure
```bash
mkdir -p domain/rules/teams
mkdir -p domain/rules/tests
```

#### Step 2: Move the files
```bash
# Move Python files
cp rules/*.py domain/rules/
cp rules/teams/*.py domain/rules/teams/
cp rules/tests/*.py domain/rules/tests/

# Create __init__.py files
touch domain/rules/__init__.py
touch domain/rules/teams/__init__.py
touch domain/rules/tests/__init__.py
```

#### Step 3: Update imports in the moved files
Update all imports in the moved files to use the new package structure:
- Change `from rules.context import ...` to `from domain.rules.context import ...`
- Change `from rules.registry import ...` to `from domain.rules.registry import ...`
- Change `from rules.hard import ...` to `from domain.rules.hard import ...`
- Change `from rules.soft import ...` to `from domain.rules.soft import ...`
- Change `from rules.teams.headsub import ...` to `from domain.rules.teams.headsub import ...`

#### Step 4: Create import redirection in the old location
Create redirection files in the old location to maintain backward compatibility:

```python
# rules/__init__.py
import warnings
warnings.warn("The 'rules' package has moved to 'domain.rules'. Please update your imports.", DeprecationWarning, stacklevel=2)
from domain.rules import *
```

```python
# rules/context.py
import warnings
warnings.warn("'rules.context' has moved to 'domain.rules.context'. Please update your imports.", DeprecationWarning, stacklevel=2)
from domain.rules.context import *
```

Create similar redirection files for registry.py, hard.py, soft.py, and teams/__init__.py.

#### Step 5: Update imports in other files
Update imports in files that use the rules package:
- domain/services/schedule_service.py
- examples/context_demo.py
- scheduler/engine.py

#### Step 6: Test the changes
Run all tests to ensure the refactoring didn't break anything:
```bash
python -m unittest discover
```

#### Step 7: Remove the redirection files (optional)
Once all code has been updated to use the new imports, the redirection files can be removed.

### Scheduling Engine

The scheduling engine uses Google OR-Tools' Constraint Programming (CP) solver to generate optimal schedules based on defined constraints. The key components are:

- `domain/services/schedule_service.py`: Main scheduling algorithm implementation
- `rules/hard.py`: Hard constraints that must be satisfied
- `rules/soft.py`: Soft constraints that should be optimized
- `rules/teams/`: Team-specific rules

Note that there is an alternative implementation in `scheduler/engine.py` that is not currently used by the application.

### Adding New Rules

1. Determine if the rule is a hard constraint (must be satisfied) or a soft constraint (should be optimized)
2. Add the rule to the appropriate module (`rules/hard.py` or `rules/soft.py`)
3. Register the rule in `rules/registry.py` to apply it to specific teams
4. Add tests for the new rule in the corresponding test file

### Analytics

The project includes analytics functionality for generating reports and visualizations:

- `domain/analytics/work_count_report.py`: Generates reports on employee work assignments
- `domain/analytics/heatmap.py`: Creates heatmaps and other visualizations of work data

To run analytics:
```bash
python examples/analytics_demo.py --team <team_name> --advanced
```

This will generate:
1. Work count report (CSV file)
2. Employee-station heatmap (PNG file)
3. ABC combo heatmap (PNG file)
4. Workload balance chart (PNG file)
5. Station rotation effectiveness heatmap (PNG file)
6. Fatigue distribution chart (PNG file)

### Code Style

The project follows standard Python coding conventions:
- Use 4 spaces for indentation
- Follow PEP 8 style guidelines
- Use docstrings for functions, classes, and modules
- Write unit tests for new functionality

### Debugging

For debugging:
1. Enable more detailed logging by modifying the logging level in `utilities/utility.py`
2. Use the debug output in `domain/services/schedule_service.py` to trace the scheduling process
3. For complex scheduling issues, examine the CP model constraints and variables