from typing import List, Dict, Tuple, Set, Optional, Any
from datetime import date
import heapq  # For Dijkstra's algorithm

from domain.entities.employee import Employee
from domain.entities.team import Team
from domain.entities.workstation import Workstation
from domain.value_objects.aro_assignment import AROAssignment
from domain.repositories.interfaces.aro_assignment_repository import AROAssignmentRepositoryInterface
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.services.aro_service import AROService

class AROGraphService:
    """
    Service for optimizing ARO assignments using graph theory.
    
    This service extends the basic AROService with advanced optimization
    capabilities based on graph theory algorithms.
    """
    
    def __init__(self, 
                 aro_service: AROService,
                 aro_repository: AROAssignmentRepositoryInterface,
                 employee_repository: EmployeeRepositoryInterface,
                 team_repository: TeamRepositoryInterface,
                 workstation_repository: WorkstationRepositoryInterface):
        self.aro_service = aro_service
        self.aro_repository = aro_repository
        self.employee_repository = employee_repository
        self.team_repository = team_repository
        self.workstation_repository = workstation_repository
        
    def build_aro_transfer_graph(self, assignment_date: date, period: Optional[int] = None) -> Dict[int, List[Dict[str, Any]]]:
        """
        Build a directed graph representing possible ARO transfers between teams.
        
        Args:
            assignment_date: The date for which to build the graph
            period: Optional period of the day
            
        Returns:
            A dictionary representing the adjacency list of the graph
            {team_id: [{team_id: target_team_id, capacity: int, cost: float, employees: List[int]}]}
        """
        graph = {}
        
        # Get all teams
        teams = self.team_repository.list_all()
        
        # Initialize the graph with empty adjacency lists
        for team in teams:
            graph[team.id] = []
        
        # For each team, calculate available AROs and build edges
        for source_team in teams:
            # Get employees for this team
            team_employees = self.employee_repository.get_by_team_id(source_team.id)
            
            # Get workstations for this team
            team_workstations = self.workstation_repository.get_by_team_id(source_team.id)
            
            # Calculate capacity (how many AROs can be sent)
            # This implements Capacity Constraints (point 1)
            capacity = max(0, len(team_employees) - len(team_workstations))
            
            if capacity <= 0:
                continue  # This team has no extra employees to send as AROs
            
            # For each potential target team
            for target_team in teams:
                if source_team.id == target_team.id:
                    continue  # Skip self-loops
                
                # Get target team workstations to check qualifications
                target_workstations = self.workstation_repository.get_by_team_id(target_team.id)
                
                # Find employees who can work at the target team based on qualifications
                # This implements Qualifications/Skill Matching (point 2)
                qualified_employees = []
                for employee in team_employees:
                    # Check if employee is available for this date/period
                    if not employee.is_available_for_period(assignment_date, period):
                        continue
                        
                    # Check if employee has qualifications for at least one workstation in target team
                    can_work_at_target = False
                    for workstation in target_workstations:
                        if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                            can_work_at_target = True
                            break
                            
                    if can_work_at_target:
                        qualified_employees.append(employee.id)
                
                if not qualified_employees:
                    continue  # No qualified employees for this target team
                
                # Calculate edge cost based on various factors
                # This implements Path Weighting/Cost (point 4)
                cost = self._calculate_edge_cost(source_team, target_team, qualified_employees)
                
                # Add edge to the graph
                graph[source_team.id].append({
                    'team_id': target_team.id,
                    'capacity': min(capacity, len(qualified_employees)),
                    'cost': cost,
                    'employees': qualified_employees
                })
        
        return graph
    
    def _calculate_edge_cost(self, source_team: Team, target_team: Team, employee_ids: List[int]) -> float:
        """
        Calculate the cost of transferring AROs from source to target team.
        
        Lower cost means more preferable transfer. Cost factors include:
        - Distance between teams (if applicable)
        - Employee familiarity with target team
        - Historical ARO assignments
        - Team priority
        
        Args:
            source_team: The source team
            target_team: The target team
            employee_ids: IDs of employees who can be transferred
            
        Returns:
            A cost value (lower is better)
        """
        # Base cost
        cost = 1.0
        
        # Add cost factors as needed
        # For example, if teams have physical locations, add distance cost
        # cost += self._calculate_distance_cost(source_team, target_team)
        
        # Add cost based on employee familiarity with target team
        familiarity_cost = 0.0
        for emp_id in employee_ids:
            # Check if employee has worked at target team before
            # Lower cost if employee is familiar with target team
            # This could be based on work history or previous ARO assignments
            familiarity_cost += 0.1  # Placeholder
            
        cost += familiarity_cost / max(1, len(employee_ids))
        
        # Team priority could also affect cost
        # Lower cost for high-priority teams
        # cost -= self._get_team_priority(target_team)
        
        return cost
    
    def find_optimal_aro_paths(self, 
                              understaffed_team_id: int, 
                              assignment_date: date, 
                              period: Optional[int] = None,
                              max_hops: int = 2) -> List[Dict[str, Any]]:
        """
        Find optimal paths to send AROs to an understaffed team.
        
        This uses Dijkstra's algorithm to find the shortest (lowest cost) paths
        from any team with available AROs to the understaffed team.
        
        Args:
            understaffed_team_id: ID of the team that needs AROs
            assignment_date: The date for the assignments
            period: Optional period of the day
            max_hops: Maximum number of intermediate teams allowed
            
        Returns:
            List of paths, each containing the sequence of teams and the employees to transfer
        """
        # Build the ARO transfer graph
        graph = self.build_aro_transfer_graph(assignment_date, period)
        
        # Find all teams that have available AROs
        source_teams = [team_id for team_id, edges in graph.items() if edges]
        
        # Find paths from each source team to the understaffed team
        all_paths = []
        
        for source_team_id in source_teams:
            # Use Dijkstra's algorithm to find the shortest path
            # This implements Cycle/Redundancy Avoidance (point 3)
            paths = self._find_shortest_paths(graph, source_team_id, understaffed_team_id, max_hops)
            all_paths.extend(paths)
        
        # Sort paths by cost (lowest first)
        all_paths.sort(key=lambda p: p['total_cost'])
        
        return all_paths
    
    def _find_shortest_paths(self, 
                            graph: Dict[int, List[Dict[str, Any]]], 
                            source_team_id: int, 
                            target_team_id: int,
                            max_hops: int) -> List[Dict[str, Any]]:
        """
        Find shortest paths from source to target team using Dijkstra's algorithm.
        
        Args:
            graph: The ARO transfer graph
            source_team_id: ID of the source team
            target_team_id: ID of the target team
            max_hops: Maximum number of intermediate teams allowed
            
        Returns:
            List of paths, each containing the sequence of teams and the cost
        """
        # Initialize distances and predecessors
        distances = {team_id: float('infinity') for team_id in graph}
        distances[source_team_id] = 0
        predecessors = {team_id: None for team_id in graph}
        visited = set()
        
        # Priority queue for Dijkstra's algorithm
        pq = [(0, source_team_id, 0)]  # (distance, team_id, hops)
        
        while pq:
            current_distance, current_team_id, hops = heapq.heappop(pq)
            
            # If we've reached the target, we're done
            if current_team_id == target_team_id:
                break
                
            # If we've already processed this team or exceeded max hops, skip
            if current_team_id in visited or hops >= max_hops:
                continue
                
            visited.add(current_team_id)
            
            # Process all neighbors
            for edge in graph.get(current_team_id, []):
                neighbor_id = edge['team_id']
                
                # Skip if we've already visited this team
                if neighbor_id in visited:
                    continue
                
                # Calculate new distance
                new_distance = current_distance + edge['cost']
                
                # If this path is better, update distance and predecessor
                if new_distance < distances[neighbor_id]:
                    distances[neighbor_id] = new_distance
                    predecessors[neighbor_id] = (current_team_id, edge)
                    heapq.heappush(pq, (new_distance, neighbor_id, hops + 1))
        
        # If no path found, return empty list
        if distances[target_team_id] == float('infinity'):
            return []
        
        # Reconstruct the path
        path = []
        current = target_team_id
        
        while current != source_team_id:
            if predecessors[current] is None:
                # No path exists
                return []
                
            prev_team_id, edge = predecessors[current]
            path.append({
                'from_team_id': prev_team_id,
                'to_team_id': current,
                'capacity': edge['capacity'],
                'cost': edge['cost'],
                'employees': edge['employees']
            })
            current = prev_team_id
            
        # Reverse the path to get source to target
        path.reverse()
        
        # Calculate total cost and capacity
        total_cost = sum(edge['cost'] for edge in path)
        min_capacity = min(edge['capacity'] for edge in path)
        
        return [{
            'path': path,
            'total_cost': total_cost,
            'capacity': min_capacity
        }]
    
    def assign_optimal_aros(self, 
                           understaffed_team_id: int, 
                           needed_aros: int,
                           assignment_date: date, 
                           period: Optional[int] = None) -> List[AROAssignment]:
        """
        Assign AROs to an understaffed team using optimal paths.
        
        Args:
            understaffed_team_id: ID of the team that needs AROs
            needed_aros: Number of AROs needed
            assignment_date: The date for the assignments
            period: Optional period of the day
            
        Returns:
            List of created ARO assignments
        """
        # Find optimal paths
        paths = self.find_optimal_aro_paths(understaffed_team_id, assignment_date, period)
        
        if not paths:
            return []
            
        # Create assignments using the paths
        assignments = []
        remaining_needed = needed_aros
        
        for path_info in paths:
            if remaining_needed <= 0:
                break
                
            path = path_info['path']
            capacity = min(path_info['capacity'], remaining_needed)
            
            # For direct paths (single hop)
            if len(path) == 1:
                edge = path[0]
                from_team_id = edge['from_team_id']
                to_team_id = edge['to_team_id']
                available_employees = edge['employees'][:capacity]
                
                for employee_id in available_employees:
                    result = self.aro_service.assign_aro(
                        employee_id=employee_id,
                        to_team_id=to_team_id,
                        assignment_date=assignment_date,
                        period=period
                    )
                    
                    if result["status"] == 'success':
                        # Get the created assignment
                        assignment = self.aro_service.find_aro_assignment(
                            employee_id=employee_id,
                            assignment_date=assignment_date,
                            period=period
                        )
                        
                        if assignment:
                            assignments.append(assignment)
                            remaining_needed -= 1
                            
                            if remaining_needed <= 0:
                                break
            
            # For multi-hop paths
            else:
                # This is more complex and requires creating a chain of ARO assignments
                # For each hop in the path, we need to assign an employee from the source team
                # to the intermediate team, and then from the intermediate team to the target team
                
                # This is a simplified implementation that just creates the first and last assignments
                first_edge = path[0]
                last_edge = path[-1]
                
                from_team_id = first_edge['from_team_id']
                intermediate_team_id = first_edge['to_team_id']
                to_team_id = last_edge['to_team_id']
                
                available_employees = first_edge['employees'][:capacity]
                
                for employee_id in available_employees:
                    # Assign from source to intermediate team
                    result1 = self.aro_service.assign_aro(
                        employee_id=employee_id,
                        to_team_id=intermediate_team_id,
                        assignment_date=assignment_date,
                        period=period
                    )
                    
                    if result1["status"] == 'success':
                        # Find an employee from the intermediate team to assign to the target team
                        intermediate_employees = self.employee_repository.get_by_team_id(intermediate_team_id)
                        
                        for intermediate_employee in intermediate_employees:
                            # Skip if already assigned as ARO
                            if not intermediate_employee.is_available_for_period(assignment_date, period):
                                continue
                                
                            # Assign from intermediate to target team
                            result2 = self.aro_service.assign_aro(
                                employee_id=intermediate_employee.id,
                                to_team_id=to_team_id,
                                assignment_date=assignment_date,
                                period=period
                            )
                            
                            if result2["status"] == 'success':
                                # Get the created assignment
                                assignment = self.aro_service.find_aro_assignment(
                                    employee_id=intermediate_employee.id,
                                    assignment_date=assignment_date,
                                    period=period
                                )
                                
                                if assignment:
                                    assignments.append(assignment)
                                    remaining_needed -= 1
                                    
                                    if remaining_needed <= 0:
                                        break
                            
                        if remaining_needed <= 0:
                            break
        
        return assignments