import logging
import logging.config
import os
import threading
import stat
from pythonjsonlogger import jsonlogger
import uuid
from typing import Optional
from infrastructure.config.settings import settings
from utilities.secure_logging import redact_log_message

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['service'] = 'heijunka-api'
        log_record['hostname'] = os.environ.get('COMPUTERNAME', 'unknown')  # Windows-specific
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

        # Add request_id if available in thread context
        request_id = getattr(record, 'request_id', None)
        if request_id:
            log_record['request_id'] = request_id

        # Add redacted flag if present
        if hasattr(record, 'redacted') and record.redacted:
            log_record['redacted'] = True

class RequestIdFilter(logging.Filter):
    def __init__(self, request_id_getter):
        super().__init__()
        self.request_id_getter = request_id_getter

    def filter(self, record):
        request_id = self.request_id_getter()
        if request_id:
            record.request_id = request_id
        return True

class SecureLogFilter(logging.Filter):
    """Filter that redacts sensitive information in log messages."""

    def filter(self, record):
        # Don't modify audit logs - they should contain full information
        if getattr(record, 'is_audit', False):
            return True

        # Check if the message is already a string
        if isinstance(record.msg, str):
            original_msg = record.msg
            # Redact the message
            record.msg = redact_log_message(record.msg)

            # Add redacted flag if message was changed
            if record.msg != original_msg:
                record.redacted = True
        return True

def ensure_log_directory(log_dir):
    """
    Ensure the log directory exists and has proper permissions.

    Args:
        log_dir: Path to the log directory
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Set permissions to owner read/write only (600) on Windows
    # This is a best effort since Windows permissions are different from Unix
    try:
        # For the directory itself
        os.chmod(log_dir, stat.S_IRUSR | stat.S_IWUSR)

        # For any existing log files
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        logging.warning(f"Could not set permissions on log directory: {e}")

def configure_logging(log_level: str = None):
    """
    Configure structured JSON logging with secure log rotation and audit logging.

    Args:
        log_level: The logging level to use. If None, uses the value from settings.
    """
    # Use settings if log_level is not provided
    if log_level is None:
        log_level = settings.log_level

    # Ensure log directory exists with proper permissions
    log_dir = settings.log_dir
    ensure_log_directory(log_dir)

    # Create log file paths
    app_log_path = os.path.join(log_dir, 'heijunka.log')
    audit_log_path = os.path.join(log_dir, 'audit.log')

    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s',
            },
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
            'audit': {
                'format': '%(asctime)s - AUDIT - %(levelname)s - [%(request_id)s] - %(message)s',
            },
        },
        'filters': {
            'request_id': {
                '()': RequestIdFilter,
                'request_id_getter': get_request_id,
            },
            'secure_log': {
                '()': SecureLogFilter,
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'filters': ['request_id', 'secure_log'],
                'level': log_level,
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'standard',
                'filters': ['request_id', 'secure_log'],
                'filename': app_log_path,
                'maxBytes': settings.max_log_size_mb * 1024 * 1024,  # Convert MB to bytes
                'backupCount': settings.log_backup_count,
                'level': log_level,
            },
            'audit_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'audit',
                'filters': ['request_id'],  # No redaction for audit logs
                'filename': audit_log_path,
                'maxBytes': settings.max_log_size_mb * 1024 * 1024,  # Convert MB to bytes
                'backupCount': settings.log_backup_count,
                'level': 'INFO',
            },
        },
        'loggers': {
            'heijunka': {
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False,
            },
            'heijunka.audit': {
                'handlers': ['audit_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'uvicorn': {
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': log_level,
        },
    }

    # Apply configuration
    logging.config.dictConfig(log_config)

    # Set permissions on log files after they're created
    try:
        if os.path.exists(app_log_path):
            os.chmod(app_log_path, stat.S_IRUSR | stat.S_IWUSR)
        if os.path.exists(audit_log_path):
            os.chmod(audit_log_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        logging.warning(f"Could not set permissions on log files: {e}")

    # Create and return the audit logger
    audit_logger = logging.getLogger("heijunka.audit")
    return audit_logger

# Thread-local storage for request ID
_request_id_storage = {}

def set_request_id(request_id: str) -> None:
    """Set the request ID for the current thread."""
    _request_id_storage[threading.get_ident()] = request_id

def get_request_id() -> Optional[str]:
    """Get the request ID for the current thread."""
    return _request_id_storage.get(threading.get_ident())

def clear_request_id() -> None:
    """Clear the request ID for the current thread."""
    thread_id = threading.get_ident()
    if thread_id in _request_id_storage:
        del _request_id_storage[thread_id]

def log_startup_environment():
    """
    Log environment variables at startup with sensitive values masked.

    This function logs all environment variables, masking those that might contain
    sensitive information like secrets, passwords, or connection strings.
    """
    logger = logging.getLogger("heijunka")

    # Define keys that might contain sensitive information
    SENSITIVE_ENV_KEYS = {
        "JWT_SECRET_KEY", "CSRF_SECRET", "SECRET_KEY", "DATABASE_URL", 
        "REDIS_URL", "API_KEY", "PASSWORD", "TOKEN", "PRIVATE_KEY",
        "CERT", "CREDENTIALS", "AUTH", "ACCESS_KEY", "SECRET"
    }

    # Case-insensitive check for sensitive keys
    def is_sensitive(key):
        key_upper = key.upper()
        if any(sensitive in key_upper for sensitive in SENSITIVE_ENV_KEYS):
            return True
        # Check for common sensitive patterns
        return any(pattern in key_upper for pattern in ["SECRET", "PASSWORD", "KEY", "TOKEN", "CRED"])

    logger.info("Application environment variables (sensitive values masked):")
    for key, value in os.environ.items():
        # Mask sensitive values
        masked_value = "[REDACTED]" if is_sensitive(key) else value
        logger.info(f"{key} = {masked_value}")
