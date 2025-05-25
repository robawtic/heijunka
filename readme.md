# Heijunka

> **Production-Level Workforce Scheduling with Constraint Programming**

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](LICENSE)](./LICENSE)

---

**Heijunka** is a workforce scheduling system inspired by lean manufacturing principles, leveraging Google's OR-Tools for constraint-based optimization. It balances fairness, rotation, and workload while supporting advanced analytics and extensibility.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API](#api)
- [Architecture](#architecture)
- [Extending Heijunka](#extending-heijunka)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- 🔢 **Constraint Scheduling**: Employee qualifications, availability, team rules, fairness, and workload balance
- 🧑‍🤝‍🧑 **Rule-based Constraints**: Hard/soft constraints and team-specific rules
- 📊 **Analytics**: Heatmaps, rotation tracking, fatigue analysis, fairness metrics
- 🚀 **RESTful API**: For integrations and programmatic scheduling
- 🔌 **Extensible**: Easily add new rules, analytics, or teams

---

## Installation

### Prerequisites

- Python 3.8+
- pip

### Quickstart

```bash
git clone https://github.com/robawtic/heijunka.git
cd heijunka

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
python -m alembic upgrade head  # Initialize database
```

---

## Configuration

Configure `config.yaml`:

```yaml
periods: 4
database_url: "sqlite:///schedule.db"
max_solve_time: 60
start_date: null
lookback: 3
offline_periods: {}
```

---

## Usage

### CLI: Generate Schedules

```bash
python main.py generate --team <team_name> [--periods <n>] [options]
```

- `--team`: Team name (required)
- `--start-date`: (YYYY-MM-DD)
- `--call-ins`: Unavailable employees
- `--offline`: "employee:periods" (e.g., "John:1,2")
- `--force-complete`: Relax constraints if needed

#### Example

```bash
python main.py generate --team headsub --periods 4 --start-date 2024-08-19
```

### CLI: Manual Assignment

```bash
python main.py assign --employee <name> --workstation <name> --date <YYYY-MM-DD> --period <n>
```

### CLI: Generate Historical Data

```bash
python generate_historical_data.py --team <team_name> --days <n>
```

### Analytics

```bash
python examples/analytics_demo.py --team <team_name> [--advanced]
```

---

## API

Start with:

```bash
python main_api.py
```

Default port: `8889` (change with `PORT` env variable)

### Endpoints

- **Auth**: `POST /auth/token`, `GET /auth/me`
- **Schedules**: `POST /schedules`, `GET /schedules/{id}`, `GET /schedules`
- **Teams**: `GET/POST/PUT/DELETE /teams`
- **Employees**: `GET/POST/PUT/DELETE /employees`
- **Workstations**: `GET/POST/PUT/DELETE /workstations`
- **Assignments**: `GET /assignments`, `GET /assignments/{id}`
- **Status**: `GET /status/health`, `GET /status/metrics`

---

## Architecture

Heijunka uses a domain-driven design:

- **Application**: Commands, queries, and services
- **Domain**: Core logic (entities, services, analytics)
- **Infrastructure**: API, config, logging, monitoring, background tasks
- **Presentation**: API endpoints, CLI
- **Rules**: Hard/soft constraints, team-specific rules

---

## Extending Heijunka

- **Add Rules**: `rules/hard.py` or `rules/soft.py`, register in `rules/registry.py`, add tests
- **Add Team Rules**: New file in `rules/teams/`, define list `NEWTEAM_RULES`
- **Add Analytics**: Extend `domain/analytics/`, update analytics scripts

---

## Troubleshooting

- **No solution found**: Use `--force-complete` to relax constraints
- **DB errors**: Run `alembic upgrade head`
- **Missing deps**: `pip install -r requirements.txt`
- **API/auth**: Check credentials/token validity

Increase log verbosity in `infrastructure/logging/config.py` for debugging.

---

## Contributing

1. Fork, branch, and code
2. Add tests
3. Submit a pull request

---

## License

[Specify the license here]