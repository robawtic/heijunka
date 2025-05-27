import re
import os
import logging
from typing import Any, Dict, List, Union, Optional, Callable
from infrastructure.config.settings import settings

class SensitiveDataRedactor:
    """
    Utility class for redacting sensitive information in log messages.

    Supports different redaction levels:
    - none: No redaction (use only in development)
    - low: Partial redaction (show initials, partial IDs)
    - high: Full redaction (completely mask sensitive data)
    """

    def __init__(self, redaction_level: str = None):
        """
        Initialize the redactor with the specified redaction level.

        Args:
            redaction_level: The redaction level to use. If None, uses the value from settings.
        """
        self.redaction_level = redaction_level or settings.redaction_level
        if self.redaction_level not in ["none", "low", "high"]:
            raise ValueError(f"Invalid redaction level: {self.redaction_level}. Must be one of: none, low, high")

    def redact_text(self, text: str, data_type: str) -> str:
        """
        Redact a piece of text based on its data type and the configured redaction level.

        Args:
            text: The text to redact
            data_type: The type of data (e.g., 'employee_name', 'team_name', 'file_path')

        Returns:
            The redacted text
        """
        if not text or self.redaction_level == "none":
            return text

        text_str = str(text)

        if self.redaction_level == "low":
            # Low redaction - show partial information
            if 'name' in data_type:
                # For names, show initials
                parts = text_str.split()
                if len(parts) > 1:
                    # For full names (first last), show first initial and last initial
                    return f"{parts[0][0]}. {parts[-1][0]}."
                else:
                    # For single names, show first and last character
                    if len(text_str) > 2:
                        return f"{text_str[0]}...{text_str[-1]}"
                    else:
                        return f"{text_str[0]}*"
            elif 'id' in data_type:
                # For IDs, show first and last character
                if len(text_str) > 4:
                    return f"{text_str[:2]}...{text_str[-2:]}"
                else:
                    return f"{text_str[0]}{'*' * (len(text_str) - 1)}"
            elif 'path' in data_type or 'file' in data_type:
                # For paths, show only the filename
                return os.path.basename(text_str)
            elif 'date' in data_type:
                # For dates, show only the year
                if re.match(r'\d{4}-\d{2}-\d{2}', text_str):
                    return f"{text_str[:4]}-**-**"
                else:
                    return "****-**-**"
            else:
                # Default low redaction
                if len(text_str) > 4:
                    return f"{text_str[:2]}...{text_str[-2:]}"
                else:
                    return f"{text_str[0]}{'*' * (len(text_str) - 1)}"
        else:  # high redaction
            # High redaction - completely mask information
            if settings.include_redacted_metadata:
                # Include metadata about the redacted value
                if 'name' in data_type:
                    return f"[REDACTED NAME: {text_str}]"
                elif 'id' in data_type:
                    return f"[REDACTED ID: {text_str}]"
                elif 'path' in data_type or 'file' in data_type:
                    return f"[REDACTED PATH: {text_str}]"
                elif 'date' in data_type:
                    return f"[REDACTED DATE: {text_str}]"
                else:
                    return f"[REDACTED: {text_str}]"
            else:
                # Standard high redaction without metadata
                if 'name' in data_type:
                    parts = text_str.split()
                    if len(parts) > 1:
                        # For full names, replace with [REDACTED NAME]
                        return "[REDACTED NAME]"
                    else:
                        # For single names, replace with [REDACTED]
                        return "[REDACTED]"
                elif 'id' in data_type:
                    return f"[REDACTED ID]"
                elif 'path' in data_type or 'file' in data_type:
                    return "[REDACTED PATH]"
                elif 'date' in data_type:
                    return "[REDACTED DATE]"
                else:
                    # Default high redaction
                    return "[REDACTED]"

    def redact_message(self, message: str, sensitive_data: Dict[str, Union[str, List[str]]]) -> str:
        """
        Redact sensitive information in a log message.

        Args:
            message: The log message to redact
            sensitive_data: Dictionary mapping data types to values or patterns to redact
                            e.g. {'employee_name': ['John Doe', 'Jane Smith'], 
                                  'employee_id': ['123456', '789012']}

        Returns:
            Redacted log message
        """
        if self.redaction_level == "none":
            return message

        result = message

        # Process each type of sensitive data
        for data_type, values in sensitive_data.items():
            if isinstance(values, list):
                # Replace exact values
                for value in values:
                    if value and str(value) in result:
                        redacted = self.redact_text(str(value), data_type)
                        result = result.replace(str(value), redacted)
            elif isinstance(values, str) and values.startswith(r'\b'):
                # Apply regex pattern redaction
                pattern = values
                result = re.sub(pattern, 
                               lambda m: self.redact_text(m.group(0), data_type), 
                               result)

        return result

# Global redactor instance
_redactor = SensitiveDataRedactor()

def redact_log_message(message: str, 
                     employee_names: List[str] = None,
                     employee_ids: List[str] = None, 
                     team_names: List[str] = None,
                     team_ids: List[str] = None,
                     workstation_names: List[str] = None,
                     file_paths: List[str] = None,
                     dates: List[str] = None,
                     custom_data: Dict[str, List[str]] = None) -> str:
    """
    Redact a log message by masking sensitive information.

    Args:
        message: The log message to redact
        employee_names: List of employee names to redact
        employee_ids: List of employee IDs to redact
        team_names: List of team names to redact
        team_ids: List of team IDs to redact
        workstation_names: List of workstation names to redact
        file_paths: List of file paths to redact
        dates: List of dates to redact
        custom_data: Dictionary of custom data types and values to redact

    Returns:
        Redacted log message
    """
    sensitive_data = {}

    if employee_names:
        sensitive_data['employee_name'] = employee_names
    if employee_ids:
        sensitive_data['employee_id'] = employee_ids
    if team_names:
        sensitive_data['team_name'] = team_names
    if team_ids:
        sensitive_data['team_id'] = team_ids
    if workstation_names:
        sensitive_data['workstation_name'] = workstation_names
    if file_paths:
        sensitive_data['file_path'] = file_paths
    if dates:
        sensitive_data['date'] = dates
    if custom_data:
        sensitive_data.update(custom_data)

    return _redactor.redact_message(message, sensitive_data)

def get_redactor(redaction_level: Optional[str] = None) -> SensitiveDataRedactor:
    """
    Get a redactor instance with the specified redaction level.

    Args:
        redaction_level: The redaction level to use. If None, uses the global redactor.

    Returns:
        A SensitiveDataRedactor instance
    """
    if redaction_level is None:
        return _redactor
    else:
        return SensitiveDataRedactor(redaction_level)

def sanitize_exception(exc: Exception) -> str:
    """
    Sanitize exception messages by redacting sensitive information.

    Args:
        exc: The exception to sanitize

    Returns:
        Sanitized exception message
    """
    # Extract common patterns that might be sensitive
    message = str(exc)

    # Extract potential employee names (assuming names are capitalized words)
    employee_names = []
    import re
    # Look for patterns like "John Doe", "Jane Smith", etc.
    name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
    employee_names.extend(re.findall(name_pattern, message))

    # Extract potential IDs (numeric sequences)
    employee_ids = []
    id_pattern = r'\b\d{4,}\b'  # IDs with 4+ digits
    employee_ids.extend(re.findall(id_pattern, message))

    # Extract potential dates
    dates = []
    date_pattern = r'\b\d{4}-\d{2}-\d{2}\b'  # YYYY-MM-DD format
    dates.extend(re.findall(date_pattern, message))

    # Now redact the message with the extracted sensitive data
    return redact_log_message(
        message,
        employee_names=employee_names,
        employee_ids=employee_ids,
        dates=dates
    )

# Lazy-loaded audit logger
_audit_logger = None

def get_audit_logger():
    """
    Get the audit logger instance.

    Returns:
        The audit logger
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = logging.getLogger("heijunka.audit")
    return _audit_logger

def log_audit_event(event_type: str, 
                   message: str, 
                   user_id: Optional[str] = None,
                   employee_names: List[str] = None,
                   employee_ids: List[str] = None, 
                   team_names: List[str] = None,
                   team_ids: List[str] = None,
                   workstation_names: List[str] = None,
                   file_paths: List[str] = None,
                   dates: List[str] = None,
                   custom_data: Dict[str, Any] = None,
                   level: str = "INFO") -> None:
    """
    Log an audit event with full details for security tracking.

    This function logs both:
    1. A redacted message to the standard log
    2. A full detailed message to the audit log

    Args:
        event_type: Type of event (e.g., 'override', 'force_assignment', 'deletion')
        message: The log message
        user_id: ID of the user performing the action
        employee_names: List of employee names involved
        employee_ids: List of employee IDs involved
        team_names: List of team names involved
        team_ids: List of team IDs involved
        workstation_names: List of workstation names involved
        file_paths: List of file paths involved
        dates: List of dates involved
        custom_data: Dictionary of custom data to include in the audit log
        level: Log level (default: INFO)
    """
    # Get the standard logger
    logger = logging.getLogger("heijunka")

    # Get the audit logger
    audit_logger = get_audit_logger()

    # Create the redacted message for standard logs
    redacted_message = f"AUDIT: {event_type} - {message}"

    # Create the full audit data
    audit_data = {
        "event_type": event_type,
        "message": message,
        "user_id": user_id
    }

    # Add optional data if provided
    if employee_names:
        audit_data["employee_names"] = employee_names
    if employee_ids:
        audit_data["employee_ids"] = employee_ids
    if team_names:
        audit_data["team_names"] = team_names
    if team_ids:
        audit_data["team_ids"] = team_ids
    if workstation_names:
        audit_data["workstation_names"] = workstation_names
    if file_paths:
        audit_data["file_paths"] = file_paths
    if dates:
        audit_data["dates"] = dates
    if custom_data:
        audit_data.update(custom_data)

    # Log to standard logger (redacted)
    log_func = getattr(logger, level.lower())
    log_func(redact_log_message(
        redacted_message,
        employee_names=employee_names,
        employee_ids=employee_ids,
        team_names=team_names,
        team_ids=team_ids,
        workstation_names=workstation_names,
        file_paths=file_paths,
        dates=dates
    ))

    # Log to audit logger (full details)
    audit_log_func = getattr(audit_logger, level.lower())

    # Set the is_audit flag to prevent redaction
    extra = {"is_audit": True}

    # Log the full audit message
    audit_log_func(f"{event_type} - {message} - {audit_data}", extra=extra)
