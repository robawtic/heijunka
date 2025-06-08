# domain/services/cp_model_builder.py
from typing import List, Dict, Tuple, Any, Optional
from ortools.sat.python import cp_model
from datetime import date
import logging

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment

# Logger for this module
logger = logging.getLogger(__name__)

class CPModelBuilder:
    def build_model(self, employees: List[Employee], workstations: List[Workstation], 
                   period: int, team_id: int, aro_data: Dict, 
                   start_date: date = None, team_name: str = None,
                   employee_history_repo = None) -> Tuple[cp_model.CpModel, Dict]:
        """
        Build a CP model for the given employees, workstations, and period.

        Args:
            employees: List of employees available for this period
            workstations: List of workstations for this team
            period: The period to generate a schedule for
            team_id: The ID of the team to generate a schedule for
            aro_data: Dictionary of ARO assignments by employee and period
            start_date: The date of the schedule (required for rule context)
            team_name: The name of the team (required for rule context)
            employee_history_repo: Repository for employee work history (required for same-day repeat penalties)

        Returns:
            A tuple containing:
            - The CP model with all variables and constraints defined
            - The assignment variables dictionary
        """
        # Create CP model
        model = cp_model.CpModel()

        # Define decision variables
        assign = {}
        for e, employee in enumerate(employees):
            for w, workstation in enumerate(workstations):
                assign[(e, w, period-1)] = model.NewBoolVar(
                    f'assign_e{e}_w{w}_p{period-1}')

        # If team_name is provided, use rules from registry
        if team_name:
            from domain.rules.registry import get_rules_for_team, create_context_for_team

            # Get rules for this team
            rules = get_rules_for_team(team_name)

            # Create context with all necessary data
            ctx = create_context_for_team(
                team_name,
                model=model,
                assign=assign,
                employees=employees,
                workstations=workstations,
                periods=1,  # We're only solving for one period at a time
                start_date=start_date,
                # Add any other data needed by rules
                aro_data=aro_data,
                current_period=period,  # Pass the current period being processed
                employee_history_repo=employee_history_repo,  # Pass the employee work history repository
                lookback=7  # Default lookback window of 7 days
            )

            # Apply each rule to the context
            penalties = []
            for rule in rules:
                result = rule(ctx)
                if result:  # Some rules return penalty variables
                    penalties.extend(result)

            # Add penalties to objective function if any
            if penalties:
                model.Minimize(sum(penalties))
            else:
                # Fallback objective: maximize assignments
                # Identify ARO employees (employees whose home team is not this team)
                aro_employees = [e for e, employee in enumerate(employees) if employee.team_id != team_id]

                # Regular assignments have weight 1, ARO assignments have weight 2
                objective_terms = []
                for e in range(len(employees)):
                    for w in range(len(workstations)):
                        weight = 2 if e in aro_employees else 1
                        objective_terms.append(weight * assign[(e, w, period-1)])

                model.Minimize(sum(objective_terms))
        else:
            # Fallback to existing hard-coded constraints for backward compatibility

            # Each employee is assigned to at most one workstation per period
            for e in range(len(employees)):
                model.Add(sum(assign[(e, w, period-1)] for w in range(len(workstations))) <= 1)

            # Each workstation is assigned to at most one employee per period
            for w in range(len(workstations)):
                model.Add(sum(assign[(e, w, period-1)] for e in range(len(employees))) <= 1)

            # Handle employee availability and qualifications
            for e, employee in enumerate(employees):
                is_available = True

                # Check if employee is available for this period based on ARO data
                # If employee has ARO assignments, check if they're available for this team
                if employee.id in aro_data:
                    aro_list = aro_data[employee.id]
                    for aro in aro_list:
                        # Check if this ARO assignment is for the current period or all periods
                        if aro.period == period or aro.period is None:
                            # If employee's home team is not this team (they are an ARO from another team),
                            # they should only be available if they are assigned as an ARO to this team
                            if employee.team_id != team_id:
                                # ARO employee should only be available if assigned to this team
                                if aro.to_team_id != team_id:
                                    is_available = False
                                    break
                            else:
                                # Regular employee (home team is this team) should not be available 
                                # if assigned elsewhere as ARO
                                if aro.to_team_id != team_id:
                                    is_available = False
                                    break

                # Additional check: If employee's home team is not this team and they have no ARO assignments
                # to this team, they should not be available
                if employee.team_id != team_id and is_available:
                    # Check if this employee has any ARO assignment to this team
                    has_aro_to_this_team = False
                    if employee.id in aro_data:
                        for aro in aro_data[employee.id]:
                            if (aro.period == period or aro.period is None) and aro.to_team_id == team_id:
                                has_aro_to_this_team = True
                                break

                    # If no ARO assignment to this team, make unavailable
                    if not has_aro_to_this_team:
                        is_available = False

                # If employee is not available, ensure they're not assigned
                if not is_available:
                    for w in range(len(workstations)):
                        model.Add(assign[(e, w, period-1)] == 0)
                else:
                    # Check qualifications for each workstation
                    for w, workstation in enumerate(workstations):
                        # If employee is not qualified for this workstation, prevent assignment
                        if not employee.can_work(workstation) or not employee.can_handle_workstation_type(workstation):
                            model.Add(assign[(e, w, period-1)] == 0)

            # Identify ARO employees (employees whose home team is not this team)
            aro_employees = [e for e, employee in enumerate(employees) if employee.team_id != team_id]

            # Objective: Minimize assignments with weights
            # Regular assignments have weight 1, ARO assignments have weight 2 to prioritize them
            objective_terms = []
            for e in range(len(employees)):
                for w in range(len(workstations)):
                    # Higher weight for ARO assignments to prioritize them
                    if e in aro_employees:
                        # AROs should be assigned first, so give them higher weight
                        weight = 2
                    else:
                        weight = 1
                    objective_terms.append(weight * assign[(e, w, period-1)])

            model.Minimize(sum(objective_terms))

        return model, assign

    def solve_model(self, model: cp_model.CpModel, assign: Dict, 
                   employees: List[Employee], workstations: List[Workstation],
                   period: int, start_date: date) -> List[WorkAssignment]:
        """
        Solve the CP model and return work assignments.

        Args:
            model: The CP model to solve
            assign: Dictionary of decision variables
            employees: List of employees available for this period
            workstations: List of workstations for this team
            period: The period to generate a schedule for
            start_date: The date of the schedule

        Returns:
            List of work assignments for the specified team and period
        """
        # Create solver and solve the model
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        # Process the solution
        assignments = []
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            for e, employee in enumerate(employees):
                for w, workstation in enumerate(workstations):
                    if solver.Value(assign[(e, w, period-1)]) == 1:
                        # Create a schedule period
                        schedule_period = SchedulePeriod(
                            date=start_date,
                            period=period
                        )

                        # Create a work assignment
                        assignment = WorkAssignment(
                            employee=employee,
                            workstation=workstation,
                            period=schedule_period
                        )

                        assignments.append(assignment)

            logger.info(f"Generated {len(assignments)} assignments for period {period}")
        else:
            logger.warning(f"No solution found for period {period}. Status: {status}")

        return assignments

    def solve_one_period(self, employees: List[Employee], workstations: List[Workstation],
                        period: int, team_id: int, start_date: date, 
                        aro_data: Dict, team_name: str = None,
                        employee_history_repo = None) -> List[WorkAssignment]:
        """
        Build and solve a CP model for one period, returning work assignments.

        This is a convenience method that combines build_model and solve_model.

        Args:
            employees: List of employees available for this period
            workstations: List of workstations for this team
            period: The period to generate a schedule for
            team_id: The ID of the team to generate a schedule for
            start_date: The date of the schedule
            aro_data: Dictionary of ARO assignments by employee and period
            team_name: The name of the team (optional, for rule context)
            employee_history_repo: Repository for employee work history (required for same-day repeat penalties)

        Returns:
            List of work assignments for the specified team and period
        """
        try:
            # Build the model
            model, assign = self.build_model(
                employees, 
                workstations, 
                period, 
                team_id, 
                aro_data, 
                start_date=start_date, 
                team_name=team_name,
                employee_history_repo=employee_history_repo
            )

            # Solve the model
            return self.solve_model(model, assign, employees, workstations, period, start_date)
        except Exception as e:
            logger.error(f"Error solving model for period {period}: {str(e)}")
            return []
