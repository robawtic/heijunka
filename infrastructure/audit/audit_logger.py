import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

class AuditLogger:
    """
    Logger for auditing sensitive operations.
    
    This class provides methods for logging user actions for auditing purposes.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the audit logger.
        
        Args:
            logger: The logger to use. If None, a new logger will be created.
        """
        self.logger = logger or logging.getLogger("heijunka_api.audit")
    
    def log_action(self, user: Dict[str, Any], action: str, resource_type: str, 
                  resource_id: Any, details: Optional[Dict[str, Any]] = None):
        """
        Log an audit event for a user action.
        
        Args:
            user: The user performing the action
            action: The action being performed (create, update, delete, etc.)
            resource_type: The type of resource being acted upon
            resource_id: The ID of the resource
            details: Additional details about the action
        """
        audit_event = {
            "timestamp": datetime.now().isoformat(),
            "user": user.get("username", "unknown"),
            "roles": user.get("roles", []),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {}
        }
        
        self.logger.info(f"AUDIT: {json.dumps(audit_event)}")
        
        # In a real implementation, you might also store this in a database
        # or send it to a centralized logging system

# Singleton instance
audit_logger = AuditLogger()

def get_audit_logger():
    """
    Get the audit logger instance.
    
    Returns:
        The audit logger instance
    """
    return audit_logger