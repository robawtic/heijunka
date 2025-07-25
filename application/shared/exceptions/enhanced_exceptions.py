from typing import Type, Optional, Dict, Any
import inspect
from .command_validation_error import CommandValidationError, CommandExecutionError
from .query_execution_error import QueryExecutionError, QueryValidationError

class EnhancedCommandExecutionError(CommandExecutionError):
    """Enhanced command execution error with additional context."""
    
    def __init__(self, message: str, command_type: str = None, 
                 handler_type: str = None, execution_context: Dict[str, Any] = None, 
                 inner_exception: Exception = None):
        super().__init__(message, command_type, inner_exception)
        self.handler_type = handler_type
        self.execution_context = execution_context or {}
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.handler_type:
            base_msg += f" [Handler: {self.handler_type}]"
        if self.execution_context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.execution_context.items())
            base_msg += f" [Context: {context_str}]"
        return base_msg

class EnhancedQueryExecutionError(QueryExecutionError):
    """Enhanced query execution error with additional context."""
    
    def __init__(self, message: str, query_type: str = None, 
                 handler_type: str = None, execution_context: Dict[str, Any] = None, 
                 inner_exception: Exception = None):
        super().__init__(message, query_type, inner_exception)
        self.handler_type = handler_type
        self.execution_context = execution_context or {}
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.handler_type:
            base_msg += f" [Handler: {self.handler_type}]"
        if self.execution_context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.execution_context.items())
            base_msg += f" [Context: {context_str}]"
        return base_msg

class ExceptionHelper:
    """
    Utility class for creating properly configured exceptions with enhanced context.
    Reduces code duplication and provides consistent error handling patterns.
    """
    
    @staticmethod
    def create_typed_exception(
        error_class: Type[Exception], 
        message: str, 
        request_name: str,
        handler_type: Optional[str] = None,
        inner_exception: Optional[Exception] = None,
        validation_errors: Optional[Dict] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Exception:
        """
        Create exception with appropriate constructor arguments based on class signature.
        
        Args:
            error_class: Exception class to instantiate
            message: Error message
            request_name: Name of the request that failed
            handler_type: Name of the handler that was processing the request
            inner_exception: Original exception that caused the failure
            validation_errors: Validation error details (for validation exceptions)
            execution_context: Additional context information
            
        Returns:
            Properly configured exception instance
        """
        sig = inspect.signature(error_class.__init__)
        kwargs = {}
        
        # Map common parameter names based on exception type
        if 'command_type' in sig.parameters:
            kwargs['command_type'] = request_name
        elif 'query_type' in sig.parameters:
            kwargs['query_type'] = request_name
            
        if 'handler_type' in sig.parameters and handler_type:
            kwargs['handler_type'] = handler_type
            
        if 'inner_exception' in sig.parameters and inner_exception:
            kwargs['inner_exception'] = inner_exception
            
        if 'validation_errors' in sig.parameters and validation_errors:
            kwargs['validation_errors'] = validation_errors
            
        if 'execution_context' in sig.parameters and execution_context:
            kwargs['execution_context'] = execution_context
            
        return error_class(message, **kwargs)
    
    @staticmethod
    def create_command_execution_error(
        message: str,
        command_type: str,
        handler_type: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        inner_exception: Optional[Exception] = None
    ) -> EnhancedCommandExecutionError:
        """
        Create enhanced command execution error with full context.
        
        Args:
            message: Error message
            command_type: Name of the command that failed
            handler_type: Name of the handler that was processing the command
            execution_context: Additional context information
            inner_exception: Original exception that caused the failure
            
        Returns:
            Enhanced command execution error
        """
        return EnhancedCommandExecutionError(
            message=message,
            command_type=command_type,
            handler_type=handler_type,
            execution_context=execution_context,
            inner_exception=inner_exception
        )
    
    @staticmethod
    def create_query_execution_error(
        message: str,
        query_type: str,
        handler_type: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        inner_exception: Optional[Exception] = None
    ) -> EnhancedQueryExecutionError:
        """
        Create enhanced query execution error with full context.
        
        Args:
            message: Error message
            query_type: Name of the query that failed
            handler_type: Name of the handler that was processing the query
            execution_context: Additional context information
            inner_exception: Original exception that caused the failure
            
        Returns:
            Enhanced query execution error
        """
        return EnhancedQueryExecutionError(
            message=message,
            query_type=query_type,
            handler_type=handler_type,
            execution_context=execution_context,
            inner_exception=inner_exception
        )
    
    @staticmethod
    def wrap_handler_exception(
        original_exception: Exception,
        request_name: str,
        handler_type: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Exception:
        """
        Wrap an exception that occurred during handler execution with enhanced context.
        
        Args:
            original_exception: The original exception that occurred
            request_name: Name of the request being processed
            handler_type: Name of the handler that threw the exception
            execution_context: Additional context information
            
        Returns:
            Enhanced exception with additional context
        """
        context = execution_context or {}
        context['original_exception_type'] = type(original_exception).__name__
        
        # Determine if this is a command or query based on naming convention
        if 'Command' in request_name:
            return ExceptionHelper.create_command_execution_error(
                message=f"Handler execution failed: {str(original_exception)}",
                command_type=request_name,
                handler_type=handler_type,
                execution_context=context,
                inner_exception=original_exception
            )
        else:
            return ExceptionHelper.create_query_execution_error(
                message=f"Handler execution failed: {str(original_exception)}",
                query_type=request_name,
                handler_type=handler_type,
                execution_context=context,
                inner_exception=original_exception
            )