# Test script to verify repository reorganization
import sys
import os

def test_repository_imports():
    """Test that all moved repositories can be imported from their new locations."""
    try:
        # Test user management repositories
        from infrastructure.repositories.user_management.sqlalchemy_user_repository import SqlAlchemyUserRepository
        from infrastructure.repositories.user_management.sqlalchemy_api_key_repository import SqlAlchemyApiKeyRepository
        from infrastructure.repositories.user_management.sqlalchemy_refresh_token_repository import SqlAlchemyRefreshTokenRepository
        print("✓ User management repositories imported successfully")
        
        # Test employee management repositories
        from infrastructure.repositories.employee_management.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
        from infrastructure.repositories.employee_management.sqlalchemy_team_member_repository import SqlAlchemyTeamMemberRepository
        print("✓ Employee management repositories imported successfully")
        
        # Test scheduling repositories
        from infrastructure.repositories.scheduling.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
        print("✓ Scheduling repositories imported successfully")
        
        # Test assignment repositories
        from infrastructure.repositories.assignment.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
        from infrastructure.repositories.assignment.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
        print("✓ Assignment repositories imported successfully")
        
        # Test workstation management repositories
        from infrastructure.repositories.workstation_management.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
        print("✓ Workstation management repositories imported successfully")
        
        print("\n✅ All repository imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Testing repository reorganization...")
    success = test_repository_imports()
    sys.exit(0 if success else 1)