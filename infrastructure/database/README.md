# Database Infrastructure

This directory contains modules for database infrastructure in the Heijunka application.

## Overview

The database infrastructure provides:

1. Connection management for both SQLite and PostgreSQL databases
2. Role-based access control (RBAC) for PostgreSQL
3. Database initialization and migration tools

## Modules

### init_db.py

A script to initialize the PostgreSQL database:

```bash
python -m infrastructure.database.init_db
```

This script:
- Creates the database if it doesn't exist
- Sets up RBAC roles (admin, writer, reader)
- Applies all Alembic migrations to create the schema

### rbac.py

Implements role-based access control for PostgreSQL databases:

- `heijunka_admin`: Full administrative access
- `heijunka_writer`: Can read, insert, update, and delete data
- `heijunka_reader`: Read-only access

## Usage

### Development Environment

For development, SQLite is used by default:

```
DATABASE_URL=sqlite:///schedule.db
```

### Production Environment

For production, PostgreSQL is strongly recommended:

```
DATABASE_URL=postgresql+psycopg://heijunka_user:your_secure_password@localhost/heijunka
```

### Database Migration

To apply migrations:

```bash
alembic upgrade head
```

To create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

## Security Considerations

1. **Use strong passwords**: Always use strong, unique passwords for database users
2. **Principle of least privilege**: Use the appropriate role for each connection
3. **Regular backups**: Implement regular database backups
4. **Connection pooling**: The application uses connection pooling for PostgreSQL to improve performance and security
5. **Secure connections**: Consider using SSL for database connections in production