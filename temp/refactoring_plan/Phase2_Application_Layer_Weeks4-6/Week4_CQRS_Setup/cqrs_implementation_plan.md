## Week 4: CQRS Foundation Setup - Implementation Plan

Based on the target structure and Python-specific recommendations, here's a comprehensive plan to implement the CQRS Foundation during Week 4.

## 🎯 **Week 4 Objectives**

1. **Create CQRS Infrastructure**: Shared interfaces, buses, and behaviors
2. **Establish Bounded Context Structure**: Commands/queries organization by context
3. **Implement Python-Specific Patterns**: Async/await, Pydantic DTOs, dynamic loading
4. **Prepare Migration Framework**: Foundation for existing handler refactoring

---

## 📋 **Day-by-Day Implementation Plan**

### **Day 1: Core CQRS Infrastructure Setup**

#### 🏗️ **Create Shared Infrastructure**

**1. Create Directory Structure**
```
application/
├── shared/
│   ├── interfaces/
│   ├── behaviors/
│   ├── exceptions/
│   ├── dto/
│   └── __init__.py
```

**2. Implement Core Interfaces**

**`application/shared/interfaces/command_handler.py`**
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Optional
from dataclasses import dataclass

TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')

class ICommandHandler(ABC, Generic[TCommand, TResult]):
    """Base interface for command handlers with async support."""
    
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Handle the command asynchronously."""
        pass

class ICommand(ABC):
    """Marker interface for commands."""
    pass
```

**`application/shared/interfaces/query_handler.py`**
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any
from dataclasses import dataclass

TQuery = TypeVar('TQuery')
TResult = TypeVar('TResult')

class IQueryHandler(ABC, Generic[TQuery, TResult]):
    """Base interface for query handlers with async support."""
    
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Handle the query asynchronously."""
        pass

class IQuery(ABC):
    """Marker interface for queries."""
    pass
```

**`application/shared/interfaces/command_bus.py`**
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Any, Type
import asyncio
from .command_handler import ICommand

TCommand = TypeVar('TCommand', bound=ICommand)
TResult = TypeVar('TResult')

class ICommandBus(ABC):
    """Command bus interface for dispatching commands."""
    
    @abstractmethod
    async def send(self, command: TCommand) -> TResult:
        """Send a command and return the result."""
        pass
    
    @abstractmethod
    def register_handler(self, command_type: Type[TCommand], handler_type: Type) -> None:
        """Register a command handler."""
        pass
```

**`application/shared/interfaces/query_bus.py`**
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Any, Type
from .query_handler import IQuery

TQuery = TypeVar('TQuery', bound=IQuery)
TResult = TypeVar('TResult')

class IQueryBus(ABC):
    """Query bus interface for dispatching queries."""
    
    @abstractmethod
    async def send(self, query: TQuery) -> TResult:
        """Send a query and return the result."""
        pass
    
    @abstractmethod
    def register_handler(self, query_type: Type[TQuery], handler_type: Type) -> None:
        """Register a query handler."""
        pass
```

#### 🚌 **Implement Simple Command/Query Buses**

**`application/shared/implementations/simple_command_bus.py`**
```python
from typing import Dict, Type, Any, TypeVar
import importlib
import inspect
from ..interfaces.command_bus import ICommandBus, ICommand
from ..interfaces.command_handler import ICommandHandler
from ..exceptions.command_validation_error import CommandValidationError

TCommand = TypeVar('TCommand', bound=ICommand)

class SimpleCommandBus(ICommandBus):
    """Simple in-memory command bus with dynamic handler loading."""
    
    def __init__(self, container: 'DependencyContainer'):
        self._container = container
        self._handlers: Dict[Type[ICommand], Type[ICommandHandler]] = {}
    
    async def send(self, command: TCommand) -> Any:
        """Send a command and return the result."""
        try:
            handler_type = self._get_handler_type(type(command))
            handler = self._container.resolve(handler_type)
            
            # Apply behaviors (validation, logging, etc.)
            await self._apply_behaviors(command, handler)
            
            return await handler.handle(command)
        except Exception as e:
            raise CommandValidationError(f"Failed to handle command {type(command).__name__}: {str(e)}")
    
    def register_handler(self, command_type: Type[TCommand], handler_type: Type[ICommandHandler]) -> None:
        """Register a command handler."""
        self._handlers[command_type] = handler_type
    
    def _get_handler_type(self, command_type: Type[ICommand]) -> Type[ICommandHandler]:
        """Get handler type for command, with auto-discovery fallback."""
        if command_type in self._handlers:
            return self._handlers[command_type]
        
        # Auto-discovery: Look for handler in same module
        handler_name = f"{command_type.__name__.replace('Command', '')}Handler"
        module_name = command_type.__module__.replace('.commands.', '.commands.handlers.')
        
        try:
            module = importlib.import_module(module_name)
            handler_class = getattr(module, handler_name)
            self._handlers[command_type] = handler_class
            return handler_class
        except (ImportError, AttributeError):
            raise CommandValidationError(f"No handler found for command {command_type.__name__}")
    
    async def _apply_behaviors(self, command: ICommand, handler: ICommandHandler) -> None:
        """Apply cross-cutting behaviors."""
        # Validation, logging, etc. will be implemented in behaviors
        pass
```

### **Day 2: Exception Handling & Behaviors**

#### 🚨 **Create Exception Classes**

**`application/shared/exceptions/command_validation_error.py`**
```python
class CommandValidationError(Exception):
    """Raised when command validation fails."""
    
    def __init__(self, message: str, command_type: str = None, validation_errors: dict = None):
        super().__init__(message)
        self.command_type = command_type
        self.validation_errors = validation_errors or {}

class CommandExecutionError(Exception):
    """Raised when command execution fails."""
    
    def __init__(self, message: str, command_type: str = None, inner_exception: Exception = None):
        super().__init__(message)
        self.command_type = command_type
        self.inner_exception = inner_exception
```

**`application/shared/exceptions/query_execution_error.py`**
```python
class QueryExecutionError(Exception):
    """Raised when query execution fails."""
    
    def __init__(self, message: str, query_type: str = None, inner_exception: Exception = None):
        super().__init__(message)
        self.query_type = query_type
        self.inner_exception = inner_exception

class QueryValidationError(Exception):
    """Raised when query validation fails."""
    
    def __init__(self, message: str, query_type: str = None, validation_errors: dict = None):
        super().__init__(message)
        self.query_type = query_type
        self.validation_errors = validation_errors or {}
```

#### 🔄 **Implement Behavior Pipeline**

**`application/shared/behaviors/logging_behavior.py`**
```python
import logging
import time
from typing import Any, Callable, Awaitable
from ..interfaces.command_handler import ICommand
from ..interfaces.query_handler import IQuery

logger = logging.getLogger(__name__)

class LoggingBehavior:
    """Cross-cutting logging behavior for commands and queries."""
    
    @staticmethod
    async def execute_with_logging(
        request: Any,
        handler: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """Execute handler with logging."""
        request_name = type(request).__name__
        start_time = time.time()
        
        logger.info(f"Executing {request_name}")
        
        try:
            result = await handler(request)
            execution_time = time.time() - start_time
            logger.info(f"Successfully executed {request_name} in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed to execute {request_name} in {execution_time:.3f}s: {str(e)}")
            raise
```

**`application/shared/behaviors/validation_behavior.py`**
```python
from typing import Any, Callable, Awaitable
from pydantic import BaseModel, ValidationError
from ..exceptions.command_validation_error import CommandValidationError
from ..exceptions.query_execution_error import QueryValidationError

class ValidationBehavior:
    """Cross-cutting validation behavior using Pydantic."""
    
    @staticmethod
    async def execute_with_validation(
        request: Any,
        handler: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """Execute handler with validation."""
        # Validate request if it's a Pydantic model
        if isinstance(request, BaseModel):
            try:
                # Pydantic validation happens automatically on instantiation
                # But we can add custom validation here
                await ValidationBehavior._validate_business_rules(request)
            except ValidationError as e:
                if hasattr(request, '__class__') and 'Command' in request.__class__.__name__:
                    raise CommandValidationError(
                        f"Validation failed for {type(request).__name__}",
                        command_type=type(request).__name__,
                        validation_errors=e.errors()
                    )
                else:
                    raise QueryValidationError(
                        f"Validation failed for {type(request).__name__}",
                        query_type=type(request).__name__,
                        validation_errors=e.errors()
                    )
        
        return await handler(request)
    
    @staticmethod
    async def _validate_business_rules(request: Any) -> None:
        """Validate business rules specific to the request."""
        # Custom business validation logic can be added here
        pass
```

### **Day 3: Bounded Context Structure Setup**

#### 📁 **Create Bounded Context Directories**

**Create the complete directory structure:**
```
application/
├── user_management/
│   ├── commands/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── queries/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── __init__.py
├── employee_management/
│   ├── commands/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── queries/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── __init__.py
├── scheduling/
│   ├── commands/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── queries/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── __init__.py
├── assignment/
│   ├── commands/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── queries/
│   │   ├── handlers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── __init__.py
└── workstation_management/
    ├── commands/
    │   ├── handlers/
    │   └── __init__.py
    ├── queries/
    │   ├── handlers/
    │   └── __init__.py
    ├── services/
    │   └── __init__.py
    └── __init__.py
```

#### 📝 **Create Pydantic DTOs**

**`application/shared/dto/base_dto.py`**
```python
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class BaseRequest(BaseModel):
    """Base class for all request DTOs."""
    
    class Config:
        # Enable validation on assignment
        validate_assignment = True
        # Use enum values instead of enum objects
        use_enum_values = True
        # Allow population by field name or alias
        allow_population_by_field_name = True

class BaseResponse(BaseModel):
    """Base class for all response DTOs."""
    
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        # Enable validation on assignment
        validate_assignment = True
        # Use enum values instead of enum objects
        use_enum_values = True

class PaginatedResponse(BaseResponse):
    """Base class for paginated responses."""
    
    total_count: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0
    
    def __post_init__(self):
        if self.total_count > 0 and self.page_size > 0:
            self.total_pages = (self.total_count + self.page_size - 1) // self.page_size
```

### **Day 4: Sample Implementation & Migration Framework**

#### 🔄 **Fix Directory Typo**
```bash
# Rename quieries to queries
mv application/quieries application/queries
```

#### 📋 **Create Sample Commands and Queries**

**`application/user_management/commands/create_user_command.py`**
```python
from dataclasses import dataclass
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from ..shared.interfaces.command_handler import ICommand
from ..shared.dto.base_dto import BaseRequest

@dataclass
class CreateUserCommand(ICommand):
    """Command to create a new user."""
    username: str
    email: Optional[str] = None
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = None

class CreateUserRequest(BaseRequest):
    """Pydantic model for user creation request validation."""
    username: str = Field(..., min_length=3, max_length=50, description="Username must be 3-50 characters")
    email: Optional[EmailStr] = Field(None, description="Valid email address")
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    roles: List[str] = Field(default_factory=list, description="List of role names")
    
    def to_command(self) -> CreateUserCommand:
        """Convert request DTO to command."""
        return CreateUserCommand(
            username=self.username,
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
            roles=self.roles
        )
```

**`application/user_management/queries/get_user_query.py`**
```python
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field
from ..shared.interfaces.query_handler import IQuery
from ..shared.dto.base_dto import BaseRequest, BaseResponse

@dataclass
class GetUserQuery(IQuery):
    """Query to get a user by ID."""
    user_id: int

class GetUserRequest(BaseRequest):
    """Pydantic model for get user request validation."""
    user_id: int = Field(..., gt=0, description="User ID must be positive")
    
    def to_query(self) -> GetUserQuery:
        """Convert request DTO to query."""
        return GetUserQuery(user_id=self.user_id)

class UserResponse(BaseResponse):
    """Response DTO for user data."""
    id: int
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    roles: List[str]
    created_at: datetime
    last_login_at: Optional[datetime]
```

#### 🔧 **Create Migration Framework**

**`application/shared/migration/handler_migrator.py`**
```python
import importlib
import inspect
from typing import Type, Dict, Any, List
from ..interfaces.command_handler import ICommandHandler
from ..interfaces.query_handler import IQueryHandler

class HandlerMigrator:
    """Utility to help migrate existing handlers to CQRS structure."""
    
    @staticmethod
    def analyze_existing_handler(handler_class: Type) -> Dict[str, Any]:
        """Analyze an existing handler to identify refactoring opportunities."""
        analysis = {
            'class_name': handler_class.__name__,
            'line_count': 0,
            'methods': [],
            'dependencies': [],
            'responsibilities': [],
            'suggested_splits': []
        }
        
        # Get source lines
        try:
            source_lines = inspect.getsourcelines(handler_class)[0]
            analysis['line_count'] = len(source_lines)
        except:
            pass
        
        # Analyze methods
        for name, method in inspect.getmembers(handler_class, predicate=inspect.ismethod):
            if not name.startswith('_'):
                analysis['methods'].append({
                    'name': name,
                    'parameters': list(inspect.signature(method).parameters.keys())
                })
        
        # Suggest splits based on analysis
        if analysis['line_count'] > 100:
            analysis['suggested_splits'].append('Consider splitting into multiple handlers')
        
        return analysis
    
    @staticmethod
    def suggest_command_query_split(handler_class: Type) -> Dict[str, List[str]]:
        """Suggest how to split a handler into commands and queries."""
        suggestions = {
            'commands': [],
            'queries': []
        }
        
        for name, method in inspect.getmembers(handler_class, predicate=inspect.ismethod):
            if not name.startswith('_'):
                # Simple heuristic: methods that return data are queries
                if 'get' in name.lower() or 'list' in name.lower() or 'find' in name.lower():
                    suggestions['queries'].append(name)
                else:
                    suggestions['commands'].append(name)
        
        return suggestions
```

---

## 🧪 **Testing Strategy**

### **Create Test Framework**

**`tests/application/shared/test_command_bus.py`**

```python
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from infrastructure.messaging.buses.simple_command_bus import SimpleCommandBus
from application.shared.interfaces.command_handler import ICommand, ICommandHandler


class TestCommand(ICommand):
  def __init__(self, value: str):
    self.value = value


class TestCommandHandler(ICommandHandler[TestCommand, str]):
  async def handle(self, command: TestCommand) -> str:
    return f"Handled: {command.value}"


@pytest.mark.asyncio
async def test_command_bus_sends_command():
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
```

---

## 📊 **Success Criteria for Week 4**

### ✅ **Completion Checklist**

- [ ] **Core Infrastructure Created**
  - [ ] Command/Query handler interfaces
  - [ ] Command/Query bus interfaces and implementations
  - [ ] Exception classes for validation and execution errors
  - [ ] Behavioral pipeline (logging, validation, transaction)

- [ ] **Bounded Context Structure**
  - [ ] All 5 bounded contexts have commands/queries/handlers directories
  - [ ] Directory typo fixed (`quieries` → `queries`)
  - [ ] Proper `__init__.py` files in all directories

- [ ] **Python-Specific Features**
  - [ ] Async/await support in all interfaces
  - [ ] Pydantic DTOs for request/response validation
  - [ ] Dynamic handler loading with importlib
  - [ ] Type hints throughout the codebase

- [ ] **Migration Framework**
  - [ ] Handler analysis tools
  - [ ] Command/query split suggestions
  - [ ] Sample implementations for each bounded context

- [ ] **Testing Foundation**
  - [ ] Unit tests for command/query buses
  - [ ] Integration tests for handler registration
  - [ ] Behavior testing framework

### 🎯 **Week 4 Deliverables**

1. **Complete CQRS Infrastructure** ready for handler implementation
2. **Bounded Context Structure** organized and ready for migration
3. **Migration Analysis** of existing `GenerateScheduleHandler`
4. **Sample Implementations** demonstrating patterns
5. **Testing Framework** for validating CQRS implementation
6. **Documentation** of new patterns and conventions

---

## 🚀 **Next Steps (Week 5 Preview)**

With Week 4 foundation complete, Week 5 will focus on:

1. **Migrate Existing Handlers**: Refactor `GenerateScheduleHandler` using new patterns
2. **Implement Query Handlers**: Create read-side operations for each context
3. **Add Cross-Context Communication**: Event-driven communication between contexts
4. **Performance Optimization**: Implement caching and read model optimization

This foundation provides a solid, Python-specific CQRS implementation that supports async operations, proper validation, and maintainable architecture patterns.