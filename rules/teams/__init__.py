# rules/teams/__init__.py
import warnings
warnings.warn("'rules.teams' has moved to 'domain.rules.teams'. Please update your imports.", DeprecationWarning, stacklevel=2)
from domain.rules.teams import *