#!/usr/bin/env python3
"""
Simple test script to verify logging configuration.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.logging.config import configure_logging
from utilities.logging_factory import get_logger
import logging

def test_logging():
    """Test different logging approaches to identify the issue."""
    print("Testing logging configuration...")
    
    # Configure logging
    configure_logging()
    print("✓ Logging configured")
    
    # Test 1: Direct standard logger
    print("\n1. Testing direct standard logger...")
    std_logger = logging.getLogger("test.standard")
    std_logger.info("Test message from standard logger")
    print("✓ Standard logger call made")
    
    # Test 2: Standard logger with heijunka prefix
    print("\n2. Testing standard logger with heijunka prefix...")
    heijunka_logger = logging.getLogger("heijunka.test")
    heijunka_logger.info("Test message from heijunka logger")
    print("✓ Heijunka logger call made")
    
    # Test 3: RateLimitedLogger
    print("\n3. Testing RateLimitedLogger...")
    rate_limited_logger = get_logger("test.ratelimited", rate_limit=True)
    rate_limited_logger.info("Test message from RateLimitedLogger", "test_event", "test_id")
    print("✓ RateLimitedLogger call made")
    
    # Test 4: RateLimitedLogger with heijunka prefix
    print("\n4. Testing RateLimitedLogger with heijunka prefix...")
    heijunka_rate_limited = get_logger("heijunka.test.ratelimited", rate_limit=True)
    heijunka_rate_limited.info("Test message from heijunka RateLimitedLogger", "test_event", "test_id")
    print("✓ Heijunka RateLimitedLogger call made")
    
    # Test 5: Root logger
    print("\n5. Testing root logger...")
    root_logger = logging.getLogger()
    root_logger.info("Test message from root logger")
    print("✓ Root logger call made")
    
    print("\nAll logging calls completed. Check the log file to see which ones worked.")

if __name__ == "__main__":
    test_logging()