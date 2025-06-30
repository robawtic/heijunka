from typing import List, Dict, Tuple, Set, Optional, Any, Callable
from datetime import date, timedelta
import heapq  # For Dijkstra's algorithm
import functools
import time
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

from domain.entities.employee import Employee
from domain.entities.team import Team
from domain.entities.workstation import Workstation
from domain.contexts.assignment.aro_assignment import AROAssignment
from domain.repositories.interfaces.aro_assignment_repository import AROAssignmentRepositoryInterface
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.services.aro_service import AROService
from domain.events.publisher import DomainEventPublisher

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
                 workstation_repository: WorkstationRepositoryInterface,
                 event_publisher: DomainEventPublisher):
        self.aro_service = aro_service
        self.aro_repository = aro_repository
        self.employee_repository = employee_repository
        self.team_repository = team_repository
        self.workstation_repository = workstation_repository
        self.event_publisher = event_publisher
        self._edge_cost_cache = {}  # Cache for edge costs
        self._graph_cache = {}      # Cache for transfer graphs

        # Get the session factory from the repository
        self._session_factory = getattr(aro_repository, '_session_factory', None)
        if not self._session_factory:
            raise ValueError("Could not get database session factory from repository")

    def clear_caches(self):
        """Clear all caches when data changes."""
        self._edge_cost_cache.clear()
        self._graph_cache.clear()

    def build_aro_transfer_graph(self, assignment_date: date, period: Optional[int] = None) -> Dict[int, List[Dict[str, Any]]]:
        """
        Build a directed graph representing possible ARO transfers between teams.
        Now with caching for better performance.

        Args:
            assignment_date: The date for which to build the graph
            period: Optional period of the day

        Returns:
            A dictionary representing the adjacency list of the graph
            {team_id: [{team_id: target_team_id, capacity: int, cost: float, employees: List[int]}]}
        """
        # Create a cache key
        cache_key = (assignment_date, period)

        # Check if graph is in cache
        if cache_key in self._graph_cache:
            return self._graph_cache[cache_key]

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

                # Use the cached edge cost calculation
                cost = self._calculate_edge_cost_cached(
                    source_team.id, target_team.id, assignment_date, period
                )

                # Add edge to the graph
                graph[source_team.id].append({
                    'team_id': target_team.id,
                    'capacity': min(capacity, len(qualified_employees)),
                    'cost': cost,
                    'employees': qualified_employees
                })

        # Cache the result
        self._graph_cache[cache_key] = graph
        return graph

    @functools.lru_cache(maxsize=128)
    def _calculate_edge_cost_cached(self, source_team_id: int, target_team_id: int, 
                                  assignment_date: date, period: Optional[int] = None) -> float:
        """
        Cached version of edge cost calculation.

        Args:
            source_team_id: ID of the source team
            target_team_id: ID of the target team
            assignment_date: The date for the assignment
            period: Optional period of the day

        Returns:
            A cost value (lower is better)
        """
        # Get the teams
        source_team = self.team_repository.get(source_team_id)
        target_team = self.team_repository.get(target_team_id)

        if not source_team or not target_team:
            return float('infinity')

        # Get qualified employees
        team_employees = self.employee_repository.get_by_team_id(source_team_id)
        target_workstations = self.workstation_repository.get_by_team_id(target_team_id)

        qualified_employee_ids = []
        for employee in team_employees:
            if not employee.is_available_for_period(assignment_date, period):
                continue

            can_work_at_target = False
            for workstation in target_workstations:
                if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                    can_work_at_target = True
                    break

            if can_work_at_target:
                qualified_employee_ids.append(employee.id)

        # Calculate cost using the non-cached method
        return self._calculate_edge_cost(source_team, target_team, qualified_employee_ids)

    def _calculate_edge_cost(self, source_team: Team, target_team: Team, employee_ids: List[int]) -> float:
        """
        Calculate the cost of transferring AROs from source to target team.

        Lower cost means more preferable transfer. Cost factors include:
        - Distance between teams (if applicable)
        - Employee familiarity with target team
        - Historical ARO assignments
        - Team priority
        - Employee fatigue and fairness

        Args:
            source_team: The source team
            target_team: The target team
            employee_ids: IDs of employees who can be transferred

        Returns:
            A cost value (lower is better)
        """
        # Create a cache key
        cache_key = (source_team.id, target_team.id, tuple(sorted(employee_ids)))

        # Check if result is in cache
        if cache_key in self._edge_cost_cache:
            return self._edge_cost_cache[cache_key]

        # Base cost
        cost = 1.0

        # 1. Physical distance cost (if applicable)
        # Assuming teams have location attributes
        if hasattr(source_team, 'location') and hasattr(target_team, 'location'):
            distance = self._calculate_physical_distance(source_team.location, target_team.location)
            cost += distance * 0.1  # Weight factor for distance

        # 2. Employee familiarity with target team
        familiarity_cost = 0.0
        for emp_id in employee_ids:
            employee = self.employee_repository.get(emp_id)
            if employee:
                # Check previous ARO assignments to this team
                previous_assignments = self.aro_repository.get_by_employee_id(emp_id)
                target_team_assignments = [a for a in previous_assignments if a.to_team_id == target_team.id]

                # More assignments = more familiarity = lower cost
                familiarity_factor = min(1.0, len(target_team_assignments) * 0.2)
                familiarity_cost -= familiarity_factor

        # Average familiarity across all qualified employees
        if employee_ids:
            cost += familiarity_cost / len(employee_ids)

        # 3. Fairness factor - employees who have done many ARO assignments recently
        # should be less likely to be chosen (higher cost)
        fairness_cost = 0.0
        recent_cutoff = date.today() - timedelta(days=30)  # Last 30 days

        for emp_id in employee_ids:
            recent_assignments = [a for a in self.aro_repository.get_by_employee_id(emp_id) 
                                 if a.assignment_date >= recent_cutoff]

            # More recent assignments = higher cost (less fair to assign again)
            fairness_factor = min(2.0, len(recent_assignments) * 0.5)
            fairness_cost += fairness_factor

        # Average fairness across all qualified employees
        if employee_ids:
            cost += fairness_cost / len(employee_ids)

        # 4. Team priority (if applicable)
        # Higher priority teams should have lower costs
        if hasattr(target_team, 'priority'):
            priority_factor = getattr(target_team, 'priority', 0)
            cost -= priority_factor * 0.5

        # Ensure cost is never negative or zero
        cost = max(0.1, cost)

        # Cache the result
        self._edge_cost_cache[cache_key] = cost
        return cost

    def _calculate_physical_distance(self, location1, location2):
        """Calculate physical distance between two locations."""
        # Implementation depends on how locations are represented
        # Could be simple Euclidean distance, Manhattan distance, etc.
        return 1.0  # Placeholder

    def find_optimal_aro_paths(self, 
                              understaffed_team_id: int, 
                              assignment_date: date, 
                              period: Optional[int] = None,
                              max_hops: int = 2,
                              k: int = 3) -> List[Dict[str, Any]]:
        """
        Find optimal paths to send AROs to an understaffed team.

        This uses Yen's algorithm to find the k shortest (lowest cost) paths
        from any team with available AROs to the understaffed team.

        Args:
            understaffed_team_id: ID of the team that needs AROs
            assignment_date: The date for the assignments
            period: Optional period of the day
            max_hops: Maximum number of intermediate teams allowed
            k: Number of shortest paths to find per source team

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
            # Use Yen's algorithm to find k shortest paths
            # This implements Cycle/Redundancy Avoidance (point 3)
            paths = self.find_k_shortest_paths(
                graph, source_team_id, understaffed_team_id, max_hops, k
            )
            all_paths.extend(paths)

        # Sort paths by cost (lowest first)
        all_paths.sort(key=lambda p: p['total_cost'])

        return all_paths

    def find_k_shortest_paths(self, 
                             graph: Dict[int, List[Dict[str, Any]]], 
                             source_team_id: int, 
                             target_team_id: int,
                             max_hops: int = 2,
                             k: int = 3) -> List[Dict[str, Any]]:
        """
        Find k shortest paths using Yen's algorithm.

        Args:
            graph: The ARO transfer graph
            source_team_id: ID of the source team
            target_team_id: ID of the target team
            max_hops: Maximum number of intermediate teams allowed
            k: Number of shortest paths to find

        Returns:
            List of paths, sorted by cost
        """
        # Find the shortest path first using Dijkstra
        shortest_paths = self._find_shortest_paths(graph, source_team_id, target_team_id, max_hops)

        if not shortest_paths:
            return []

        # The first shortest path
        A = [shortest_paths[0]]

        # Potential k-shortest paths
        B = []

        # Find k-1 more paths
        for i in range(1, k):
            # The previous shortest path
            prev_path = A[-1]['path']

            # For each node in the previous path except the last one
            for j in range(len(prev_path)):
                # The spur node is the j-th node in the previous path
                spur_node = prev_path[j]['from_team_id']

                # The root path is the path from source to spur node
                root_path = prev_path[:j]

                # Remove the links that are part of the previous shortest paths which share the same root path
                removed_edges = []
                for path_dict in A:
                    path = path_dict['path']
                    if len(path) > j and path[:j] == root_path:
                        # Remove the edge after the spur node
                        if j < len(path):
                            edge_to_remove = (path[j]['from_team_id'], path[j]['to_team_id'])
                            for edge_idx, edge in enumerate(graph.get(edge_to_remove[0], [])):
                                if edge['team_id'] == edge_to_remove[1]:
                                    removed_edges.append((edge_to_remove[0], edge_idx, edge))
                                    graph[edge_to_remove[0]].pop(edge_idx)
                                    break

                # Remove nodes in the root path from the graph except the spur node
                removed_nodes = []
                if j > 0:
                    for node_idx in range(j):
                        node = prev_path[node_idx]['from_team_id']
                        if node != spur_node and node in graph:
                            removed_nodes.append((node, graph[node]))
                            graph[node] = []

                # Calculate the spur path from the spur node to the target
                spur_paths = self._find_shortest_paths(graph, spur_node, target_team_id, max_hops - j)

                # Add back the edges and nodes
                for node, edges in removed_nodes:
                    graph[node] = edges

                for node, edge_idx, edge in removed_edges:
                    if node in graph:
                        graph[node].insert(edge_idx, edge)

                # No spur path was found
                if not spur_paths:
                    continue

                # Complete path: root path + spur path
                total_path = root_path + spur_paths[0]['path']

                # Calculate total cost and capacity
                total_cost = sum(edge['cost'] for edge in total_path)
                min_capacity = min(edge['capacity'] for edge in total_path)

                # Add the path to the potential k-shortest paths
                potential_path = {
                    'path': total_path,
                    'total_cost': total_cost,
                    'capacity': min_capacity
                }

                # Add the potential path to B if it's not already there
                if potential_path not in B:
                    B.append(potential_path)

            # No more paths can be found
            if not B:
                break

            # Sort the potential paths by cost
            B.sort(key=lambda p: p['total_cost'])

            # Add the lowest cost path to A
            A.append(B[0])
            B.pop(0)

        return A

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

    @contextmanager
    def _transaction(self, max_retries: int = 3, retry_delay: float = 0.5):
        """
        Context manager for database transactions with retry logic.
        Ensures all operations within a block either complete successfully or are rolled back.

        Args:
            max_retries: Maximum number of retry attempts for deadlocks
            retry_delay: Delay in seconds between retry attempts
        """
        retries = 0
        while True:
            session = self._session_factory()
            try:
                yield session
                session.commit()
                break  # Success, exit the loop
            except SQLAlchemyError as e:
                session.rollback()

                # Check if it's a deadlock error (depends on the database)
                is_deadlock = "deadlock" in str(e).lower() or "lock timeout" in str(e).lower()

                if is_deadlock and retries < max_retries:
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** retries)
                    retries += 1
                    print(f"Deadlock detected, retrying in {sleep_time:.2f} seconds (attempt {retries}/{max_retries})")
                    time.sleep(sleep_time)
                else:
                    # Not a deadlock or max retries exceeded
                    raise ValueError(f"Database error: {str(e)}")
            finally:
                session.close()

    def _lock_aro_assignments(self, session, assignment_date: date, period: Optional[int] = None):
        """
        Acquire a lock on the ARO assignments for a specific date and period.
        This prevents concurrent modifications to the same assignments.

        Args:
            session: The database session to use
            assignment_date: The date to lock
            period: Optional period of the day
        """
        # Implementation depends on the database being used
        # For PostgreSQL, you might use:
        from sqlalchemy import text
        query = text("""
        SELECT 1 FROM aro_assignments 
        WHERE assignment_date = :date AND (period = :period OR period IS NULL)
        FOR UPDATE
        """)
        session.execute(query, {"date": assignment_date, "period": period})

    def assign_optimal_aros(self, 
                           understaffed_team_id: int, 
                           needed_aros: int,
                           assignment_date: date, 
                           period: Optional[int] = None) -> List[AROAssignment]:
        """
        Assign AROs to an understaffed team using optimal paths.
        Now with transaction management to prevent race conditions.

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

        # Use a transaction for the entire operation
        with self._transaction() as session:
            # Acquire a lock on the aro_assignments table for this date/period
            self._lock_aro_assignments(session, assignment_date, period)

            # Refresh the graph to ensure we have the latest data
            self.clear_caches()
            paths = self.find_optimal_aro_paths(understaffed_team_id, assignment_date, period)

            # Track virtual staffing changes
            virtual_staffing = {}  # team_id -> {added: [emp_ids], removed: [emp_ids]}

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

                                # Update virtual staffing
                                if from_team_id not in virtual_staffing:
                                    virtual_staffing[from_team_id] = {'added': [], 'removed': []}
                                if to_team_id not in virtual_staffing:
                                    virtual_staffing[to_team_id] = {'added': [], 'removed': []}

                                virtual_staffing[from_team_id]['removed'].append(employee_id)
                                virtual_staffing[to_team_id]['added'].append(employee_id)

                                if remaining_needed <= 0:
                                    break

                # For multi-hop paths
                else:
                    # Create a chain of assignments for each hop in the path
                    for hop_index in range(len(path)):
                        if remaining_needed <= 0:
                            break

                        # Process each hop in the path
                        current_hop = path[hop_index]
                        from_team_id = current_hop['from_team_id']
                        to_team_id = current_hop['to_team_id']

                        # For the first hop, use employees from the source team
                        if hop_index == 0:
                            available_employees = current_hop['employees'][:capacity]

                            for employee_id in available_employees:
                                # Assign employee to the intermediate team
                                result = self.aro_service.assign_aro(
                                    employee_id=employee_id,
                                    to_team_id=to_team_id,
                                    assignment_date=assignment_date,
                                    period=period
                                )

                                if result["status"] == 'success':
                                    # Update virtual staffing
                                    if from_team_id not in virtual_staffing:
                                        virtual_staffing[from_team_id] = {'added': [], 'removed': []}
                                    if to_team_id not in virtual_staffing:
                                        virtual_staffing[to_team_id] = {'added': [], 'removed': []}

                                    virtual_staffing[from_team_id]['removed'].append(employee_id)
                                    virtual_staffing[to_team_id]['added'].append(employee_id)

                        # For intermediate and final hops, use employees from the previous team
                        # that are now virtually available
                        else:
                            # Get employees that were virtually added to the from_team
                            virtually_added = virtual_staffing.get(from_team_id, {}).get('added', [])

                            # Get all employees from the from_team
                            from_team_employees = self.employee_repository.get_by_team_id(from_team_id)

                            # Find employees that can work at the to_team
                            to_team_workstations = self.workstation_repository.get_by_team_id(to_team_id)

                            # Prioritize employees that were virtually added
                            candidate_employees = []

                            # First check virtually added employees
                            for emp_id in virtually_added:
                                employee = next((e for e in from_team_employees if e.id == emp_id), None)
                                if employee and employee.is_available_for_period(assignment_date, period):
                                    # Check if employee can work at the target team
                                    can_work_at_target = False
                                    for workstation in to_team_workstations:
                                        if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                                            can_work_at_target = True
                                            break

                                    if can_work_at_target:
                                        candidate_employees.append(employee.id)

                            # Then check regular employees if needed
                            if len(candidate_employees) < capacity:
                                for employee in from_team_employees:
                                    if employee.id in virtually_added or not employee.is_available_for_period(assignment_date, period):
                                        continue

                                    # Check if employee can work at the target team
                                    can_work_at_target = False
                                    for workstation in to_team_workstations:
                                        if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                                            can_work_at_target = True
                                            break

                                    if can_work_at_target:
                                        candidate_employees.append(employee.id)

                                        if len(candidate_employees) >= capacity:
                                            break

                            # Assign the candidates
                            for employee_id in candidate_employees[:capacity]:
                                result = self.aro_service.assign_aro(
                                    employee_id=employee_id,
                                    to_team_id=to_team_id,
                                    assignment_date=assignment_date,
                                    period=period
                                )

                                if result["status"] == 'success':
                                    # Update virtual staffing
                                    if from_team_id not in virtual_staffing:
                                        virtual_staffing[from_team_id] = {'added': [], 'removed': []}
                                    if to_team_id not in virtual_staffing:
                                        virtual_staffing[to_team_id] = {'added': [], 'removed': []}

                                    virtual_staffing[from_team_id]['removed'].append(employee_id)
                                    virtual_staffing[to_team_id]['added'].append(employee_id)

                                    # For the final hop, add the assignment to the result
                                    if hop_index == len(path) - 1:
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

        return assignments
