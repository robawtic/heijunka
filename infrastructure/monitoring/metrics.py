from prometheus_client import Counter, Histogram, Gauge, Info
import time
from utilities.logging_factory import get_all_suppression_stats

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

# Log suppression metrics
log_suppression_total = Gauge(
    'log_suppression_total',
    'Total number of suppressed log messages',
    ['logger_name', 'event_type']
)

def update_log_suppression_metrics():
    """
    Update the log suppression metrics with the current suppression statistics.
    This should be called before serving the metrics endpoint.
    """
    # Clear existing metrics to avoid stale data
    log_suppression_total._metrics.clear()

    # Get current suppression stats
    suppression_stats = get_all_suppression_stats()

    # Update metrics
    for logger_name, stats in suppression_stats.items():
        for counter_key, count in stats.items():
            # Extract event_type from counter_key (format: "event_type:identifier")
            event_type = counter_key.split(':', 1)[0] if ':' in counter_key else counter_key
            log_suppression_total.labels(logger_name=logger_name, event_type=event_type).set(count)

# Custom metrics endpoint that includes log suppression metrics
async def custom_metrics(request):
    """
    Custom metrics endpoint that updates log suppression metrics before serving.
    This function should be used instead of the starlette_prometheus metrics function.
    """
    from starlette_prometheus import metrics

    # Update log suppression metrics
    update_log_suppression_metrics()

    # Call the original metrics function
    return await metrics(request)

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
