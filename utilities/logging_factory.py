import logging
import time
import threading
from typing import Dict, Any, Optional, List, Union, Callable
from infrastructure.config.settings import settings

class RateLimitedLogger:
    """
    Rate-limited logger that prevents log flooding for high-frequency operations.

    This class ensures that similar log messages are not logged more than
    a specified number of times within a time window.
    """

    def __init__(self, logger: logging.Logger, window_seconds: int = 60, max_count: int = 5):
        """
        Initialize the rate-limited logger.

        Args:
            logger: The logger to use
            window_seconds: Time window in seconds
            max_count: Maximum number of similar logs in the window
        """
        self.logger = logger
        self.window_seconds = window_seconds
        self.max_count = max_count
        self.log_counters: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()

    def _get_counter_key(self, event_type: str, identifier: str) -> str:
        """Generate a unique key for the log counter."""
        return f"{event_type}:{identifier}"

    def debug(self, msg: str, event_type: str, identifier: str, 
             extra: Optional[Dict[str, Any]] = None, *args, **kwargs):
        """
        Log a debug message with rate limiting.

        Args:
            msg: The log message
            event_type: Type of event (e.g., 'username_check', 'email_check')
            identifier: Unique identifier for the event (e.g., username, email)
            extra: Extra data for structured logging
        """
        self._log(msg, "debug", event_type, identifier, extra, *args, **kwargs)

    def info(self, msg: str, event_type: str, identifier: str, 
             extra: Optional[Dict[str, Any]] = None, *args, **kwargs):
        """
        Log an info message with rate limiting.

        Args:
            msg: The log message
            event_type: Type of event (e.g., 'username_check', 'email_check')
            identifier: Unique identifier for the event (e.g., username, email)
            extra: Extra data for structured logging
        """
        self._log(msg, "info", event_type, identifier, extra, *args, **kwargs)

    def warning(self, msg: str, event_type: str, identifier: str, 
               extra: Optional[Dict[str, Any]] = None, *args, **kwargs):
        """
        Log a warning message with rate limiting.

        Args:
            msg: The log message
            event_type: Type of event (e.g., 'username_check', 'email_check')
            identifier: Unique identifier for the event (e.g., username, email)
            extra: Extra data for structured logging
        """
        self._log(msg, "warning", event_type, identifier, extra, *args, **kwargs)

    def error(self, msg: str, event_type: str, identifier: str, 
             extra: Optional[Dict[str, Any]] = None, *args, **kwargs):
        """
        Log an error message with rate limiting.

        Args:
            msg: The log message
            event_type: Type of event (e.g., 'username_check', 'email_check')
            identifier: Unique identifier for the event (e.g., username, email)
            extra: Extra data for structured logging
        """
        self._log(msg, "error", event_type, identifier, extra, *args, **kwargs)

    def critical(self, msg: str, event_type: str, identifier: str, 
                extra: Optional[Dict[str, Any]] = None, *args, **kwargs):
        """
        Log a critical message with rate limiting.

        Args:
            msg: The log message
            event_type: Type of event (e.g., 'username_check', 'email_check')
            identifier: Unique identifier for the event (e.g., username, email)
            extra: Extra data for structured logging
        """
        self._log(msg, "critical", event_type, identifier, extra, *args, **kwargs)

    def _log(self, msg: str, level: str, event_type: str, identifier: str, 
            extra: Optional[Dict[str, Any]] = None, *args, **kwargs):
        """
        Internal method to log a message with rate limiting.

        Args:
            msg: The log message
            level: Log level (debug, info, warning, error, critical)
            event_type: Type of event
            identifier: Unique identifier for the event
            extra: Extra data for structured logging
        """
        # Make a copy of kwargs to avoid modifying the original
        kwargs_copy = kwargs.copy()

        # Remove event_type from kwargs if it exists to prevent passing it to the standard logger
        if 'event_type' in kwargs_copy:
            del kwargs_copy['event_type']

        with self.lock:
            counter_key = self._get_counter_key(event_type, identifier)
            now = time.time()

            # Initialize or update counter
            if counter_key not in self.log_counters:
                self.log_counters[counter_key] = {
                    'count': 0,
                    'first_seen': now,
                    'last_logged': 0
                }

            counter = self.log_counters[counter_key]

            # Reset counter if window has passed
            if now - counter['first_seen'] > self.window_seconds:
                counter['count'] = 0
                counter['first_seen'] = now

            # Increment counter
            counter['count'] += 1

            # Determine if we should log
            should_log = counter['count'] <= self.max_count

            # Always log the first occurrence
            if counter['count'] == 1:
                should_log = True

            # Log summary at the end of the window
            if counter['count'] == self.max_count + 1:
                summary_extra = extra.copy() if extra else {}
                summary_extra.update({
                    'rate_limited': True,
                    'event_type': event_type,
                    'message': f"Rate limiting similar logs for {event_type}"
                })
                log_func = getattr(self.logger, level)
                log_func(
                    f"Rate limiting activated for {event_type}. Further similar logs will be suppressed for this window.", 
                    extra=summary_extra,
                    *args, **kwargs_copy
                )

            if should_log:
                counter['last_logged'] = now
                if extra is None:
                    extra = {}
                extra['event_type'] = event_type
                log_func = getattr(self.logger, level)
                log_func(msg, extra=extra, *args, **kwargs_copy)

    def get_suppression_stats(self) -> Dict[str, int]:
        """
        Get statistics about suppressed log messages.

        Returns:
            Dictionary mapping counter keys to counts for suppressed messages
        """
        with self.lock:
            return {
                key: counter['count']
                for key, counter in self.log_counters.items()
                if counter['count'] > self.max_count
            }

# Cache for loggers to avoid creating multiple instances
_logger_cache: Dict[str, Union[logging.Logger, RateLimitedLogger]] = {}

def get_logger(name: str, rate_limit: bool = False, 
              window_seconds: int = 60, max_count: int = 5) -> Union[logging.Logger, RateLimitedLogger]:
    """
    Get a logger instance with optional rate limiting.

    Args:
        name: The name of the logger
        rate_limit: Whether to enable rate limiting
        window_seconds: Time window in seconds for rate limiting
        max_count: Maximum number of similar logs in the window for rate limiting

    Returns:
        A logger instance (either standard Logger or RateLimitedLogger)
    """
    cache_key = f"{name}:{rate_limit}:{window_seconds}:{max_count}"

    if cache_key in _logger_cache:
        return _logger_cache[cache_key]

    logger = logging.getLogger(name)

    if rate_limit:
        logger = RateLimitedLogger(logger, window_seconds, max_count)

    _logger_cache[cache_key] = logger
    return logger

# Global function to get all suppression stats from rate-limited loggers
def get_all_suppression_stats() -> Dict[str, Dict[str, int]]:
    """
    Get suppression statistics from all rate-limited loggers.

    Returns:
        Dictionary mapping logger names to their suppression stats
    """
    stats = {}
    for cache_key, logger in _logger_cache.items():
        if isinstance(logger, RateLimitedLogger):
            logger_name = cache_key.split(':')[0]
            stats[logger_name] = logger.get_suppression_stats()
    return stats
