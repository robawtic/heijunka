import unittest
from unittest.mock import patch, MagicMock
import logging
import io
import json
import infrastructure.logging.config

from utilities.secure_logging import (
    redact_log_message, 
    sanitize_exception, 
    SensitiveDataRedactor
)
from infrastructure.config.settings import settings
from infrastructure.logging.config import SecureLogFilter, CustomJsonFormatter


class TestSecureLogging(unittest.TestCase):
    """Test cases for secure logging functionality."""

    def test_redaction_of_employee_name(self):
        """Test that employee names are properly redacted."""
        message = "Created assignment for John Doe on 2024-05-26"
        redacted = redact_log_message(message, employee_names=["John Doe"])
        self.assertNotIn("John Doe", redacted)
        self.assertIn("[REDACTED", redacted)

    def test_redaction_with_metadata(self):
        """Test that redaction includes metadata when enabled."""
        # Save original setting
        original_setting = settings.include_redacted_metadata

        try:
            # Enable metadata in redaction
            settings.include_redacted_metadata = True

            message = "Employee John Doe assigned to station H010"
            redacted = redact_log_message(message, employee_names=["John Doe"])
            self.assertIn("[REDACTED NAME: John Doe]", redacted)

            # Disable metadata in redaction
            settings.include_redacted_metadata = False

            redacted = redact_log_message(message, employee_names=["John Doe"])
            self.assertNotIn("John Doe", redacted)
            self.assertNotIn("[REDACTED NAME: John Doe]", redacted)
            self.assertIn("[REDACTED NAME]", redacted)
        finally:
            # Restore original setting
            settings.include_redacted_metadata = original_setting

    def test_sanitize_exception(self):
        """Test that exception messages are properly sanitized."""
        # Create an exception with sensitive data
        exc = ValueError("Invalid data for employee John Doe with ID 12345")

        # Sanitize the exception
        sanitized = sanitize_exception(exc)

        # Verify sensitive data is redacted
        self.assertNotIn("John Doe", sanitized)
        self.assertIn("[REDACTED", sanitized)

    def test_redaction_of_multiple_sensitive_fields(self):
        """Test that multiple types of sensitive data are redacted."""
        message = "Team Alpha assigned John Doe (ID: 12345) to station H010 on 2024-05-26"
        redacted = redact_log_message(
            message,
            employee_names=["John Doe"],
            employee_ids=["12345"],
            team_names=["Alpha"],
            dates=["2024-05-26"]
        )

        # Verify all sensitive data is redacted
        self.assertNotIn("John Doe", redacted)
        self.assertNotIn("12345", redacted)
        self.assertNotIn("Alpha", redacted)
        self.assertNotIn("2024-05-26", redacted)

    def test_secure_log_filter_adds_redacted_flag(self):
        """Test that SecureLogFilter adds a redacted flag when redaction occurs."""
        # Create a log record with sensitive data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Employee John Doe assigned to station H010",
            args=(),
            exc_info=None
        )

        # Mock the redact_log_message function to simulate redaction
        original_redact = infrastructure.logging.config.redact_log_message

        try:
            # Replace with a mock that changes the message and returns a different value
            def mock_redact(message, **kwargs):
                return message.replace("John Doe", "[REDACTED NAME]")

            infrastructure.logging.config.redact_log_message = mock_redact

            # Apply the filter
            filter_instance = SecureLogFilter()
            filter_instance.filter(record)

            # Verify redacted flag is set
            self.assertTrue(hasattr(record, "redacted"))
            self.assertTrue(record.redacted)
        finally:
            # Restore the original function
            infrastructure.logging.config.redact_log_message = original_redact

        # Create a log record without sensitive data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Generic message without sensitive data",
            args=(),
            exc_info=None
        )

        # Apply the filter
        filter_instance.filter(record)

        # Verify redacted flag is not set (or is False)
        self.assertFalse(getattr(record, "redacted", False))

    def test_json_formatter_includes_redacted_flag(self):
        """Test that CustomJsonFormatter includes the redacted flag in JSON output."""
        # Create a formatter
        formatter = CustomJsonFormatter()

        # Create a log record with redacted flag
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Redacted message",
            args=(),
            exc_info=None
        )
        record.redacted = True

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        log_data = json.loads(formatted)

        # Verify redacted flag is included
        self.assertIn("redacted", log_data)
        self.assertTrue(log_data["redacted"])


if __name__ == "__main__":
    unittest.main()
