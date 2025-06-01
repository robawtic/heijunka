# Heijunka Seeding System

This directory contains the new seeding system for the Heijunka project. The system provides a more detailed and realistic seeding mechanism, with a focus on the Powertrain department.

## Directory Structure

The seeding system uses a directory structure that mirrors the organizational hierarchy:
The following is in infrastrcture/seeding/seed_data/
```
seed_data/
├── seed_manager.py                # Main script for seeding the database
├── powertrain_seed.py             # Script for seeding Powertrain department data
├── MIGRATION_PLAN.md              # Instructions for migrating from the old seeding mechanism
├── groups/                        # Groups within departments
│   └── shortblock/                # Shortblock group
│       └── teams/                 # Teams within the Shortblock group
│           ├── shortblock/        # Shortblock team
│           │   ├── README.md      # Documentation for the Shortblock team
│           │   ├── workstations.json  # Workstation data for the Shortblock team
│           │   └── employees.json # Employee data for the Shortblock team
│           ├── headsub/           # Headsub team
│           │   ├── README.md      # Documentation for the Headsub team
│           │   ├── workstations.json  # Workstation data for the Headsub team
│           │   └── employees.json # Employee data for the Headsub team
│           └── camsub/            # Camsub team
│               ├── README.md      # Documentation for the Camsub team
│               ├── workstations.json  # Workstation data for the Camsub team
│               └── employees.json # Employee data for the Camsub team
```

## File Formats

### workstations.json

This file contains data about the workstations for a team. Each workstation has the following properties:

- `name`: The name of the workstation
- `line_type`: The type of line (e.g., "Sub-Assembly", "Mainline")
- `is_loading_job`: Whether the workstation is a loading job
- `is_heavy_job`: Whether the workstation is a heavy job
- `is_key_skill_job`: Whether the workstation requires a key skill
- `description`: A description of the workstation
- `cycle_time_minutes`: The cycle time in minutes
- `required_tools`: A list of tools required for the workstation
- `safety_equipment`: A list of safety equipment required for the workstation

Additional properties may be included for specific workstations, such as:

- `certification_required`: Whether certification is required for the workstation
- `training_hours_required`: The number of training hours required for certification
- `precision_requirement`: The precision requirement for the workstation
- `quality_checks`: A list of quality checks performed at the workstation

### employees.json

This file contains data about the employees for a team. Each employee has the following properties:

- `name`: The name of the employee
- `role`: The role of the employee (e.g., "Team Leader", "Backup", "Associate")
- `is_active`: Whether the employee is active
- `known_stations`: A list of workstation names that the employee knows
- `hire_date`: The date the employee was hired
- `skills`: A dictionary of skills and their levels (e.g., "leadership": "High")
- `availability_pattern`: A dictionary containing availability information:
  - `regular_days_off`: A list of days the employee is regularly off
  - `vacation_days`: A list of dates the employee is on vacation
  - `training_days`: A list of dates the employee is in training

Additional properties may be included for specific employees, such as:

- `is_trainer`: Whether the employee is a trainer
- `certifications`: A list of certifications the employee has
- `training_progress`: A dictionary of workstations and training progress
- `notes`: Additional notes about the employee

## Usage

### Seeding the Database

To seed the database with the new seeding mechanism, use the `seed_manager.py` script:

```bash
python infrastrcture/seeding/seed_data/seed_manager.py --department powertrain --reset-db
```

This will seed the database with Powertrain department data, including the Shortblock group and its teams.

### Generating Historical Data

To generate historical data using the new seeding mechanism, use the `generate_historical_data.py` script with the `--seed` flag:

```bash
python generate_historical_data.py --team headsub --seed --department powertrain --reset-db
```

This will seed the database with Powertrain department data and then generate historical data for the Headsub team.

## Extending the System

### Adding New Teams

To add a new team:

1. Create a new directory for the team under the appropriate group
2. Create a README.md file documenting the team
3. Create a workstations.json file with the team's workstations
4. Create an employees.json file with the team's employees

### Adding New Departments

To add a new department:

1. Create a new script for seeding the department (e.g., `trim_seed.py`)
2. Create a directory structure for the department's groups and teams
3. Update the `seed_manager.py` script to include the new department

## Migration

For instructions on migrating from the old seeding mechanism to the new one, see the [MIGRATION_PLAN.md](MIGRATION_PLAN.md) file.