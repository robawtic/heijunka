import pytest
from infrastructure.messaging.buses.simple_command_bus import SimpleCommandBus
from application.user_management.commands.create_user_request import CreateUserRequest
from application.user_management.commands.create_user_command import CreateUserCommand
from application.user_management.commands.handlers.create_user_handler import CreateUserHandler

@pytest.mark.asyncio
async def test_complete_cqrs_flow():
    """
    Integration test for complete CQRS flow: DTO → Command → Handler.
    
    This test demonstrates the dataclass/Pydantic harmony pattern:
    1. Pydantic DTO validates input at boundary
    2. DTO converts to lightweight dataclass command
    3. Command bus dispatches to handler
    4. Handler processes command and returns result
    """
    # Arrange - Create command bus and register handler
    bus = SimpleCommandBus()
    bus.register_handler(CreateUserCommand, CreateUserHandler)
    
    # Arrange - Create Pydantic DTO with validation
    request_data = {
        "username": "john_doe",
        "password": "SecurePass123!",
        "email": "john.doe@company.com",
        "first_name": "John",
        "last_name": "Doe",
        "roles": ["user", "employee"]
    }
    
    # Act - Create and validate Pydantic DTO
    request = CreateUserRequest(**request_data)
    
    # Act - Convert DTO to internal command
    command = request.to_command()
    
    # Act - Send command through bus
    result = await bus.send(command)
    
    # Assert - Verify the complete flow worked
    assert isinstance(result, int)
    assert result == 123  # Mock user ID from handler
    
    # Assert - Verify command has correct data
    assert command.username == "john_doe"
    assert command.email == "john.doe@company.com"
    assert command.first_name == "John"
    assert command.last_name == "Doe"
    assert command.roles == ["user", "employee"]

@pytest.mark.asyncio
async def test_pydantic_validation_in_cqrs_flow():
    """
    Test that Pydantic validation works correctly in CQRS flow.
    
    This demonstrates boundary validation with rich error messages.
    """
    # Arrange - Invalid data that should fail Pydantic validation
    invalid_data = {
        "username": "jo",  # Too short (min 3 chars)
        "password": "123",  # Too short (min 8 chars)
        "email": "invalid-email",  # Invalid email format
        "first_name": "A" * 101,  # Too long (max 100 chars)
    }
    
    # Act & Assert - Pydantic should raise ValidationError
    with pytest.raises(Exception):  # Pydantic ValidationError
        CreateUserRequest(**invalid_data)

@pytest.mark.asyncio
async def test_dto_to_command_conversion():
    """
    Test the DTO to command conversion maintains data integrity.
    
    This validates the centralized mapping logic in the to_command() method.
    """
    # Arrange
    request_data = {
        "username": "test_user",
        "password": "password123",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "roles": ["admin"]
    }
    
    # Act
    request = CreateUserRequest(**request_data)
    command = request.to_command()
    
    # Assert - All fields are correctly mapped
    assert command.username == request.username
    assert command.password == request.password
    assert command.email == request.email
    assert command.first_name == request.first_name
    assert command.last_name == request.last_name
    assert command.roles == request.roles
    
    # Assert - Command is lightweight dataclass
    assert isinstance(command, CreateUserCommand)
    assert hasattr(command, '__dataclass_fields__')

@pytest.mark.asyncio
async def test_handler_dependency_injection_pattern():
    """
    Test that handlers can be instantiated with dependencies.
    
    This demonstrates the dependency injection pattern for handlers.
    """
    # Arrange - Mock dependencies
    mock_user_repo = "mock_user_repository"
    mock_password_service = "mock_password_service"
    mock_email_service = "mock_email_service"
    
    # Act - Create handler with dependencies
    handler = CreateUserHandler(
        user_repository=mock_user_repo,
        password_service=mock_password_service,
        email_service=mock_email_service
    )
    
    # Assert - Dependencies are properly injected
    assert handler._user_repository == mock_user_repo
    assert handler._password_service == mock_password_service
    assert handler._email_service == mock_email_service

@pytest.mark.asyncio
async def test_async_handler_execution():
    """
    Test that handlers execute asynchronously.
    
    This validates the async/await pattern throughout the CQRS pipeline.
    """
    # Arrange
    handler = CreateUserHandler()
    command = CreateUserCommand(
        username="async_test",
        password="password123"
    )
    
    # Act - Execute handler asynchronously
    result = await handler.handle(command)
    
    # Assert - Handler completed and returned result
    assert isinstance(result, int)
    assert result == 123