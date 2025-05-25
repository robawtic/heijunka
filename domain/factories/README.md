# Factory Pattern in Heijunka

This directory contains factory classes for creating domain entities in the Heijunka project. The factory pattern centralizes entity creation logic, enforces validation, and helps maintain domain invariants.

## Overview

The factory pattern is a creational design pattern that provides an interface for creating objects without specifying their concrete classes. In Domain-Driven Design (DDD), factories are used to encapsulate the complex creation logic of domain entities and aggregates.

## Benefits

Implementing the factory pattern in Heijunka provides several benefits:

1. **Centralized Creation Logic**: All entity creation is handled by specialized factory classes, reducing duplication and ensuring consistency.

2. **Enforced Validation**: Factories ensure that all created entities are valid according to domain rules.

3. **Simplified Testing**: It's easier to mock or substitute factories in tests.

4. **Reduced Duplication**: Creation logic is defined once in the factory, not scattered throughout the codebase.

5. **Better Encapsulation**: Domain entities don't need to expose their internal state for creation.

6. **Support for Complex Creation Scenarios**: Factories provide specialized methods for different creation scenarios.

## Factory Classes

### EmployeeFactory

The `EmployeeFactory` class provides methods for creating `Employee` entities:

- `create_employee`: Basic factory method for creating an Employee with essential properties
- `create_employee_with_availability`: Creates an Employee with availability information
- `create_employee_with_workstations`: Creates an Employee with workstation assignments
- `create_employee_with_team_roles`: Creates an Employee with team memberships and roles
- `create_from_model`: Creates an Employee entity from a database model

### WorkstationFactory

The `WorkstationFactory` class provides methods for creating `Workstation` entities:

- `create_workstation`: Basic factory method for creating a Workstation with validation
- `create_loading_workstation`: Creates a Workstation that is a loading job
- `create_heavy_workstation`: Creates a Workstation that is a heavy job
- `create_key_skill_job`: Creates a Workstation that requires a key skill
- `create_from_model`: Creates a Workstation entity from a database model

### TeamFactory

The `TeamFactory` class provides methods for creating `Team` entities:

- `create_team`: Basic factory method for creating a Team with essential properties
- `create_team_with_members`: Creates a Team with pre-defined members
- `create_team_with_workstations`: Creates a Team with pre-defined workstations
- `create_from_model`: Creates a Team entity from a database model

### ScheduleFactory

The `ScheduleFactory` class provides methods for creating `Schedule` entities:

- `create_schedule`: Basic factory method for creating a Schedule with essential properties
- `create_daily_schedule`: Creates a Schedule for a single day
- `create_schedule_with_assignments`: Creates a Schedule with pre-defined assignments
- `create_from_model`: Creates a Schedule entity from a database model

### AssignmentFactory

The `AssignmentFactory` class provides methods for creating `WorkAssignment` value objects:

- `create_assignment`: Basic factory method for creating a WorkAssignment with validation
- `create_assignment_for_date`: Creates a WorkAssignment for a specific date and period number
- `create_assignment_if_qualified`: Creates a WorkAssignment only if the employee is qualified

## Usage

### Basic Usage

```python
from domain.factories.employee_factory import EmployeeFactory
from domain.factories.workstation_factory import WorkstationFactory
from domain.factories.team_factory import TeamFactory
from domain.factories.schedule_factory import ScheduleFactory
from domain.factories.assignment_factory import AssignmentFactory

# Create an employee
employee = EmployeeFactory.create_employee(
    name="John Doe",
    team_id=1,
    roles=["Associate"],
    qualifications=["H010", "H080/H090"]
)

# Create a workstation
workstation = WorkstationFactory.create_workstation(
    name="H010",
    line_type="Sub-Assembly",
    is_loading_job=True,
    team_id=1
)

# Create a team
team = TeamFactory.create_team(
    name="Example Team",
    description="A team created using TeamFactory"
)

# Create a schedule
schedule = ScheduleFactory.create_schedule(
    team_id=1,
    start_date=date.today(),
    periods_per_day=4,
    status="pending"
)

# Create an assignment
assignment = AssignmentFactory.create_assignment(
    employee=employee,
    workstation=workstation,
    period=SchedulePeriod(date=date.today(), period=1)
)
```

### Using with Repositories

The factory classes are used in repository implementations to convert database models to domain entities:

```python
def _to_domain(self, model: TeamModel) -> Team:
    """Convert a TeamModel to a Team domain entity using factory."""
    from domain.factories.team_factory import TeamFactory
    return TeamFactory.create_from_model(model)
```

## Examples

For more examples of using the factory pattern, see the `examples/factory_examples.py` file.

## Testing

The factories include unit tests to verify their functionality. Run the tests with:

```bash
python -m unittest domain.factories.tests.test_team_factory
python -m unittest domain.factories.tests.test_schedule_factory
python -m unittest domain.factories.tests.test_assignment_factory
```