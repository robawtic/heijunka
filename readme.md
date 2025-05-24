
# Heijunka Project Documentation

## Overview

Heijunka is a sophisticated scheduling system designed to optimize workforce allocation across workstations. The name "Heijunka" comes from lean manufacturing principles and refers to production leveling or smoothing. This system uses constraint programming to generate optimal schedules based on various constraints and optimization criteria.

## Core Functionality

### Scheduling Engine

The heart of Heijunka is its scheduling engine, which uses Google's OR-Tools Constraint Programming solver to generate optimal schedules. The engine:

1. Takes into account employee qualifications and availability
2. Respects workstation requirements
3. Applies team-specific rules and constraints
4. Optimizes for fairness, rotation, and workload balance
5. Handles special cases like call-ins and offline periods

### Rule-Based Constraints

The scheduling system uses a flexible rule-based approach to define constraints:

- **Hard Constraints**: Must be satisfied for a valid schedule (e.g., employee qualifications, availability)
- **Soft Constraints**: Preferences that should be optimized (e.g., rotation, workload balance)
- **Team-Specific Rules**: Custom rules that apply to specific teams

### Analytics

The system includes analytics capabilities to evaluate schedule quality and track metrics over time:

- Employee-station assignment heatmaps
- Workload balance tracking
- Station rotation effectiveness
- Fatigue analysis
- Historical fairness metrics

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/heijunka.git
   cd heijunka
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```bash
   python -m alembic upgrade head
   ```

## Configuration

The system uses a YAML configuration file (`config.yaml`) with the following settings:

```yaml
periods: 4                           # Number of work periods in a day
database_url: "sqlite:///schedule.db" # Database connection string
max_solve_time: 60                   # Maximum time in seconds for the solver
start_date: null                     # Start date for scheduling (default: current date)
lookback: 3                          # Number of days to look back for history
offline_periods: {}                  # Dictionary of periods when workstations are offline
```

## Usage

### Command Line Interface

#### Generate a Schedule

```bash
python main.py generate --team <team_name> --periods <periods_per_day> [options]
```

Options:
- `--team`: Team name (required)
- `--start-date`: Start date for the schedule (YYYY-MM-DD)
- `--periods`: Number of periods per day (default: 4)
- `--call-ins`: List of employees calling in (unavailable)
- `--offline`: List of employees offline for specific periods in format "employee:periods" (e.g., "John:1,2")
- `--force-complete`: Force complete the schedule even if some constraints cannot be satisfied

Example:
```bash
python main.py generate --team headsub --periods 4 --start-date 2024-08-19
```

#### Create a Manual Assignment

```bash
python main.py assign --employee <employee_name> --workstation <workstation_name> --date <date> --period <period>
```

Options:
- `--employee`: Employee name (required)
- `--workstation`: Workstation name (required)
- `--date`: Assignment date (YYYY-MM-DD)
- `--period`: Work period (1-4) (required)
- `--schedule-id`: Schedule ID (optional)

Example:
```bash
python main.py assign --employee "John Doe" --workstation "Station A" --date 2024-08-19 --period 2
```

### Generate Historical Data

To generate historical data for testing and analytics:

```bash
python generate_historical_data.py --team <team_name> --days <num_days> [options]
```

Options:
- `--team`: Team name (required)
- `--days`: Number of business days to generate (default: 300)
- `--batch-size`: Number of days to process in each batch (default: 1)
- `--periods`: Number of periods per day (default: 4)
- `--saturday-percent`: Percentage of Saturdays to include (default: 0.1)
- `--force-complete`: Force complete the schedule
- `--dry-run`: Print commands but do not execute them

Example:
```bash
python generate_historical_data.py --team headsub --days 60 --batch-size 5
```

### Analytics

To generate analytics reports and visualizations:

```bash
python examples/analytics_demo.py [options]
```

Options:
- `--team`: Name of the team to analyze (default: all teams)
- `--output-dir`: Directory to save output files
- `--year`: Year to analyze for time-based visualizations
- `--advanced`: Generate advanced analytics visualizations

Example:
```bash
python examples/analytics_demo.py --team headsub --advanced
```

## API

Heijunka provides a RESTful API for integration with other systems.

### Starting the API Server

```bash
python main_api.py
```

The API server runs on port 8889 by default, which can be changed using the PORT environment variable.

### API Endpoints

#### Authentication

- `POST /auth/token`: Obtain an access token
- `GET /auth/me`: Get current user information

#### Schedules

- `POST /schedules`: Create a new schedule
- `GET /schedules/{schedule_id}`: Get a specific schedule
- `GET /schedules`: List schedules with filtering and pagination
- `GET /schedules/task/{task_id}`: Get a schedule by task ID
- `POST /schedules/assignments`: Create a manual assignment

#### Teams

- `GET /teams`: List all teams
- `GET /teams/{team_id}`: Get a specific team
- `POST /teams`: Create a new team
- `PUT /teams/{team_id}`: Update a team
- `DELETE /teams/{team_id}`: Delete a team

#### Employees

- `GET /employees`: List all employees
- `GET /employees/{employee_id}`: Get a specific employee
- `POST /employees`: Create a new employee
- `PUT /employees/{employee_id}`: Update an employee
- `DELETE /employees/{employee_id}`: Delete an employee

#### Workstations

- `GET /workstations`: List all workstations
- `GET /workstations/{workstation_id}`: Get a specific workstation
- `POST /workstations`: Create a new workstation
- `PUT /workstations/{workstation_id}`: Update a workstation
- `DELETE /workstations/{workstation_id}`: Delete a workstation

#### Assignments

- `GET /assignments`: List assignments with filtering and pagination
- `GET /assignments/{assignment_id}`: Get a specific assignment

#### Status

- `GET /status/health`: Check API health
- `GET /status/metrics`: Get system metrics

## Architecture

Heijunka follows a domain-driven design approach with the following components:

### Application Layer

Contains application-specific logic, commands, and handlers:
- `application/commands`: Command objects and handlers
- `application/queries`: Query objects and handlers
- `application/services`: Application services

### Domain Layer

Contains the core business logic:
- `domain/entities`: Domain entities (Employee, Workstation, etc.)
- `domain/repositories`: Repository interfaces
- `domain/services`: Domain services (ScheduleService)
- `domain/value_objects`: Value objects (SchedulePeriod, WorkAssignment)
- `domain/events`: Domain events
- `domain/analytics`: Analytics functionality

### Infrastructure Layer

Contains implementation details:
- `infrastructure/api`: API-related code
- `infrastructure/cache`: Caching implementation
- `infrastructure/config`: Configuration
- `infrastructure/exceptions`: Exception handling
- `infrastructure/logging`: Logging configuration
- `infrastructure/monitoring`: Monitoring and metrics
- `infrastructure/tasks`: Background task management

### Presentation Layer

Contains user interfaces:
- `presentation/api`: API endpoints and models
- `presentation/cli`: Command-line interface

### Rules

Contains scheduling rules and constraints:
- `rules/hard.py`: Hard constraints
- `rules/soft.py`: Soft constraints
- `rules/teams/`: Team-specific rules
- `rules/registry.py`: Rule registry

## Extending the System

### Adding New Rules

1. Determine if the rule is a hard constraint or soft constraint
2. Add the rule to the appropriate module (`rules/hard.py` or `rules/soft.py`)
3. Register the rule in `rules/registry.py`
4. Add tests for the new rule

### Adding Team-Specific Rules

1. Create a new module in `rules/teams/` (e.g., `rules/teams/newteam.py`)
2. Define team-specific rules in the module
3. Create a list of rules named `NEWTEAM_RULES`
4. The rules will be automatically discovered and applied

### Adding New Analytics

1. Add new analytics functions to `domain/analytics/`
2. Update the analytics demo script to include the new functions

## Troubleshooting

### Common Issues

1. **No solution found**: This can happen if the constraints are too strict. Try using `--force-complete` to relax some constraints.

2. **Database errors**: Ensure the database is properly initialized with `alembic upgrade head`.

3. **Missing dependencies**: Make sure all dependencies are installed with `pip install -r requirements.txt`.

4. **API authentication issues**: Check that you're providing valid credentials and that the token hasn't expired.

### Debugging

For more detailed logging, modify the logging level in `infrastructure/logging/config.py`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for your changes
5. Submit a pull request

## License

[Specify the license here]