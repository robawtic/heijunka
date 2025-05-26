import os
import sys
import unittest
from unittest.mock import patch
from dotenv import load_dotenv

# Add the project root to the path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.config.settings import settings
from domain.models.db import DATABASE_URL, engine


class TestEnvironmentConfig(unittest.TestCase):
    """Test that environment variables are correctly loaded and used."""

    def setUp(self):
        """Set up test environment."""
        # Ensure environment variables are loaded
        load_dotenv()

    def test_settings_loaded(self):
        """Test that settings are loaded from environment variables."""
        # Check that required settings are loaded
        self.assertIsNotNone(settings.jwt_secret_key)
        self.assertIsNotNone(settings.database_url)
        
        # Check that optional settings have default values
        self.assertEqual(settings.jwt_expiration_minutes, 30)
        self.assertEqual(settings.periods, 4)
        self.assertEqual(settings.max_solve_time, 60)
        self.assertEqual(settings.lookback, 3)

    def test_database_url(self):
        """Test that the database URL is correctly loaded from settings."""
        # Check that the database URL in domain/models/db.py matches the one in settings
        self.assertEqual(DATABASE_URL, settings.database_url)
        
        # Check that the engine is created with the correct URL
        self.assertEqual(str(engine.url), settings.database_url)

    @patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"})
    def test_override_database_url(self):
        """Test that the database URL can be overridden with an environment variable."""
        # Reload settings to pick up the new environment variable
        from importlib import reload
        import infrastructure.config.settings
        reload(infrastructure.config.settings)
        from infrastructure.config.settings import settings
        
        # Check that the database URL is updated
        self.assertEqual(settings.database_url, "sqlite:///test.db")


if __name__ == '__main__':
    unittest.main()