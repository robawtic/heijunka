# models.py
"""
This module is maintained for backward compatibility.
New code should import from domain.models.model_loader directly.
"""
import warnings

warnings.warn(
    "The 'models' module has been moved to 'domain.models.model_loader'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2
)

from domain.models.model_loader import load_models
