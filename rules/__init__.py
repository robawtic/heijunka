# rules/__init__.py
import warnings
warnings.warn("The 'rules' package has moved to 'domain.rules'. Please update your imports.", DeprecationWarning, stacklevel=2)
from domain.rules import *