# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Environment Setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac  
source .venv/bin/activate

pip install -r requirements.txt
python -m alembic upgrade head  # Initialize database
```

### Running the Application
```bash
# CLI Interface
python main.py generate --team <team_name> [--periods <n>] [options]
python main.py assign --employee <name> --workstation <name> --date <YYYY-MM-DD> --period <n>

# API Server
python main_api.py  # Starts on port 8889 (configurable via PORT env var)

# Generate Historical Data
python generate_historical_data.py --team <team_name> --days <n>

# Analytics
python examples/analytics_demo.py --team <team_name> [--advanced]
```

### Testing
```bash
# Run tests using unittest (pytest not available)
python -m unittest discover tests/
python -m unittest tests.domain.services.test_regression_test_service
python -m unittest tests.integration.test_team_model
```

### Database Management
```bash
python -m alembic upgrade head  # Apply migrations
python infrastructure/database/init_db.py  # Initialize database
```

## Architecture Overview

### Domain-Driven Design Structure
Heijunka uses a domain-driven design (DDD) approach with bounded contexts:

**Bounded Contexts:**
- `domain/contexts/assignment/` - Work assignment and optimization logic
- `domain/contexts/employee_management/` - Employee, team, department management  
- `domain/contexts/scheduling/` - Schedule generation and management
- `domain/contexts/user_management/` - User authentication and API keys
- `domain/contexts/workstation_management/` - Workstation and line type management

**Layer Structure:**
- `application/` - CQRS command/query handlers, DTOs, application services
- `domain/` - Core business logic, entities, value objects, domain services
- `infrastructure/` - Database repositories, external integrations, config
- `presentation/` - API endpoints (`presentation/api/`) and CLI (`presentation/cli/`)

### Key Components

**Constraint Programming Engine:**
- Uses Google OR-Tools for optimization
- Core logic in `domain/services/cp_model_builder.py`
- Rule system in `domain/rules/` with hard/soft constraints

**Repository Pattern:**
- Interface definitions in `domain/contexts/*/repositories/interfaces/`
- SQLAlchemy implementations in `infrastructure/repositories/*/`
- Mock implementations for testing in `domain/repositories/tests/`

**Factory Pattern:**
- Entity factories in `domain/factories/` for consistent object creation
- Seed data factories for test data generation

**Event System:**
- Domain events in `domain/events/`
- Event publishing for loose coupling between contexts

### Data Models
- SQLAlchemy models in `domain/models/`
- Database schema managed via Alembic migrations
- Seed data system in `infrastructure/seeding/seed_data/`

### Configuration
- Main config in `config.yaml`
- Environment-specific settings in `infrastructure/config/settings.py`
- Database URL, JWT secrets, and other sensitive config via environment variables

### Testing Strategy
- Unit tests using Python's unittest framework
- Mock repositories for domain testing
- Integration tests for full workflow validation
- Test structure mirrors source code organization

### Team-Specific Rules
- Team rules in `domain/rules/teams/` (e.g., `headsub.py`)
- Rule registry system for dynamic constraint loading
- Extensible constraint framework for new business rules

### API Security
- JWT-based authentication
- API key management system
- CSRF protection and rate limiting
- Input sanitization and validation

## Development Guidelines

### Adding New Features
1. Start with domain entities and value objects in appropriate bounded context
2. Create repository interfaces and implementations
3. Add domain services for business logic
4. Implement application layer commands/queries using CQRS
5. Add presentation layer endpoints or CLI commands
6. Write tests for all layers

### Database Changes
1. Create Alembic migration: `alembic revision --autogenerate -m "description"`
2. Review generated migration before applying
3. Update seed data if needed
4. Test migration rollback capability

### Adding New Teams/Rules
1. Create team-specific rule file in `domain/rules/teams/`
2. Register rules in `domain/rules/registry.py`
3. Add team configuration to seed data
4. Update analytics and reporting as needed

### Troubleshooting
- Check logs in `logs/` directory for application and audit logs
- Use `--force-complete` flag to relax constraints if scheduling fails
- Verify database schema with `python infrastructure/database/check_schema.py`
- Environment validation runs automatically on startup