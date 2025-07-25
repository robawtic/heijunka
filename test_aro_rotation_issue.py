#!/usr/bin/env python3
"""
Test script to reproduce the ARO rotation issue.
This script demonstrates that the same ARO gets assigned to the same workstation every period.
"""

import sys
import os
from datetime import date, timedelta
from typing import List, Dict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.services.aro_orchestration_service import AROOrchestrationService


class MockAROService:
    """Mock ARO service for testing"""
    
    def __init__(self):
        # Simulate 3 qualified AROs for each workstation
        self.mock_aro_mapping = {
            1: [101, 102, 103],  # Workstation 1 has 3 qualified AROs
            2: [102, 103, 104],  # Workstation 2 has 3 qualified AROs (some overlap)
            3: [103, 104, 105],  # Workstation 3 has 3 qualified AROs
        }
    
    def get_workstation_aro_mapping(self, team_id: int, period: int = None, 
                                   assignment_date: date = None, 
                                   empty_workstations: List[Workstation] = None) -> Dict[int, List[int]]:
        """Return mock ARO mapping"""
        print(f"  ARO Service called with period={period} (should vary, but currently hardcoded to 1)")
        
        if not empty_workstations:
            return {}
        
        result = {}
        for workstation in empty_workstations:
            if workstation.id in self.mock_aro_mapping:
                result[workstation.id] = self.mock_aro_mapping[workstation.id]
        
        return result


def create_test_data():
    """Create test employees and workstations"""
    
    # Create ARO employees with different qualification levels using actual Employee class
    aros = []
    
    # ARO Alice - 3 qualifications
    alice = Employee(id=101, name="ARO_Alice", team_id=10)
    alice.add_qualification("qual1")
    alice.add_qualification("qual2") 
    alice.add_qualification("qual3")
    aros.append(alice)
    
    # ARO Bob - 2 qualifications
    bob = Employee(id=102, name="ARO_Bob", team_id=10)
    bob.add_qualification("qual1")
    bob.add_qualification("qual2")
    aros.append(bob)
    
    # ARO Charlie - 3 qualifications (tie with Alice)
    charlie = Employee(id=103, name="ARO_Charlie", team_id=10)
    charlie.add_qualification("qual1")
    charlie.add_qualification("qual2")
    charlie.add_qualification("qual3")
    aros.append(charlie)
    
    # ARO Diana - 1 qualification
    diana = Employee(id=104, name="ARO_Diana", team_id=10)
    diana.add_qualification("qual1")
    aros.append(diana)
    
    # ARO Eve - 2 qualifications
    eve = Employee(id=105, name="ARO_Eve", team_id=10)
    eve.add_qualification("qual1")
    eve.add_qualification("qual2")
    aros.append(eve)
    
    # Create workstations using actual Workstation class
    workstations = [
        Workstation(id=1, name="Assembly_Line_1"),
        Workstation(id=2, name="Quality_Check_1"), 
        Workstation(id=3, name="Packaging_1"),
    ]
    
    return aros, workstations


def test_aro_rotation_issue():
    """Test that demonstrates the ARO rotation issue"""
    
    print("=== ARO Rotation Issue Test ===\n")
    
    # Create test data
    aros, workstations = create_test_data()
    
    # Create ARO lookup
    aro_lookup = {aro.id: aro for aro in aros}
    
    # Create orchestration service with mock ARO service
    mock_aro_service = MockAROService()
    orchestration_service = AROOrchestrationService(aro_service=mock_aro_service)
    
    print("Test Setup:")
    print(f"- {len(aros)} ARO employees available")
    print(f"- {len(workstations)} workstations need coverage")
    print(f"- ARO qualifications:")
    for aro in aros:
        print(f"  {aro.name} (ID: {aro.id}): {len(aro.qualifications)} qualifications")
    print()
    
    # Simulate multiple periods/days to show the same assignments
    test_scenarios = [
        ("Day 1, Period 1", date.today(), 1),
        ("Day 1, Period 2", date.today(), 2), 
        ("Day 1, Period 3", date.today(), 3),
        ("Day 2, Period 1", date.today() + timedelta(days=1), 1),
        ("Day 2, Period 2", date.today() + timedelta(days=1), 2),
    ]
    
    print("Testing ARO assignments across different periods:")
    print("=" * 60)
    
    assignments_by_scenario = {}
    
    for scenario_name, test_date, period in test_scenarios:
        print(f"\n{scenario_name}:")
        print("-" * 30)
        
        # Get ARO mapping (this will always use period=1 due to hardcoding)
        aro_mapping = mock_aro_service.get_workstation_aro_mapping(
            team_id=1,
            period=period,  # This should vary but gets ignored
            assignment_date=test_date,
            empty_workstations=workstations
        )
        
        # Test ARO selection for each workstation
        assigned_aro_ids = set()
        scenario_assignments = {}
        
        for workstation in workstations:
            if workstation.id in aro_mapping:
                qualified_aro_ids = aro_mapping[workstation.id]
                
                # Use the orchestration service's selection method
                selected_aro = orchestration_service._select_best_aro_for_workstation(
                    workstation=workstation,
                    qualified_aro_ids=qualified_aro_ids,
                    aro_lookup=aro_lookup,
                    assigned_aro_ids=assigned_aro_ids
                )
                
                if selected_aro:
                    assigned_aro_ids.add(selected_aro.id)
                    scenario_assignments[workstation.id] = selected_aro.id
                    print(f"  {workstation.name} -> {selected_aro.name} (ID: {selected_aro.id})")
                else:
                    print(f"  {workstation.name} -> No ARO assigned")
        
        assignments_by_scenario[scenario_name] = scenario_assignments
    
    # Analyze results
    print("\n" + "=" * 60)
    print("ANALYSIS - Demonstrating the Issue:")
    print("=" * 60)
    
    # Check if assignments are identical across scenarios
    first_scenario = list(assignments_by_scenario.keys())[0]
    first_assignments = assignments_by_scenario[first_scenario]
    
    identical_count = 0
    for scenario_name, assignments in assignments_by_scenario.items():
        if assignments == first_assignments:
            identical_count += 1
    
    print(f"\nResults:")
    print(f"- Total scenarios tested: {len(assignments_by_scenario)}")
    print(f"- Scenarios with identical assignments: {identical_count}")
    print(f"- Assignment variation: {len(assignments_by_scenario) - identical_count} different patterns")
    
    if identical_count == len(assignments_by_scenario):
        print("\n❌ ISSUE CONFIRMED: Same ARO assigned to same workstation in ALL scenarios!")
        print("   This demonstrates the lack of rotation logic.")
    else:
        print("\n✅ Assignments vary across scenarios (rotation working)")
    
    print(f"\nDetailed breakdown:")
    for workstation in workstations:
        assigned_aros = set()
        for scenario_assignments in assignments_by_scenario.values():
            if workstation.id in scenario_assignments:
                assigned_aros.add(scenario_assignments[workstation.id])
        
        aro_names = [aro_lookup[aro_id].name for aro_id in assigned_aros]
        print(f"- {workstation.name}: {len(assigned_aros)} different AROs assigned -> {', '.join(aro_names)}")
    
    print(f"\n" + "=" * 60)
    print("ISSUES IDENTIFIED:")
    print("1. Period parameter is hardcoded to 1 in orchestration service")
    print("2. Selection method uses deterministic max() without rotation logic")
    print("3. No historical assignment tracking for diversity")
    print("4. No randomization for tie-breaking between equal candidates")


if __name__ == "__main__":
    test_aro_rotation_issue()