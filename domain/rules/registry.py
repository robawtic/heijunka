# domain/rules/registry.py

import pkgutil
import importlib
import inspect

from domain.rules.context import adapt_rule, RuleContext, HeadsubRuleContext
from domain.rules.hard import (
    forbid_unavailable,
    forbid_unknown_stations,
    add_one_station_per_employee,
    add_exactly_one_per_station,
    # ...add other hard rules here
)
from domain.rules.soft import (
    add_same_day_repeat_penalties,
    add_lookback_any_period_penalties,
    add_lookback_same_period_penalties,
)

# All rules should take a single argument: ctx (RuleContext)
COMMON_HARD_RULES = [

    forbid_unavailable,
    forbid_unknown_stations,
    add_one_station_per_employee,
    add_exactly_one_per_station,

    # ...add more
]

COMMON_SOFT_RULES = [
    add_same_day_repeat_penalties,
    add_lookback_any_period_penalties,
    add_lookback_same_period_penalties,
    # ...add more
]


def _discover_team_rules():
    """
    Discovers the team-specific rules.

    This function scans the domain.rules.teams package for modules containing team-specific rules.
    Each module should define a list of rules in a variable named <TEAM_NAME>_RULES.
    """
    team_rules = {}
    import domain.rules.teams as pkg
    for finder, name, ispkg in pkgutil.iter_modules(pkg.__path__):
        if name.startswith("_"):
            continue
        mod = importlib.import_module(f"domain.rules.teams.{name}")
        attr = name.upper() + "_RULES"
        rules = getattr(mod, attr, None)
        if rules is not None:
            # Adapt any prototype rules to use the Context pattern
            adapted_rules = []
            for rule in rules:
                if len(inspect.signature(rule).parameters) > 1:
                    # This is a prototype rule with multiple parameters
                    adapted_rules.append(adapt_rule(rule))
                else:
                    # This is already a Context-based rule
                    adapted_rules.append(rule)
            team_rules[name.lower()] = adapted_rules
    return team_rules


TEAM_RULES = _discover_team_rules()


def get_rules_for_team(team_name):
    """
    Returns a list of all rules to be applied for a team.
    Order: [COMMON_HARD_RULES] + [team-specific] + [COMMON_SOFT_RULES]

    Args:
        team_name: The name of the team to get rules for

    Returns:
        A list of rule functions that take a RuleContext parameter
    """
    team_name = team_name.lower() if team_name else ""
    team_specific = TEAM_RULES.get(team_name, [])
    return COMMON_HARD_RULES + team_specific + COMMON_SOFT_RULES


def create_context_for_team(team_name, **kwargs):
    """
    Creates the appropriate RuleContext subclass for a team.

    Args:
        team_name: The name of the team
        **kwargs: Additional parameters to pass to the context constructor

    Returns:
        A RuleContext instance appropriate for the team
    """
    team_name = team_name.lower() if team_name else ""

    # Add team_name to kwargs
    kwargs['team_name'] = team_name

    # Create the appropriate context based on team name
    if team_name == "headsub":
        return HeadsubRuleContext(**kwargs)
    else:
        return RuleContext(**kwargs)


# Optionally: all rules in a flat list (for reference/testing)
ALL_RULES = COMMON_HARD_RULES + COMMON_SOFT_RULES + [
    r for rules in TEAM_RULES.values() for r in rules
]