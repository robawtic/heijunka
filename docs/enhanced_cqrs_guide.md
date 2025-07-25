# Enhanced CQRS Implementation Guide

## Overview

This guide covers the enhanced Command Query Responsibility Segregation (CQRS) implementation that provides production-grade features for both command and query buses.

## Key Features

### 🚀 Production-Grade Features
- **Dynamic Handler Discovery**: Automatic handler loading via naming conventions
- **Behavior Pipeline**: Cross-cutting concerns (logging, validation, caching, transactions)
- **Robust Error Handling**: Detailed error messages and proper exception handling
- **Dependency Injection Support**: Optional DI container integration
- **Comprehensive Logging**: Debug and performance logging throughout
- **Type Safety**: Full generic type support with proper interfaces

### 🔧 Shared Architecture
Both `SimpleCommandBus` and `SimpleQueryBus` now use shared mixins for consistency:
- `BehaviorPipelineMixin`: Behavior registration and execution
- `HandlerInstantiationMixin`: Robust handler creation with error handling
- `HandlerDiscoveryMixin`: Handler registration and dynamic discovery

## Quick Start

### Basic Usage

```python
from infrastructure.messaging.buses.simple_command_bus import SimpleCommandBus
from infrastructure.messaging.buses.simple_query_bus import SimpleQueryBus

# Create buses
command_bus = SimpleCommandBus()
query_bus = SimpleQueryBus()

# Register handlers
command_bus.register_handler(CreateUserCommand, CreateUserHandler)
query_bus.register_handler(GetUserQuery, GetUserHandler)

# Send commands and queries
result = await command_bus.send(CreateUserCommand(username="john"))
user = await query_bus.send(GetUserQuery(user_id=123))
```

### With Dependency Injection

```python
# Initialize with DI container
command_bus = SimpleCommandBus(dependency_container=container)
query_bus = SimpleQueryBus(dependency_container=container)

# Handlers will be resolved from container automatically
```

## Behavior Pipeline

### Adding Behaviors

Behaviors are executed in the order they are added, creating a pipeline around handler execution:

```python
# Add logging behavior
async def logging_behavior(request, next_handler):
    logger.info(f"Processing {type(request).__name__}")
    result = await next_handler(request)
    logger.info(f"Completed {type(request).__name__}")
    return result

# Add validation behavior
async def validation_behavior(request, next_handler):
    # Validate request
    if not hasattr(request, 'validate') or not request.validate():
        raise ValidationError("Invalid request")
    return await next_handler(request)

# Register behaviors
command_bus.add_behavior(logging_behavior)
command_bus.add_behavior(validation_behavior)
query_bus.add_behavior(logging_behavior)
```

### Common Behavior Patterns

#### 1. Logging Behavior
```python
async def logging_behavior(request, next_handler):
    start_time = time.time()
    logger.info(f"Starting {type(request).__name__}")
    
    try:
        result = await next_handler(request)
        duration = time.time() - start_time
        logger.info(f"Completed {type(request).__name__} in {duration:.3f}s")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed {type(request).__name__} after {duration:.3f}s: {e}")
        raise
```

#### 2. Caching Behavior (for Queries)
```python
async def caching_behavior(request, next_handler):
    cache_key = f"{type(request).__name__}:{hash(str(request))}"
    
    # Try cache first
    cached_result = await cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Execute and cache result
    result = await next_handler(request)
    await cache.set(cache_key, result, ttl=300)
    return result
```

#### 3. Transaction Behavior (for Commands)
```python
async def transaction_behavior(request, next_handler):
    async with database.transaction():
        return await next_handler(request)
```

#### 4. Validation Behavior
```python
async def validation_behavior(request, next_handler):
    if hasattr(request, 'validate'):
        validation_result = request.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
    
    return await next_handler(request)
```

## Handler Discovery

### Explicit Registration
```python
# Explicit registration (recommended for production)
command_bus.register_handler(CreateUserCommand, CreateUserHandler)
query_bus.register_handler(GetUserQuery, GetUserHandler)
```

### Dynamic Discovery
Handlers can be automatically discovered using naming conventions:

**For Commands:**
- Command: `CreateUserCommand` in module `app.commands.create_user_command`
- Handler: `CreateUserHandler` in module `app.commands.handlers.create_user_handler`

**For Queries:**
- Query: `GetUserQuery` in module `app.queries.get_user_query`
- Handler: `GetUserHandler` in module `app.queries.handlers.get_user_handler`

## Error Handling

### Command Errors
- `CommandValidationError`: Handler not found or validation failures
- `CommandExecutionError`: Handler instantiation or execution failures

### Query Errors
- `QueryValidationError`: Handler not found or validation failures
- `QueryExecutionError`: Handler instantiation or execution failures

### Error Information
All exceptions include:
- Detailed error messages
- Request type information
- Inner exception details (when applicable)
- Helpful suggestions for resolution

## Handler Requirements

### Without Dependency Injection
Handlers must have parameterless constructors:

```python
class CreateUserHandler(ICommandHandler):
    def __init__(self):
        # Initialize without parameters
        pass
    
    async def handle(self, command: CreateUserCommand) -> str:
        # Handle the command
        return "User created"
```

### With Dependency Injection
Handlers can have dependencies injected:

```python
class CreateUserHandler(ICommandHandler):
    def __init__(self, user_repository: IUserRepository, logger: ILogger):
        self.user_repository = user_repository
        self.logger = logger
    
    async def handle(self, command: CreateUserCommand) -> str:
        # Use injected dependencies
        user = User(command.username)
        await self.user_repository.save(user)
        self.logger.info(f"Created user: {user.username}")
        return user.id
```

## Performance Considerations

### Logging Levels
- Use `DEBUG` level for detailed tracing
- Use `INFO` level for important operations
- Use `WARNING` for recoverable issues
- Use `ERROR` for failures

### Behavior Ordering
- Place validation behaviors early in the pipeline
- Place logging behaviors at the beginning and end
- Place transaction behaviors around the core logic
- Place caching behaviors for queries only

### Handler Caching
Discovered handlers are automatically cached for improved performance on subsequent requests.

## Best Practices

### 1. Handler Design
- Keep handlers focused on a single responsibility
- Use dependency injection for testability
- Implement proper error handling
- Add validation where appropriate

### 2. Behavior Design
- Make behaviors composable and reusable
- Handle exceptions appropriately
- Consider performance impact
- Document behavior purpose and usage

### 3. Error Handling
- Use specific exception types
- Provide helpful error messages
- Log errors with appropriate levels
- Include context information

### 4. Testing
- Test handlers in isolation
- Test behavior pipeline combinations
- Test error scenarios
- Use mocks for dependencies

## Migration from Previous Implementation

### SimpleQueryBus Changes
The `SimpleQueryBus` has been significantly enhanced:

**Before:**
```python
# Minimal implementation
bus = SimpleQueryBus()
bus.register_handler(GetUserQuery, GetUserHandler)
result = await bus.send(query)
```

**After:**
```python
# Enhanced with behaviors and robust error handling
bus = SimpleQueryBus(dependency_container=container)
bus.add_behavior(logging_behavior)
bus.add_behavior(caching_behavior)
bus.register_handler(GetUserQuery, GetUserHandler)
result = await bus.send(query)
```

### SimpleCommandBus Changes
The `SimpleCommandBus` now uses shared mixins for consistency:
- Same API, improved internal implementation
- Better error messages and logging
- Consistent behavior with QueryBus

## Troubleshooting

### Common Issues

1. **Handler Not Found**
   - Ensure handler is registered or follows naming convention
   - Check module paths for dynamic discovery
   - Verify handler class exists and is importable

2. **Handler Instantiation Failed**
   - Check constructor requirements
   - Provide DI container if handler has dependencies
   - Ensure all dependencies are registered in container

3. **Behavior Execution Issues**
   - Check behavior function signature
   - Ensure behaviors call `next_handler`
   - Handle exceptions in behaviors appropriately

### Debug Logging
Enable debug logging to see detailed execution flow:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- Bus initialization
- Handler registration and discovery
- Handler instantiation
- Behavior execution
- Performance metrics

## Examples

See `test_enhanced_buses.py` for complete working examples of:
- Basic command and query handling
- Behavior pipeline usage
- Error handling scenarios
- Performance logging

The enhanced CQRS implementation provides a solid foundation for scalable, maintainable applications with comprehensive cross-cutting concerns support.