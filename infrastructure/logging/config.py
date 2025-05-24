import logging
import logging.config
import os
import threading
from pythonjsonlogger import jsonlogger
import uuid
from typing import Optional

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

class RequestIdFilter(logging.Filter):
    def __init__(self, request_id_getter):
        super().__init__()
        self.request_id_getter = request_id_getter
        
    def filter(self, record):
        request_id = self.request_id_getter()
        if request_id:
            record.request_id = request_id
        return True

def configure_logging(log_level: str = "INFO"):
    """Configure structured JSON logging."""
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
        },
        'filters': {
            'request_id': {
                '()': RequestIdFilter,
                'request_id_getter': get_request_id,
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'json',
                'filters': ['request_id'],
                'level': log_level,
            },
        },
        'loggers': {
            'heijunka_api': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': False,
            },
            'uvicorn': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console'],
            'level': log_level,
        },
    }
    
    logging.config.dictConfig(log_config)

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