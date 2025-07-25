# Production Readiness Validation Script
# Tests critical imports and bounded context structure

import sys
import traceback

def test_bounded_context_imports():
    """Test that all bounded context imports work correctly"""
    print("🔍 Testing Bounded Context Imports...")
    
    test_results = []
    
    # Test Employee Management Context
    try:
        from domain.contexts.employee_management.entities.employee import Employee
        from domain.contexts.employee_management.entities.team import Team
        from domain.contexts.employee_management.entities.group import Group
        test_results.append(("Employee Management Entities", "✅ PASS"))
    except Exception as e:
        test_results.append(("Employee Management Entities", f"❌ FAIL: {str(e)}"))
    
    # Test Workstation Management Context
    try:
        from domain.contexts.workstation_management.entities.workstation import Workstation
        from domain.contexts.workstation_management.value_objects.line_type import LineType
        test_results.append(("Workstation Management", "✅ PASS"))
    except Exception as e:
        test_results.append(("Workstation Management", f"❌ FAIL: {str(e)}"))
    
    # Test Assignment Context
    try:
        from domain.contexts.assignment.entities.work_assignment import WorkAssignment
        test_results.append(("Assignment Context", "✅ PASS"))
    except Exception as e:
        test_results.append(("Assignment Context", f"❌ FAIL: {str(e)}"))
    
    # Test Scheduling Context
    try:
        from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod
        test_results.append(("Scheduling Context", "✅ PASS"))
    except Exception as e:
        test_results.append(("Scheduling Context", f"❌ FAIL: {str(e)}"))
    
    # Test User Management Context
    try:
        from domain.contexts.user_management.entities.user import User
        test_results.append(("User Management Context", "✅ PASS"))
    except Exception as e:
        test_results.append(("User Management Context", f"❌ FAIL: {str(e)}"))
    
    return test_results

def test_infrastructure_repositories():
    """Test that infrastructure repositories are accessible"""
    print("🔍 Testing Infrastructure Repository Access...")
    
    test_results = []
    
    # Test Employee Management Repositories
    try:
        from infrastructure.repositories.employee_management.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
        from infrastructure.repositories.employee_management.sqlalchemy_team_repository import SqlAlchemyTeamRepository
        test_results.append(("Employee Management Repositories", "✅ PASS"))
    except Exception as e:
        test_results.append(("Employee Management Repositories", f"❌ FAIL: {str(e)}"))
    
    # Test Workstation Management Repositories
    try:
        from infrastructure.repositories.workstation_management.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
        test_results.append(("Workstation Management Repositories", "✅ PASS"))
    except Exception as e:
        test_results.append(("Workstation Management Repositories", f"❌ FAIL: {str(e)}"))
    
    # Test Assignment Repositories
    try:
        from infrastructure.repositories.assignment.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
        test_results.append(("Assignment Repositories", "✅ PASS"))
    except Exception as e:
        test_results.append(("Assignment Repositories", f"❌ FAIL: {str(e)}"))
    
    return test_results

def test_legacy_imports_removed():
    """Test that legacy imports are properly removed"""
    print("🔍 Testing Legacy Import Removal...")
    
    test_results = []
    
    # Test that domain.entities imports are cleaned up
    try:
        import domain.entities
        # Should not have the old imports anymore
        if not hasattr(domain.entities, 'Employee'):
            test_results.append(("Domain Entities Cleanup", "✅ PASS - Legacy imports removed"))
        else:
            test_results.append(("Domain Entities Cleanup", "⚠️ WARNING - Legacy imports still present"))
    except Exception as e:
        test_results.append(("Domain Entities Cleanup", f"❌ FAIL: {str(e)}"))
    
    # Test that domain.repositories.buses imports are cleaned up
    try:
        import domain.repositories.implementations
        # Should not have the old repository imports anymore
        if not hasattr(domain.repositories.implementations, 'SqlAlchemyEmployeeRepository'):
            test_results.append(("Domain Repository Implementations Cleanup", "✅ PASS - Legacy imports removed"))
        else:
            test_results.append(("Domain Repository Implementations Cleanup", "⚠️ WARNING - Legacy imports still present"))
    except Exception as e:
        test_results.append(("Domain Repository Implementations Cleanup", f"❌ FAIL: {str(e)}"))
    
    return test_results

def main():
    """Run all validation tests"""
    print("🚀 Production Readiness Validation")
    print("=" * 50)
    
    all_results = []
    
    # Run all test suites
    all_results.extend(test_bounded_context_imports())
    all_results.extend(test_infrastructure_repositories())
    all_results.extend(test_legacy_imports_removed())
    
    # Print results
    print("\n📊 Validation Results:")
    print("-" * 50)
    
    passed = 0
    failed = 0
    warnings = 0
    
    for test_name, result in all_results:
        print(f"{test_name}: {result}")
        if "✅ PASS" in result:
            passed += 1
        elif "❌ FAIL" in result:
            failed += 1
        elif "⚠️ WARNING" in result:
            warnings += 1
    
    print("-" * 50)
    print(f"📈 Summary: {passed} passed, {failed} failed, {warnings} warnings")
    
    if failed == 0:
        print("🎉 Production Readiness: READY")
        return True
    else:
        print("⚠️ Production Readiness: ISSUES DETECTED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)