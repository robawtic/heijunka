import yaml
import logging
from typing import Dict, Any, Optional

# Define the schema for config.yaml
CONFIG_SCHEMA = {
    'periods': {'type': int, 'required': True, 'default': 4},
    'database_url': {'type': str, 'required': True, 'default': "sqlite:///schedule.db"},
    'max_solve_time': {'type': int, 'required': False, 'default': 60},
    'start_date': {'type': str, 'required': False, 'default': None},
    'lookback': {'type': int, 'required': False, 'default': 3},
    'offline_periods': {'type': dict, 'required': False, 'default': {}},
}

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the configuration against the schema.

    Args:
        config: The configuration dictionary to validate

    Returns:
        The validated configuration with default values applied

    Raises:
        ValueError: If the configuration is invalid
    """
    validated = {}

    # Check for required fields and apply defaults
    for field, schema in CONFIG_SCHEMA.items():
        if field in config:
            # Validate type
            if not isinstance(config[field], schema['type']):
                raise ValueError(f"Config field '{field}' must be of type {schema['type'].__name__}")
            validated[field] = config[field]
        elif schema['required']:
            # Use default for required fields
            validated[field] = schema['default']
        elif schema['default'] is not None:
            # Use default for optional fields if available
            validated[field] = schema['default']

    # Check for unknown fields
    for field in config:
        if field not in CONFIG_SCHEMA:
            logging.warning(f"Unknown configuration field: {field}")

    return validated

def load_config(path: str) -> Dict[str, Any]:
    """
    Load and validate configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file

    Returns:
        The validated configuration dictionary

    Raises:
        FileNotFoundError: If the configuration file does not exist
        ValueError: If the configuration is invalid
    """
    with open(path) as f:
        config = yaml.safe_load(f)

    # Validate the configuration
    return validate_config(config)

def setup_logging(config: Dict[str, Any]) -> None:
    """
    Set up logging based on the configuration.

    Args:
        config: The configuration dictionary
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )
