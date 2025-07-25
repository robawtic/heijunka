import pytest
from unittest.mock import Mock
from infrastructure.messaging.buses.simple_command_bus import SimpleCommandBus
from application.shared.interfaces.command_handler import ICommand, ICommandHandler
from application.shared.exceptions.command_validation_error import CommandValidationError, CommandExecutionError

class TestCommand(ICommand):
    """Test command for unit testing."""
    def __init__(self, value: str):
        self.value = value

class TestCommandHandler(ICommandHandler[TestCommand, str]):
    """Test command handler for unit testing."""
    async def handle(self, command: TestCommand) -> str:
        return f"Handled: {command.value}"

class FailingTestCommandHandler(ICommandHandler[TestCommand, str]):
    """Test command handler that always fails."""
    async def handle(self, command: TestCommand) -> str:
        raise Exception("Handler failed")

class HandlerWithDependencies(ICommandHandler[TestCommand, str]):
    """Test handler that requires constructor arguments."""
    def __init__(self, dependency1, dependency2):
        self.dependency1 = dependency1
        self.dependency2 = dependency2

    async def handle(self, command: TestCommand) -> str:
        return f"Handled with deps: {command.value}"

@pytest.mark.asyncio
async def test_command_bus_sends_command_with_registered_handler():
    """Test that command bus can send commands with registered handlers."""
    # Arrange
    container = Mock()
    handler = TestCommandHandler()
    container.resolve.return_value = handler

    bus = SimpleCommandBus(container)
    bus.register_handler(TestCommand, TestCommandHandler)

    command = TestCommand("test")

    # Act
    result = await bus.send(command)

    # Assert
    assert result == "Handled: test"
    container.resolve.assert_called_once_with(TestCommandHandler)

@pytest.mark.asyncio
async def test_command_bus_sends_command_without_container():
    """Test that command bus works without dependency injection container."""
    # Arrange
    bus = SimpleCommandBus()
    bus.register_handler(TestCommand, TestCommandHandler)

    command = TestCommand("test")

    # Act
    result = await bus.send(command)

    # Assert
    assert result == "Handled: test"

@pytest.mark.asyncio
async def test_command_bus_raises_error_for_unregistered_handler():
    """Test that command bus raises error when no handler is found."""
    # Arrange
    bus = SimpleCommandBus()
    command = TestCommand("test")

    # Act & Assert
    with pytest.raises(CommandValidationError) as exc_info:
        await bus.send(command)

    assert "No handler registered or found for command TestCommand" in str(exc_info.value)

@pytest.mark.asyncio
async def test_command_bus_wraps_handler_exceptions():
    """Test that command bus wraps handler exceptions in CommandExecutionError."""
    # Arrange
    container = Mock()
    handler = FailingTestCommandHandler()
    container.resolve.return_value = handler

    bus = SimpleCommandBus(container)
    bus.register_handler(TestCommand, FailingTestCommandHandler)

    command = TestCommand("test")

    # Act & Assert
    with pytest.raises(CommandExecutionError) as exc_info:
        await bus.send(command)

    assert "Unexpected error processing command TestCommand" in str(exc_info.value)

def test_command_bus_registers_handler():
    """Test that command bus can register handlers."""
    # Arrange
    bus = SimpleCommandBus()

    # Act
    bus.register_handler(TestCommand, TestCommandHandler)

    # Assert
    assert TestCommand in bus._handlers
    assert bus._handlers[TestCommand] == TestCommandHandler

@pytest.mark.asyncio
async def test_command_bus_uses_registered_handler_over_dynamic_loading():
    """Test that registered handlers take precedence over dynamic loading."""
    # Arrange
    container = Mock()
    handler = TestCommandHandler()
    container.resolve.return_value = handler

    bus = SimpleCommandBus(container)
    bus.register_handler(TestCommand, TestCommandHandler)

    command = TestCommand("test")

    # Act
    result = await bus.send(command)

    # Assert
    assert result == "Handled: test"
    container.resolve.assert_called_once_with(TestCommandHandler)

@pytest.mark.asyncio
async def test_command_bus_detects_handler_with_dependencies():
    """Test that command bus detects handlers requiring constructor arguments."""
    # Arrange
    bus = SimpleCommandBus()  # No DI container
    bus.register_handler(TestCommand, HandlerWithDependencies)

    command = TestCommand("test")

    # Act & Assert
    with pytest.raises(CommandExecutionError) as exc_info:
        await bus.send(command)

    assert "requires constructor arguments" in str(exc_info.value)
    assert "dependency1" in str(exc_info.value)
    assert "dependency2" in str(exc_info.value)

@pytest.mark.asyncio
async def test_command_bus_handles_container_returning_none():
    """Test that command bus handles DI container returning None."""
    # Arrange
    container = Mock()
    container.resolve.return_value = None  # Container returns None

    bus = SimpleCommandBus(container)
    bus.register_handler(TestCommand, TestCommandHandler)

    command = TestCommand("test")

    # Act & Assert
    with pytest.raises(CommandExecutionError) as exc_info:
        await bus.send(command)

    assert "DI container returned None" in str(exc_info.value)

def test_command_bus_validates_handler_registration():
    """Test that command bus validates handler registration."""
    # Arrange
    bus = SimpleCommandBus()

    # Act & Assert - Invalid command type
    with pytest.raises(ValueError) as exc_info:
        bus.register_handler(str, TestCommandHandler)  # str is not ICommand

    assert "must implement ICommand" in str(exc_info.value)

    # Act & Assert - Invalid handler type
    with pytest.raises(ValueError) as exc_info:
        bus.register_handler(TestCommand, str)  # str doesn't have handle method

    assert "must implement handle method" in str(exc_info.value)

@pytest.mark.asyncio
async def test_command_bus_behavior_pipeline():
    """Test that command bus executes behaviors in correct order."""
    # Arrange
    bus = SimpleCommandBus()
    bus.register_handler(TestCommand, TestCommandHandler)

    execution_order = []

    async def behavior1(request, next_handler):
        execution_order.append("behavior1_start")
        result = await next_handler(request)
        execution_order.append("behavior1_end")
        return result

    async def behavior2(request, next_handler):
        execution_order.append("behavior2_start")
        result = await next_handler(request)
        execution_order.append("behavior2_end")
        return result

    bus.add_behavior(behavior1)
    bus.add_behavior(behavior2)

    command = TestCommand("test")

    # Act
    result = await bus.send(command)

    # Assert
    assert result == "Handled: test"
    # Behaviors should execute in reverse order (last added first)
    assert execution_order == ["behavior2_start", "behavior1_start", "behavior1_end", "behavior2_end"]

@pytest.mark.asyncio
async def test_command_bus_behavior_can_modify_result():
    """Test that behaviors can modify the result."""
    # Arrange
    bus = SimpleCommandBus()
    bus.register_handler(TestCommand, TestCommandHandler)

    async def modifying_behavior(request, next_handler):
        result = await next_handler(request)
        return f"Modified: {result}"

    bus.add_behavior(modifying_behavior)

    command = TestCommand("test")

    # Act
    result = await bus.send(command)

    # Assert
    assert result == "Modified: Handled: test"

def test_command_bus_add_behavior():
    """Test that command bus can add behaviors."""
    # Arrange
    bus = SimpleCommandBus()

    async def test_behavior(request, next_handler):
        return await next_handler(request)

    # Act
    bus.add_behavior(test_behavior)

    # Assert
    assert len(bus._behaviors) == 1
    assert bus._behaviors[0] == test_behavior
