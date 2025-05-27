# Logging Enhancements Documentation

This document describes the logging enhancements implemented in the Heijunka project, including secure logging, rate limiting, metrics, and audit logging.

## Table of Contents

1. [Global Logger Factory](#global-logger-factory)
2. [Rate-Limited Logging](#rate-limited-logging)
3. [Log Suppression Metrics](#log-suppression-metrics)
4. [Structured Log Formatter](#structured-log-formatter)
5. [Replayable Audit Bus](#replayable-audit-bus)

## Global Logger Factory

The global logger factory provides a centralized way to create logger instances with optional rate limiting.

### Usage

```python
from utilities.logging_factory import get_logger

# Get a standard logger
logger = get_logger("heijunka.repositories.user")

# Get a rate-limited logger
rate_limited_logger = get_logger("heijunka.repositories.user", rate_limit=True)

# Get a rate-limited logger with custom settings
custom_logger = get_logger(
    "heijunka.repositories.user", 
    rate_limit=True, 
    window_seconds=120,  # 2-minute window
    max_count=10         # Allow 10 similar logs in the window
)
```

## Rate-Limited Logging

Rate-limited logging prevents log flooding for high-frequency operations by limiting the number of similar log messages within a time window.

### Usage

```python
# Using a rate-limited logger
rate_limited_logger = get_logger("heijunka.repositories.user", rate_limit=True)

# Log with event type and identifier
rate_limited_logger.info(
    "Checking if username exists", 
    event_type="username_check",
    identifier="johndoe",
    extra={"user_id": 123}
)

# After max_count similar logs within window_seconds, further logs are suppressed
# A summary message is logged when suppression begins
```

### Suppression Statistics

You can get statistics about suppressed log messages:

```python
from utilities.logging_factory import get_all_suppression_stats

# Get suppression stats for all rate-limited loggers
stats = get_all_suppression_stats()
print(stats)
# Example output: {'heijunka.repositories.user': {'username_check:johndoe': 42}}
```

## Log Suppression Metrics

Log suppression metrics are exposed through the Prometheus metrics endpoint at `/metrics`. These metrics show how many log messages have been suppressed for each logger and event type.

### Metrics Format

```
# HELP log_suppression_total Total number of suppressed log messages
# TYPE log_suppression_total gauge
log_suppression_total{logger_name="heijunka.repositories.user",event_type="username_check"} 42.0
```

## Structured Log Formatter

The structured log formatter ensures that logs include all necessary fields for analysis and monitoring.

### JSON Log Format

```json
{
  "timestamp": "2025-05-26T12:34:56.789Z",
  "level": "INFO",
  "logger": "heijunka.repositories.user",
  "message": "User login successful",
  "service": "heijunka-api",
  "hostname": "server1",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "user_login",
  "user_id": "123",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0 ...",
  "redacted": true,
  "redacted_fields": ["username"],
  "rate_limited": false
}
```

### Adding Context to Logs

```python
logger.info(
    "User login successful", 
    extra={
        "event_type": "user_login",
        "user_id": user.id,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }
)
```

## Replayable Audit Bus

The replayable audit bus provides a way to persist audit events to a file for later analysis or replay.

### Audit Event Structure

```python
@dataclass
class AuditEvent:
    id: str                     # Unique identifier
    timestamp: str              # ISO format timestamp
    user: Dict[str, Any]        # User information
    action: str                 # Action performed
    resource_type: str          # Type of resource
    resource_id: Any            # ID of resource
    details: Dict[str, Any]     # Additional details
```

### Logging Audit Events

```python
from infrastructure.audit.audit_logger import get_audit_logger

audit_logger = get_audit_logger()

# Log an audit event
audit_logger.log_action(
    user={"username": "admin", "roles": ["admin"]},
    action="create",
    resource_type="user",
    resource_id="123",
    details={"email": "user@example.com"}
)
```

### Subscribing to Audit Events

```python
from infrastructure.audit.bus import get_audit_event_bus

audit_bus = get_audit_event_bus()

# Define a subscriber function
def audit_subscriber(event):
    print(f"Audit event received: {event.action} {event.resource_type} {event.resource_id}")

# Subscribe to audit events
audit_bus.subscribe(audit_subscriber)
```

### Replaying Audit Events

```python
from infrastructure.audit.bus import get_audit_event_bus
from datetime import datetime, timedelta

audit_bus = get_audit_event_bus()

# Get yesterday's date
yesterday = datetime.now() - timedelta(days=1)

# Replay audit events with filters
events = audit_bus.replay_events(
    start_time=yesterday,
    user="admin",
    action="create",
    resource_type="user"
)

# Process the events
for event in events:
    print(f"{event.timestamp}: {event.user['username']} {event.action} {event.resource_type} {event.resource_id}")
```

## Best Practices

1. **Use Structured Logging**: Always include relevant context using the `extra` parameter.
2. **Rate Limit High-Frequency Logs**: Use rate-limited loggers for operations that might generate many similar logs.
3. **Redact Sensitive Information**: Use `redact_log_message()` for logs containing sensitive data.
4. **Sanitize Exceptions**: Use `sanitize_exception()` when logging exceptions.
5. **Audit Security-Relevant Events**: Use `log_action()` for security-relevant operations.
6. **Monitor Log Suppression**: Check the metrics endpoint to ensure logs aren't being excessively suppressed.
7. **Use Appropriate Log Levels**:
   - DEBUG: Detailed troubleshooting information
   - INFO: Normal operational information
   - WARNING: Potential issues that don't prevent operation
   - ERROR: Errors that prevent normal operation
   - CRITICAL: Critical errors that require immediate attention