# domain/rules/context.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set, Callable, Union
from datetime import date
from ortools.sat.python.cp_model import CpModel
from sqlalchemy.orm import Session

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface

@dataclass(init=True)
class RuleContext:
    """
    Context object that holds all the data needed for scheduling rules.

    This class follows the Context design pattern, providing a consistent
    interface for all scheduling rules regardless of their specific needs.
    """
    model: CpModel
    assign: Dict[Tuple[int, int, int], Any]  # (employee_idx, workstation_idx, period) -> BoolVar
    employees: List[Employee]
    workstations: List[Workstation]
    periods: int
    start_date: Optional[date] = None
    lookback: Optional[int] = None
    session: Optional[Session] = None
    backup_idx: Optional[int] = None
    offline_periods: Optional[Dict[str, Set[int]]] = None
    scheduled: Optional[List[Tuple[int, int, int]]] = None  # List of (employee_id, station_id, period)
    team_name: Optional[str] = None
    call_ins: Optional[List[str]] = None  # List of employee names who called in (unavailable)
    employee_offline_periods: Optional[Dict[str, Set[int]]] = None  # Dict of employee name -> set of periods when offline
    employee_history_repo: Optional[EmployeeWorkHistoryRepositoryInterface] = None  # Repository for employee work history
    work_history_data: Optional[Dict] = field(default=None)  # Dictionary containing work history data for employees
    aro_data: Optional[Dict] = None  # Dictionary of ARO assignments by employee and period
    current_period: Optional[int] = None  # The current period being processed (1-indexed)

    def __post_init__(self):
        """Initialize any collections that might be None."""
        if self.offline_periods is None:
            self.offline_periods = {}
        if self.scheduled is None:
            self.scheduled = []
        if self.employee_offline_periods is None:
            self.employee_offline_periods = {}
        if self.aro_data is None:
            self.aro_data = {}


# Team-specific context classes
@dataclass(init=True)
class HeadsubRuleContext(RuleContext):
    """
    Context specific to the Headsub team rules.

    Contains additional attributes and methods relevant only to Headsub team scheduling.
    """
    special_stations: List[str] = field(default_factory=lambda: ["H170", "BW010", "M050", "M090"])

    def is_special_station(self, station_name: str) -> bool:
        """Check if a station is considered 'special' for Headsub team rules."""
        return station_name in self.special_stations


# Rule metadata decorator
def rule_metadata(uses: List[str]):
    """
    Decorator to document which context attributes a rule uses.

    Args:
        uses: List of attribute names from RuleContext that this rule requires

    Example:
        @rule_metadata(uses=["model", "assign", "employees"])
        def my_rule(ctx: RuleContext):
            # Rule implementation
    """
    def decorator(rule_func: Callable[[RuleContext], Any]):
        rule_func.__rule_uses__ = uses
        return rule_func
    return decorator


# Adapter function for prototype rules
def adapt_rule(rule_func: Callable) -> Callable[[RuleContext], Any]:
    """
    Adapts a prototype rule function to use the RuleContext.

    This allows existing rules with explicit parameter lists to work with
    the new Context-based design without requiring immediate refactoring.

    Args:
        rule_func: The original rule function with explicit parameters

    Returns:
        A new function that takes a RuleContext and calls the original function
    """
    def wrapper(ctx: RuleContext) -> Any:
        # Inspect the original function's parameters and extract them from context
        import inspect
        params = inspect.signature(rule_func).parameters

        # Map common parameter names to their context equivalents
        param_map = {
            'model': ctx.model,
            'A': ctx.assign,
            'E': ctx.employees,
            'W': ctx.workstations,
            'P': ctx.periods,
            'start_date': ctx.start_date,
            'lookback': ctx.lookback,
            'session': ctx.session,
            'backup_idx': ctx.backup_idx,
            'offline_periods': ctx.offline_periods,
            'scheduled': ctx.scheduled,
            'team_name': ctx.team_name,
            'call_ins': ctx.call_ins,
            'employee_offline_periods': ctx.employee_offline_periods,
            'employee_history_repo': ctx.employee_history_repo,
            'aro_data': ctx.aro_data,
            # Add more mappings as needed
        }

        # Build the arguments dictionary for the original function
        kwargs = {}
        for name in params:
            if name in param_map:
                kwargs[name] = param_map[name]

        # Call the original function with the extracted parameters
        return rule_func(**kwargs)

    # Copy metadata from the original function
    wrapper.__name__ = rule_func.__name__
    wrapper.__doc__ = rule_func.__doc__
    wrapper.__rule_uses__ = getattr(rule_func, '__rule_uses__', None)

    return wrapper
