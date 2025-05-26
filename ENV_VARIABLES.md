# Environment Variables Configuration

This document describes the environment variables used by the Heijunka application.

## Overview

The Heijunka application uses environment variables for configuration instead of YAML files. This approach has several advantages:

1. **Security**: Sensitive information like database credentials and secret keys are not stored in version control
2. **Environment-specific configuration**: Different environments (development, testing, production) can have different configurations
3. **Containerization**: Easy to configure when running in containers
4. **Twelve-Factor App**: Follows the [Twelve-Factor App](https://12factor.net/) methodology for configuration

## Required Environment Variables

The following environment variables are required for the application to run:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `JWT_SECRET_KEY` | Secret key for JWT token generation | None | Yes |

## Optional Environment Variables

The following environment variables are optional and have default values:

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_EXPIRATION_MINUTES` | JWT token expiration time in minutes | 30 |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed origins for CORS | http://localhost:3000,http://localhost:8080 |
| `DATABASE_URL` | Database connection URL | sqlite:///schedule.db (development), postgresql+psycopg://user:password@localhost/heijunka (production) |
| `LOG_LEVEL` | Logging level | INFO |
| `ENVIRONMENT` | Environment (development, testing, production) | development |
| `PERIODS` | Number of work periods in a day | 4 |
| `MAX_SOLVE_TIME` | Maximum time in seconds for the solver | 60 |
| `LOOKBACK` | Number of days to look back for history | 3 |

## Environment-Specific Recommendations

### Development

For development, you can use the default values for most variables. Make sure to set a unique `JWT_SECRET_KEY`.

```
JWT_SECRET_KEY=your-secure-secret-key-for-development
ENVIRONMENT=development
```

### Testing

For testing, you might want to use an in-memory database:

```
JWT_SECRET_KEY=your-secure-secret-key-for-testing
DATABASE_URL=sqlite:///:memory:
ENVIRONMENT=testing
```

### Production

For production, make sure to set secure values for all sensitive variables:

```
JWT_SECRET_KEY=a-very-long-and-secure-random-key
DATABASE_URL=postgresql+psycopg://heijunka_user:your_secure_password@localhost/heijunka
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

#### PostgreSQL Database Setup

For production environments, PostgreSQL is strongly recommended over SQLite. The application includes tools to help set up and manage a PostgreSQL database:

1. **Install PostgreSQL**: Install PostgreSQL on your server or use a managed PostgreSQL service.

2. **Create a database user**: Create a PostgreSQL user for the application:
   ```sql
   CREATE USER heijunka_user WITH PASSWORD 'your_secure_password';
   ```

3. **Initialize the database**: Run the database initialization script:
   ```bash
   python -m infrastructure.database.init_db
   ```

   This script will:
   - Create the database if it doesn't exist
   - Set up role-based access control (RBAC) roles
   - Apply all migrations to create the schema

4. **Database Roles**: The application uses the following database roles:
   - `heijunka_admin`: Full administrative access
   - `heijunka_writer`: Can read, insert, update, and delete data
   - `heijunka_reader`: Read-only access

   These roles are created automatically by the initialization script.

## Setting Environment Variables

### Using a .env File

The application uses the `python-dotenv` package to load environment variables from a `.env` file. Create a `.env` file in the root directory of the project with your environment variables:

```
# .env file
JWT_SECRET_KEY=your-secure-secret-key
DATABASE_URL=sqlite:///schedule.db
```

### Using System Environment Variables

You can also set environment variables at the system level:

```bash
# Linux/macOS
export JWT_SECRET_KEY=your-secure-secret-key
export DATABASE_URL=sqlite:///schedule.db

# Windows (Command Prompt)
set JWT_SECRET_KEY=your-secure-secret-key
set DATABASE_URL=sqlite:///schedule.db

# Windows (PowerShell)
$env:JWT_SECRET_KEY="your-secure-secret-key"
$env:DATABASE_URL="sqlite:///schedule.db"
```

## Security Considerations

1. **Never commit `.env` files**: Make sure to add `.env` to your `.gitignore` file
2. **Use different values in different environments**: Use different values for sensitive configuration in development, testing, and production environments
3. **Rotate secrets regularly**: Implement a process for regularly rotating secrets like JWT keys
4. **Limit access to environment variables**: In production environments, limit access to environment variables to only the necessary services and users
