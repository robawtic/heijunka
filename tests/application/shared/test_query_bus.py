import pytest
from unittest.mock import Mock, AsyncMock
from infrastructure.messaging.buses.simple_query_bus import SimpleQueryBus, CacheProvider
from application.shared.interfaces.query_handler import IQuery, IQueryHandler
from application.shared.exceptions.query_execution_error import QueryExecutionError, QueryValidationError

class TestQuery(IQuery):
    """Test query for unit testing."""
    def __init__(self, value: str):
        self.value = value

class TestQueryHandler(IQueryHandler[TestQuery, str]):
    """Test query handler for unit testing."""
    async def handle(self, query: TestQuery) -> str:
        return f"Result: {query.value}"

class FailingTestQueryHandler(IQueryHandler[TestQuery, str]):
    """Test query handler that always fails."""
    async def handle(self, query: TestQuery) -> str:
        raise Exception("Handler failed")

class HandlerWithDependencies(IQueryHandler[TestQuery, str]):
    """Test handler that requires constructor arguments."""
    def __init__(self, dependency1, dependency2):
        self.dependency1 = dependency1
        self.dependency2 = dependency2
    
    async def handle(self, query: TestQuery) -> str:
        return f"Result with deps: {query.value}"

class MockCacheProvider:
    """Mock cache provider for testing."""
    def __init__(self):
        self.cache = {}
        self.get_calls = []
        self.set_calls = []
        self.delete_calls = []
    
    async def get(self, key: str):
        self.get_calls.append(key)
        return self.cache.get(key)
    
    async def set(self, key: str, value, ttl_seconds=None):
        self.set_calls.append((key, value, ttl_seconds))
        self.cache[key] = value
    
    async def delete(self, key: str):
        self.delete_calls.append(key)
        if key in self.cache:
            del self.cache[key]

@pytest.mark.asyncio
async def test_query_bus_sends_query_with_registered_handler():
    """Test that query bus can send queries with registered handlers."""
    # Arrange
    container = Mock()
    handler = TestQueryHandler()
    container.resolve.return_value = handler
    
    bus = SimpleQueryBus(container)
    bus.register_handler(TestQuery, TestQueryHandler)
    
    query = TestQuery("test")
    
    # Act
    result = await bus.send(query)
    
    # Assert
    assert result == "Result: test"
    container.resolve.assert_called_once_with(TestQueryHandler)

@pytest.mark.asyncio
async def test_query_bus_sends_query_without_container():
    """Test that query bus works without dependency injection container."""
    # Arrange
    bus = SimpleQueryBus()
    bus.register_handler(TestQuery, TestQueryHandler)
    
    query = TestQuery("test")
    
    # Act
    result = await bus.send(query)
    
    # Assert
    assert result == "Result: test"

@pytest.mark.asyncio
async def test_query_bus_raises_error_for_unregistered_handler():
    """Test that query bus raises error when no handler is found."""
    # Arrange
    bus = SimpleQueryBus()
    query = TestQuery("test")
    
    # Act & Assert
    with pytest.raises(QueryValidationError) as exc_info:
        await bus.send(query)
    
    assert "No handler registered or found for query TestQuery" in str(exc_info.value)

@pytest.mark.asyncio
async def test_query_bus_wraps_handler_exceptions():
    """Test that query bus wraps handler exceptions in QueryExecutionError."""
    # Arrange
    container = Mock()
    handler = FailingTestQueryHandler()
    container.resolve.return_value = handler
    
    bus = SimpleQueryBus(container)
    bus.register_handler(TestQuery, FailingTestQueryHandler)
    
    query = TestQuery("test")
    
    # Act & Assert
    with pytest.raises(QueryExecutionError) as exc_info:
        await bus.send(query)
    
    assert "Unexpected error processing query TestQuery" in str(exc_info.value)

def test_query_bus_registers_handler():
    """Test that query bus can register handlers."""
    # Arrange
    bus = SimpleQueryBus()
    
    # Act
    bus.register_handler(TestQuery, TestQueryHandler)
    
    # Assert
    assert TestQuery in bus._handlers
    assert bus._handlers[TestQuery] == TestQueryHandler

@pytest.mark.asyncio
async def test_query_bus_detects_handler_with_dependencies():
    """Test that query bus detects handlers requiring constructor arguments."""
    # Arrange
    bus = SimpleQueryBus()  # No DI container
    bus.register_handler(TestQuery, HandlerWithDependencies)
    
    query = TestQuery("test")
    
    # Act & Assert
    with pytest.raises(QueryExecutionError) as exc_info:
        await bus.send(query)
    
    assert "requires constructor arguments" in str(exc_info.value)
    assert "dependency1" in str(exc_info.value)
    assert "dependency2" in str(exc_info.value)

@pytest.mark.asyncio
async def test_query_bus_handles_container_returning_none():
    """Test that query bus handles DI container returning None."""
    # Arrange
    container = Mock()
    container.resolve.return_value = None  # Container returns None
    
    bus = SimpleQueryBus(container)
    bus.register_handler(TestQuery, TestQueryHandler)
    
    query = TestQuery("test")
    
    # Act & Assert
    with pytest.raises(QueryExecutionError) as exc_info:
        await bus.send(query)
    
    assert "DI container returned None" in str(exc_info.value)

def test_query_bus_validates_handler_registration():
    """Test that query bus validates handler registration."""
    # Arrange
    bus = SimpleQueryBus()
    
    # Act & Assert - Invalid query type
    with pytest.raises(ValueError) as exc_info:
        bus.register_handler(str, TestQueryHandler)  # str is not IQuery
    
    assert "must implement IQuery" in str(exc_info.value)
    
    # Act & Assert - Invalid handler type
    with pytest.raises(ValueError) as exc_info:
        bus.register_handler(TestQuery, str)  # str doesn't have handle method
    
    assert "must implement handle method" in str(exc_info.value)

@pytest.mark.asyncio
async def test_query_bus_behavior_pipeline():
    """Test that query bus executes behaviors in correct order."""
    # Arrange
    bus = SimpleQueryBus()
    bus.register_handler(TestQuery, TestQueryHandler)
    
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
    
    query = TestQuery("test")
    
    # Act
    result = await bus.send(query)
    
    # Assert
    assert result == "Result: test"
    # Behaviors should execute in reverse order (last added first)
    assert execution_order == ["behavior2_start", "behavior1_start", "behavior1_end", "behavior2_end"]

@pytest.mark.asyncio
async def test_query_bus_behavior_can_modify_result():
    """Test that behaviors can modify the result."""
    # Arrange
    bus = SimpleQueryBus()
    bus.register_handler(TestQuery, TestQueryHandler)
    
    async def modifying_behavior(request, next_handler):
        result = await next_handler(request)
        return f"Modified: {result}"
    
    bus.add_behavior(modifying_behavior)
    
    query = TestQuery("test")
    
    # Act
    result = await bus.send(query)
    
    # Assert
    assert result == "Modified: Result: test"

def test_query_bus_add_behavior():
    """Test that query bus can add behaviors."""
    # Arrange
    bus = SimpleQueryBus()
    
    async def test_behavior(request, next_handler):
        return await next_handler(request)
    
    # Act
    bus.add_behavior(test_behavior)
    
    # Assert
    assert len(bus._behaviors) == 1
    assert bus._behaviors[0] == test_behavior

# Caching Tests

@pytest.mark.asyncio
async def test_query_bus_caching_basic_functionality():
    """Test basic caching functionality."""
    # Arrange
    cache = MockCacheProvider()
    bus = SimpleQueryBus(cache_provider=cache)
    bus.register_handler(TestQuery, TestQueryHandler)
    bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    query = TestQuery("test")
    
    # Act - First call should execute handler and cache result
    result1 = await bus.send(query)
    
    # Act - Second call should return cached result
    result2 = await bus.send(query)
    
    # Assert
    assert result1 == "Result: test"
    assert result2 == "Result: test"
    
    # Should have called cache.get twice (miss, then hit)
    assert len(cache.get_calls) == 2
    # Should have called cache.set once (after first execution)
    assert len(cache.set_calls) == 1
    assert cache.set_calls[0][1] == "Result: test"  # cached value
    assert cache.set_calls[0][2] == 300  # TTL

@pytest.mark.asyncio
async def test_query_bus_caching_cache_miss():
    """Test behavior when cache miss occurs."""
    # Arrange
    cache = MockCacheProvider()
    bus = SimpleQueryBus(cache_provider=cache)
    bus.register_handler(TestQuery, TestQueryHandler)
    bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    query = TestQuery("test")
    
    # Act
    result = await bus.send(query)
    
    # Assert
    assert result == "Result: test"
    assert len(cache.get_calls) == 1  # Cache miss
    assert len(cache.set_calls) == 1  # Result cached

@pytest.mark.asyncio
async def test_query_bus_caching_cache_hit():
    """Test behavior when cache hit occurs."""
    # Arrange
    cache = MockCacheProvider()
    # Pre-populate cache
    cache_key = "query:TestQuery:5d41402abc4b2a76b9719d911017c592"  # MD5 of {"value": "test"}
    await cache.set(cache_key, "Cached result")
    
    bus = SimpleQueryBus(cache_provider=cache)
    bus.register_handler(TestQuery, TestQueryHandler)
    bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    query = TestQuery("test")
    
    # Act
    result = await bus.send(query)
    
    # Assert
    assert result == "Cached result"
    assert len(cache.get_calls) == 1  # Cache hit
    assert len(cache.set_calls) == 1  # Only the pre-population call

def test_query_bus_enable_caching_without_provider():
    """Test that enabling caching without provider raises error."""
    # Arrange
    bus = SimpleQueryBus()  # No cache provider
    
    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    assert "no cache provider configured" in str(exc_info.value)

def test_query_bus_disable_caching():
    """Test disabling caching for a query type."""
    # Arrange
    cache = MockCacheProvider()
    bus = SimpleQueryBus(cache_provider=cache)
    bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    # Act
    bus.disable_caching_for(TestQuery)
    
    # Assert
    assert TestQuery not in bus._cached_queries

@pytest.mark.asyncio
async def test_query_bus_invalidate_cache():
    """Test cache invalidation."""
    # Arrange
    cache = MockCacheProvider()
    bus = SimpleQueryBus(cache_provider=cache)
    bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    query = TestQuery("test")
    
    # Pre-populate cache
    await bus.send(query)  # This will cache the result
    
    # Act
    await bus.invalidate_cache(query)
    
    # Assert
    assert len(cache.delete_calls) == 1

@pytest.mark.asyncio
async def test_query_bus_cache_key_generation():
    """Test that cache keys are generated consistently."""
    # Arrange
    cache = MockCacheProvider()
    bus = SimpleQueryBus(cache_provider=cache)
    bus.register_handler(TestQuery, TestQueryHandler)
    bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    query1 = TestQuery("test")
    query2 = TestQuery("test")  # Same content
    query3 = TestQuery("different")  # Different content
    
    # Act
    await bus.send(query1)
    await bus.send(query2)
    await bus.send(query3)
    
    # Assert
    # query1 and query2 should generate the same cache key
    assert cache.get_calls[0] == cache.get_calls[1]
    # query3 should generate a different cache key
    assert cache.get_calls[0] != cache.get_calls[2]

@pytest.mark.asyncio
async def test_query_bus_caching_with_cache_failure():
    """Test that cache failures don't break query execution."""
    # Arrange
    cache = Mock()
    cache.get = AsyncMock(side_effect=Exception("Cache get failed"))
    cache.set = AsyncMock(side_effect=Exception("Cache set failed"))
    
    bus = SimpleQueryBus(cache_provider=cache)
    bus.register_handler(TestQuery, TestQueryHandler)
    bus.enable_caching_for(TestQuery, ttl_seconds=300)
    
    query = TestQuery("test")
    
    # Act - Should not raise exception despite cache failures
    result = await bus.send(query)
    
    # Assert
    assert result == "Result: test"

@pytest.mark.asyncio
async def test_query_bus_without_caching():
    """Test that queries work normally without caching enabled."""
    # Arrange
    cache = MockCacheProvider()
    bus = SimpleQueryBus(cache_provider=cache)
    bus.register_handler(TestQuery, TestQueryHandler)
    # Note: Not enabling caching for TestQuery
    
    query = TestQuery("test")
    
    # Act
    result = await bus.send(query)
    
    # Assert
    assert result == "Result: test"
    # Cache should not be used
    assert len(cache.get_calls) == 0
    assert len(cache.set_calls) == 0