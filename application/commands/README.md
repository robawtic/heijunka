# Heijunka Seeding System

This document provides an overview of the Heijunka seeding system, which is used to populate the database with initial data for testing and development.

## Architecture

The seeding system follows Domain-Driven Design (DDD) principles, with a clear separation of concerns:

### Domain Layer

- **Entities and Value Objects**: The `domain/entities/seed_data.py` file defines value objects for seed data, including `WorkstationSeedData`, `EmployeeSeedData`, `TeamSeedData`, `GroupSeedData`, and `DepartmentSeedData`.

- **Repository Interfaces**: The `domain/repositories/interfaces/seed_data_repository.py` file defines the `SeedDataRepositoryInterface`, which provides methods for loading seed data from files.

- **Services**: The `domain/services/seed_service.py` file defines the `SeedService`, which uses repositories to seed the database with initial data.

### Application Layer

- **Commands**: The `application/commands/seed_database_command.py` file defines the `SeedDatabaseCommand`, which represents the intent to seed the database.

- **Command Handlers**: The `application/commands/seed_database_handler.py` file defines the `SeedDatabaseHandler`, which handles the `SeedDatabaseCommand` and uses the `SeedService` to seed the database.

### Infrastructure Layer

- **Repository Implementations**: The `domain/repositories/implementations/file_seed_data_repository.py` file defines the `FileSeedDataRepository`, which implements the `SeedDataRepositoryInterface` and loads seed data from files.

### Presentation Layer

- **CLI**: The `presentation/cli/seed_cli.py` file provides a command-line interface for seeding the database.

## Design Principles

The seeding system follows these design principles:

1. **Separation of Concerns**: Each component has a single responsibility and is isolated from other components.

2. **Dependency Injection**: Dependencies are injected into components rather than being created directly, making the system more testable and flexible.

3. **Repository Pattern**: Data access is abstracted behind repository interfaces, allowing for different implementations (e.g., file-based, database-based).

4. **Command-Query Separation**: Commands (which modify state) are separated from queries (which return data).

5. **Domain-Driven Design**: The system is designed around the domain model, with a clear separation between domain, application, infrastructure, and presentation layers.

## Usage

### Command-Line Interface

The seeding system provides a command-line interface for seeding the database:

```bash
python -m presentation.cli.seed_cli [options]
```

Options:
- `--department DEPARTMENT`: Seed a specific department
- `--group GROUP`: Seed a specific group
- `--team TEAM`: Seed a specific team
- `--all`: Seed all departments
- `--reset-db`: Reset the database before seeding
- `--base-path BASE_PATH`: Base path for seed data files (default: infrastructure/seeding/seed_data)

### Programmatic Usage

The seeding system can also be used programmatically:

```python
from application.commands.seed_database_command import SeedDatabaseCommand
from application.commands.seed_database_handler import SeedDatabaseHandler
from domain.repositories.implementations.file_seed_data_repository import FileSeedDataRepository
from domain.repositories.implementations.sqlalchemy_department_repository import SqlAlchemyDepartmentRepository
from domain.repositories.implementations.sqlalchemy_group_repository import SqlAlchemyGroupRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_role_repository import SqlAlchemyRoleRepository
from domain.repositories.implementations.sqlalchemy_line_type_repository import SqlAlchemyLineTypeRepository
from domain.models.db import Session

# Create session
session = Session()

# Create repositories
seed_data_repository = FileSeedDataRepository()
department_repository = SqlAlchemyDepartmentRepository(session)
group_repository = SqlAlchemyGroupRepository(session)
team_repository = SqlAlchemyTeamRepository(session)
workstation_repository = SqlAlchemyWorkstationRepository(session)
employee_repository = SqlAlchemyEmployeeRepository(session)
role_repository = SqlAlchemyRoleRepository(session)
line_type_repository = SqlAlchemyLineTypeRepository(session)

# Create handler
handler = SeedDatabaseHandler(
    seed_data_repository=seed_data_repository,
    department_repository=department_repository,
    group_repository=group_repository,
    team_repository=team_repository,
    workstation_repository=workstation_repository,
    employee_repository=employee_repository,
    role_repository=role_repository,
    line_type_repository=line_type_repository,
    session=session
)

# Create command
command = SeedDatabaseCommand(
    department="powertrain",
    reset_database=True
)

# Handle command
result = handler.handle(command)

# Check result
if result["status"] == "success":
    print("Seeding successful!")
else:
    print(f"Seeding failed: {result['message']}")

# Close session
session.close()
```

## Seed Data Format

The seeding system expects seed data to be organized in a specific directory structure:

```
infrastructure/seeding/seed_data/
├── departments/
│   └── powertrain/
│       ├── groups/
│       │   └── shortblock/
│       │       ├── teams/
│       │       │   ├── shortblock/
│       │       │   │   ├── workstations.json
│       │       │   │   └── employees.json
│       │       │   ├── headsub/
│       │       │   │   ├── workstations.json
│       │       │   │   └── employees.json
│       │       │   └── camsub/
│       │       │       ├── workstations.json
│       │       │       └── employees.json
```

### workstations.json

The `workstations.json` file contains data about the workstations for a team:

```json
{
  "workstations": [
    {
      "name": "SB010",
      "line_type": "Sub-Assembly",
      "is_loading_job": true,
      "is_heavy_job": true,
      "is_key_skill_job": false,
      "description": "Initial block preparation and component loading",
      "cycle_time_minutes": 15,
      "required_tools": ["Engine block fixture", "Hoist", "Cleaning tools"],
      "safety_equipment": ["Gloves", "Safety glasses", "Steel-toed boots", "Back brace"]
    },
    ...
  ]
}
```

### employees.json

The `employees.json` file contains data about the employees for a team:

```json
{
  "employees": [
    {
      "name": "Michael",
      "role": "Team Leader",
      "is_active": true,
      "known_stations": ["SB010", "SB020", "SB030"],
      "hire_date": "2019-08-15",
      "skills": {
        "leadership": "High",
        "technical": "High",
        "problem_solving": "High"
      },
      "availability_pattern": {
        "regular_days_off": ["Saturday", "Sunday"],
        "vacation_days": ["2024-06-10", "2024-06-11", "2024-06-12", "2024-06-13", "2024-06-14"],
        "training_days": ["2024-07-25"]
      }
    },
    ...
  ]
}
```

## Extending the System

### Adding New Seed Data

To add new seed data:

1. Create the appropriate directory structure for the department, group, and team.
2. Create `workstations.json` and `employees.json` files for each team.
3. Run the seeding system to seed the database with the new data.

### Adding New Repository Implementations

To add a new repository implementation:

1. Create a new class that implements the `SeedDataRepositoryInterface`.
2. Implement all the required methods to load seed data from your data source.
3. Update the `setup_dependencies` function in `seed_cli.py` to use your new repository implementation.

### Adding New Commands and Handlers

To add new commands and handlers:

1. Create a new command class in the `application/commands` directory.
2. Create a new handler class in the `application/commands` directory.
3. Update the `seed_cli.py` file to use your new command and handler.

## Refactoring Existing Seed Data

The `utilities/refactor_seed_data.py` script can be used to refactor existing seed data from the old structure to the new structure:

```bash
python -m utilities.refactor_seed_data --source infrastructure/seeding/seed_data --destination infrastructure/seeding/seed_data_new
```

This script will:
1. Create the new directory structure
2. Copy the existing files to the new structure
3. Preserve the JSON data in the new structure
