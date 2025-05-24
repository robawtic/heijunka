from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Define metrics
http_requests_total = Counter(
    'http_requests_total', 
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
)

active_requests = Gauge(
    'active_requests',
    'Number of active HTTP requests'
)

background_tasks_total = Counter(
    'background_tasks_total',
    'Total number of background tasks',
    ['name', 'status']
)

background_task_duration_seconds = Histogram(
    'background_task_duration_seconds',
    'Background task duration in seconds',
    ['name'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, float('inf'))
)

active_background_tasks = Gauge(
    'active_background_tasks',
    'Number of active background tasks'
)

api_info = Info('api_info', 'API information')
api_info.info({'version': '1.0.0', 'name': 'Heijunka API'})

# Middleware for metrics collection
class MetricsMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        path = scope["path"]
        method = scope["method"]
        
        # Skip metrics endpoint to avoid recursion
        if path == "/metrics":
            return await self.app(scope, receive, send)
        
        # Track active requests
        active_requests.inc()
        
        # Time the request
        start_time = time.time()
        
        # Create a wrapper for the send function to capture the status code
        original_send = send
        status_code = None
        
        async def wrapped_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await original_send(message)
        
        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            # Record metrics
            duration = time.time() - start_time
            if status_code:
                http_requests_total.labels(method=method, endpoint=path, status_code=status_code).inc()
                http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)
            
            # Decrement active requests
            active_requests.dec()