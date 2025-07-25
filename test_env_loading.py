#!/usr/bin/env python3
"""
Test script to verify environment variable loading.
"""

import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_env_loading():
    """Test environment variable loading."""
    print("Testing environment variable loading...")
    
    # Check environment before loading .env
    print(f"LOG_LEVEL before load_dotenv: {os.environ.get('LOG_LEVEL', 'NOT SET')}")
    
    # Load .env file
    load_dotenv()
    print("✓ load_dotenv() called")
    
    # Check environment after loading .env
    print(f"LOG_LEVEL after load_dotenv: {os.environ.get('LOG_LEVEL', 'NOT SET')}")
    
    # Import settings after loading .env
    from infrastructure.config.settings import settings
    print(f"Settings log_level: {settings.log_level}")
    print(f"Settings environment: {settings.environment}")
    
    # Test with explicit environment variable
    os.environ['LOG_LEVEL'] = 'INFO'
    print(f"LOG_LEVEL after manual set: {os.environ.get('LOG_LEVEL')}")
    
    # Re-import settings to see if it picks up the change
    import importlib
    import infrastructure.config.settings
    importlib.reload(infrastructure.config.settings)
    from infrastructure.config.settings import settings as new_settings
    print(f"New settings log_level: {new_settings.log_level}")

if __name__ == "__main__":
    test_env_loading()