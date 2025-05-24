# heijunka/domain/services/schedule_service.py
from typing import List, Dict, Set, Optional, Tuple, Any
from datetime import date, timedelta

from ortools.sat.python import cp_model

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.value_objects.schedule_constraint import ScheduleConstraint, ConstraintType
from domain.events import AssignmentCreated
from rules.context import RuleContext


class ScheduleService:
    def __init__(self, constraints: List[ScheduleConstraint] = None):
        self.constraints = constraints or []

    def assign_employee(self, employee: Employee, workstation: Workstation,
                        period: SchedulePeriod) -> WorkAssignment:
        """
        Assign an employee to a workstation for a specific period
        """
        if not employee.can_work(workstation):
            raise ValueError(f"{employee.name} cannot work {workstation.name}")

        if not employee.is_available_for_period(period.day, period.period):
            raise ValueError(f"{employee.name} is not available on {period}")

        assignment = WorkAssignment(employee, workstation, period)

        # Create domain event
        event = AssignmentCreated(assignment)

        # In a real implementation, we would publish this event
        # event_bus.publish(event)

        return assignment

    def generate_schedule(self, employees: List[Employee], workstations: List[Workstation],
                          start_date: date, days: int, periods_per_day: int,
                          team_name: str, call_ins: List[str] = None, offline: List[str] = None, 
                          force_complete: bool = False, session=None) -> List[WorkAssignment]:
        """
        Generate a schedule for the given employees, workstations, and time period

        Args:
            employees: List of employees to schedule
            workstations: List of workstations to assign employees to
            start_date: The start date of the schedule
            days: Number of days to schedule
            periods_per_day: Number of periods per day
            team_name: Name of the team to generate the schedule for
            call_ins: List of employee names who called in (unavailable)
            offline: List of strings in format "employee:periods" specifying which employees are offline for which periods
            force_complete: Whether to force completion of the schedule
            session: Database session for accessing work history data

        Returns:
            List of work assignments
        """
        # Debug output

        """  
        print(f"Generating schedule for {len(employees)} employees and {len(workstations)} workstations")
        for i, emp in enumerate(employees):
            print(f"  Employee {i}: {emp.name}, qualifications: {emp.qualifications}")
        for j, ws in enumerate(workstations):
            print(f"  Workstation {j}: {ws.name}, is_loading: {ws.is_loading()}")

        # Check which employees can work at which workstations
        for j, ws in enumerate(workstations):
            qualified_employees = [emp.name for i, emp in enumerate(employees) if emp.can_work(ws)]
            print(f"  Workstation {j}: {ws.name}, qualified employees: {qualified_employees}")

        # Check if there are any workstations that no employee can work at
        problematic_workstations = []
        for j, ws in enumerate(workstations):
            if not any(emp.can_work(ws) for emp in employees):
                problematic_workstations.append(ws.name)
        if problematic_workstations:
            print(f"  WARNING: No employees can work at these workstations: {problematic_workstations}")
        """

        # Create CP model
        model = cp_model.CpModel()

        # Define decision variables
        # assign[(day, emp_idx, ws_idx, period)] = 1 if employee emp_idx is assigned to workstation ws_idx on day at period
        assign = {}
        for day in range(days):
            for emp_idx, employee in enumerate(employees):
                for ws_idx, workstation in enumerate(workstations):
                    for period in range(periods_per_day):
                        assign[(day, emp_idx, ws_idx, period)] = model.NewBoolVar(
                            f'assign_d{day}_e{emp_idx}_w{ws_idx}_p{period}')

        # Apply constraints using the rules registry
        print("Applying constraints using the rules registry")

        from rules.registry import get_rules_for_team, create_context_for_team

        # Parse offline parameter
        employee_offline_periods = {}
        if offline:
            for offline_str in offline:
                parts = offline_str.split(':')
                if len(parts) == 2:
                    emp_name, periods_str = parts
                    periods = {int(p) for p in periods_str.split(',')}
                    employee_offline_periods[emp_name] = periods

        # Create a context for the team
        ctx = create_context_for_team(
            team_name=team_name,
            model=model,
            assign=assign,
            days=days,
            employees=employees,
            workstations=workstations,
            periods=periods_per_day,
            start_date=start_date,
            lookback=3,  # Default lookback of 3 days
            session=session,  # Pass the session to the context
            backup_idx=next((i for i, e in enumerate(employees) if e.has_role("Backup")), None),
            offline_periods={},  # No offline periods for now
            scheduled=[],  # No scheduled assignments for now
            call_ins=call_ins,  # Pass the call-ins parameter
            employee_offline_periods=employee_offline_periods  # Pass the employee offline periods
        )

        # Get rules for the team
        rules = get_rules_for_team(team_name)
        print(f"Applying {len(rules)} rules for team '{team_name}'")

        # Apply all rules
        objective_terms = []

        # Define weights for different rule types
        rule_weights = {
            "add_rotation_penalties": 1000,  # Increased from 50 to 500 to make rotation more effective
            "add_repeat_station_penalties": 100,
            "add_workload_deviation": 200,
            "add_compound_fatigue_penalty_daylevel": 2000,
            "add_compound_fatigue_repetition_penalty": 5000,
            "add_cross_day_repeat_penalties": 500,
            "add_consecutive_day_combo_penalties": 100,
            "add_historical_station_fairness": 10000
        }

        for rule in rules:
            print(f"  Applying rule: {rule.__name__}")
            result = rule(ctx)
            # If the rule returns penalty variables, add them to the objective
            if isinstance(result, list) and result:
                # Get the weight for this rule (default to 10 if not specified)
                weight = rule_weights.get(rule.__name__, 10)
                print(f"    Rule {rule.__name__} returned {len(result)} penalty terms with weight {weight}")
                for penalty in result:
                    objective_terms.append(weight * penalty)


        # Set objective function
        if objective_terms:
            print(f"Adding {len(objective_terms)} terms to objective function")
            model.Minimize(sum(objective_terms))
        else:
            print("No objective terms to minimize")

        """# Create a simple test model to verify the solver is working
        print("Creating a simple test model...")
        test_model = cp_model.CpModel()
        test_var = test_model.NewBoolVar("test_var")
        test_model.Add(test_var == 1)  # Force the variable to be true
        test_solver = cp_model.CpSolver()
        test_status = test_solver.Solve(test_model)
        print(f"Test model status: {test_solver.StatusName(test_status)}")
        print(f"Test variable value: {test_solver.Value(test_var)}")"""

        """# Add a simple assignment to the main model
        print("Adding a simple assignment to the main model...")
        if len(employees) > 1 and len(workstations) > 1:
            # Find a qualified employee for the first workstation
            qualified_emp_idx = -1
            for i, emp in enumerate(employees):
                if emp.can_work(workstations[0]):
                    qualified_emp_idx = i
                    break

            if qualified_emp_idx >= 0:
                print(f"Forcing employee {employees[qualified_emp_idx].name} to work at {workstations[0].name}")
                model.Add(assign[(0, qualified_emp_idx, 0, 0)] == 1)  # Force this assignment"""

        # Solve the model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(30 * days / 10, 300)
        print(f"Solving model with {len(employees)} employees and {len(workstations)} workstations...")
        status = solver.Solve(model)
        print(f"Solver status: {solver.StatusName(status)}")

        # Extract and return results
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            assignments = self._extract_assignments(solver, assign, employees, workstations, days, periods_per_day, start_date)
            print(f"Generated {len(assignments)} assignments")
            return assignments
        else:
            print(f"No solution found. Status: {solver.StatusName(status)}")
            return []

    def add_constraint(self, constraint: ScheduleConstraint):
        """Add a constraint to the schedule service"""
        self.constraints.append(constraint)

    def _apply_hard_constraints(self, model: cp_model.CpModel, assign: Dict, 
                               employees: List[Employee], workstations: List[Workstation], 
                               days: int, periods_per_day: int, start_date: date,
                               call_ins: List[str] = None) -> None:
        """
        Apply hard constraints to the model

        Args:
            model: The CP model
            assign: The assignment variables
            employees: List of employees
            workstations: List of workstations
            days: Number of days
            periods_per_day: Number of periods per day
            start_date: The start date of the schedule
            call_ins: List of employee names who called in (unavailable)
        """
        # Create a RuleContext to pass to the rules
        ctx = RuleContext(
            model=model,
            assign=assign,
            days=days,
            employees=employees,
            workstations=workstations,
            periods=periods_per_day,
            start_date=start_date,
            scheduled=None,  # We could load previously scheduled assignments here
            call_ins=call_ins  # Pass call-ins to the context
        )

        # Apply hard constraints from the rules registry
        from rules.registry import COMMON_HARD_RULES
        for rule in COMMON_HARD_RULES:
            rule(ctx)

        # One employee per workstation per period
        for day in range(days):
            for period in range(periods_per_day):
                for ws_idx in range(len(workstations)):
                    model.Add(sum(assign[(day, emp_idx, ws_idx, period)] 
                                 for emp_idx in range(len(employees))) <= 1)

        # One workstation per employee per period
        for day in range(days):
            for period in range(periods_per_day):
                for emp_idx in range(len(employees)):
                    model.Add(sum(assign[(day, emp_idx, ws_idx, period)] 
                                 for ws_idx in range(len(workstations))) <= 1)

    def _apply_soft_constraints(self, model: cp_model.CpModel, assign: Dict, 
                               employees: List[Employee], workstations: List[Workstation], 
                               days: int, periods_per_day: int, start_date: date) -> List[Any]:
        """
        Apply soft constraints to the model

        Args:
            model: The CP model
            assign: The assignment variables
            employees: List of employees
            workstations: List of workstations
            days: Number of days
            periods_per_day: Number of periods per day
            start_date: The start date of the schedule

        Returns:
            List of objective terms to minimize
        """
        objective_terms = []

        # Create a RuleContext to pass to the rules
        ctx = RuleContext(
            model=model,
            assign=assign,
            days=days,
            employees=employees,
            workstations=workstations,
            periods=periods_per_day,
            start_date=start_date,
            scheduled=None  # We could load previously scheduled assignments here
        )

        # Apply soft constraints from the rules registry
        from rules.registry import COMMON_SOFT_RULES
        for rule in COMMON_SOFT_RULES:
            # Soft rules should return a list of terms to add to the objective function
            terms = rule(ctx)
            if terms:
                objective_terms.extend(terms)

        # Add rotation penalties (avoid same station on consecutive days)
        rotation_penalties = []
        for emp_idx in range(len(employees)):
            for ws_idx in range(len(workstations)):
                for day in range(days - 1):
                    for period1 in range(periods_per_day):
                        for period2 in range(periods_per_day):
                            # If employee is assigned to same station on consecutive days
                            same_station = model.NewBoolVar(f'same_station_e{emp_idx}_w{ws_idx}_d{day}')
                            model.Add(assign[(day, emp_idx, ws_idx, period1)] + 
                                     assign[(day + 1, emp_idx, ws_idx, period2)] - 
                                     same_station <= 1)
                            model.Add(assign[(day, emp_idx, ws_idx, period1)] + 
                                     assign[(day + 1, emp_idx, ws_idx, period2)] - 
                                     2 * same_station >= 0)
                            rotation_penalties.append(same_station)

        # Add rotation penalties to objective terms with a weight
        for penalty in rotation_penalties:
            objective_terms.append(50 * penalty)

        return objective_terms

    def _extract_assignments(self, solver: cp_model.CpSolver, assign: Dict, 
                            employees: List[Employee], workstations: List[Workstation], 
                            days: int, periods_per_day: int, start_date: date) -> List[WorkAssignment]:
        """
        Extract assignments from the solved model

        Args:
            solver: The CP solver
            assign: The assignment variables
            employees: List of employees
            workstations: List of workstations
            days: Number of days
            periods_per_day: Number of periods per day
            start_date: The start date of the schedule

        Returns:
            List of work assignments
        """
        assignments = []

        for day in range(days):
            current_date = start_date + timedelta(days=day)
            for period in range(periods_per_day):
                for emp_idx, employee in enumerate(employees):
                    for ws_idx, workstation in enumerate(workstations):
                        if solver.Value(assign[(day, emp_idx, ws_idx, period)]) == 1:
                            # Create a SchedulePeriod for this assignment
                            schedule_period = SchedulePeriod(date=current_date, period=period + 1)

                            # Create a WorkAssignment
                            assignment = WorkAssignment(
                                employee=employee,
                                workstation=workstation,
                                period=schedule_period
                            )

                            assignments.append(assignment)

        return assignments
