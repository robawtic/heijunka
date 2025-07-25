#!/usr/bin/env python3
"""
Debug script to investigate logging configuration issues.
"""

import sys
import os
import logging
import logging.config

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.config.settings import settings
from infrastructure.logging.config import ensure_log_directory

def debug_logging_config():
    """Debug the logging configuration step by step."""
    print("Debugging logging configuration...")
    
    # Check settings
    print(f"Log level: {settings.log_level}")
    print(f"Log directory: {settings.log_dir}")
    print(f"Environment: {settings.environment}")
    
    # Ensure log directory
    ensure_log_directory(settings.log_dir)
    print("✓ Log directory ensured")
    
    # Create log file paths
    log_dir = settings.log_dir
    app_log_path = os.path.join(log_dir, 'heijunka.log')
    audit_log_path = os.path.join(log_dir, 'audit.log')
    
    print(f"App log path: {app_log_path}")
    print(f"Audit log path: {audit_log_path}")
    
    # Check if files exist and are writable
    try:
        with open(app_log_path, 'a') as f:
            f.write("# Test write\n")
        print("✓ App log file is writable")
    except Exception as e:
        print(f"✗ App log file write error: {e}")
    
    # Create a simple logging configuration
    simple_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'simple',
                'filename': app_log_path,
                'level': 'DEBUG',
            },
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'level': 'DEBUG',
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    }
    
    print("\nApplying simple logging configuration...")
    try:
        logging.config.dictConfig(simple_config)
        print("✓ Simple logging configuration applied")
    except Exception as e:
        print(f"✗ Error applying simple config: {e}")
        return
    
    # Test simple logging
    print("\nTesting simple logging...")
    logger = logging.getLogger("debug_test")
    logger.info("Test message from debug script")
    logger.warning("Test warning from debug script")
    logger.error("Test error from debug script")
    
    print("✓ Simple logging calls made")
    
    # Force flush
    for handler in logging.getLogger().handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
    
    print("✓ Handlers flushed")
    
    # Check file size
    try:
        file_size = os.path.getsize(app_log_path)
        print(f"Log file size after test: {file_size} bytes")
    except Exception as e:
        print(f"Error checking file size: {e}")

if __name__ == "__main__":
    debug_logging_config()