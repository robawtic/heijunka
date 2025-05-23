import unittest
import os
import tempfile
from unittest.mock import patch, mock_open

from utilities.utility import load_config, setup_logging


class TestUtility(unittest.TestCase):
    def test_load_config(self):
        """Test that load_config correctly loads a YAML file."""
        # Create a temporary YAML file
        yaml_content = """
        periods: 4
        database_url: "sqlite:///test.db"
        """
        
        # Mock the open function to return our YAML content
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = load_config("dummy_path.yaml")
        
        # Verify the config was loaded correctly
        self.assertEqual(config["periods"], 4)
        self.assertEqual(config["database_url"], "sqlite:///test.db")
    
    def test_setup_logging(self):
        """Test that setup_logging configures logging correctly."""
        # This is a simple test that just verifies the function runs without error
        config = {}
        setup_logging(config)
        # No assertion needed, we're just checking it doesn't raise an exception


if __name__ == "__main__":
    unittest.main()