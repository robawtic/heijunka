import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import date

from presentation.api.app import app
from domain.contexts.employee_management.value_objects.work_history_entry import WorkHistoryEntry
from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation

# Create a test client
client = TestClient(app)

# Mock JWT token for testing
mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJyb2xlcyI6WyJhZG1pbiJdfQ.8mV_UfvLd7-9Z-QKBrG7jZ-Jf_KjLnCrJ5lvXJjvMqA"

@pytest.fixture
def mock_repositories():
    """Fixture to mock the repositories."""
    with patch("infrastructure.api.dependencies.get_repositories") as mock_get_repos:
        # Create mock repositories
        mock_work_history_repo = MagicMock()
        mock_employee_repo = MagicMock()
        mock_workstation_repo = MagicMock()
        mock_team_repo = MagicMock()
        
        # Configure the mock repositories
        mock_get_repos.return_value = {
            "work_history_repository": mock_work_history_repo,
            "employee_repository": mock_employee_repo,
            "workstation_repository": mock_workstation_repo,
            "team_repository": mock_team_repo
        }
        
        yield {
            "work_history_repository": mock_work_history_repo,
            "employee_repository": mock_employee_repo,
            "workstation_repository": mock_workstation_repo,
            "team_repository": mock_team_repo
        }

@pytest.fixture
def mock_auth():
    """Fixture to mock the authentication."""
    with patch("infrastructure.api.auth.jwt.decode") as mock_decode:
        # Configure the mock JWT decoder
        mock_decode.return_value = {
            "sub": "test_user",
            "roles": ["admin", "scheduler", "operator", "viewer"]
        }
        yield

def test_get_assignments(mock_repositories, mock_auth):
    """Test the get_assignments endpoint."""
    # Configure mock repositories
    mock_repos = mock_repositories
    
    # Mock work history entries
    work_history_entries = [
        WorkHistoryEntry(
            employee_id=1,
            workstation_id=1,
            worked_date=date.today(),
            work_period=1,
            end_flag=False
        ),
        WorkHistoryEntry(
            employee_id=2,
            workstation_id=2,
            worked_date=date.today(),
            work_period=2,
            end_flag=False
        )
    ]
    
    # Mock employees
    employee1 = Employee(id=1, name="John Doe", team_id=1, is_active=True)
    employee2 = Employee(id=2, name="Jane Smith", team_id=1, is_active=True)
    
    # Mock workstations
    workstation1 = Workstation(id=1, name="Station 1", team_id=1)
    workstation2 = Workstation(id=2, name="Station 2", team_id=1)
    
    # Configure mock repository responses
    mock_repos["work_history_repository"].get_filtered.return_value = (work_history_entries, 2)
    mock_repos["employee_repository"].get_by_id.side_effect = lambda id: {1: employee1, 2: employee2}.get(id)
    mock_repos["workstation_repository"].get_by_id.side_effect = lambda id: {1: workstation1, 2: workstation2}.get(id)
    mock_repos["team_repository"].get_by_id.return_value = MagicMock(id=1, name="Test Team")
    
    # Make request to the endpoint
    response = client.get(
        "/api/v1/assignments/",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "metadata" in data
    assert len(data["items"]) == 2
    assert data["metadata"]["total"] == 2
    
    # Check that the repository methods were called correctly
    mock_repos["work_history_repository"].get_filtered.assert_called_once()
    assert mock_repos["employee_repository"].get_by_id.call_count == 2
    assert mock_repos["workstation_repository"].get_by_id.call_count == 2

def test_create_assignment(mock_repositories, mock_auth):
    """Test the create_assignment endpoint."""
    # Configure mock repositories
    mock_repos = mock_repositories
    
    # Mock employee and workstation
    employee = Employee(id=1, name="John Doe", team_id=1, is_active=True)
    workstation = Workstation(id=1, name="Station 1", team_id=1)
    
    # Configure mock repository responses
    mock_repos["employee_repository"].get_by_id.return_value = employee
    mock_repos["workstation_repository"].get_by_id.return_value = workstation
    mock_repos["team_repository"].get_by_id.return_value = MagicMock(id=1, name="Test Team")
    
    # Mock the can_work method
    employee.can_work = MagicMock(return_value=True)
    
    # Make request to the endpoint
    response = client.post(
        "/api/v1/assignments/",
        json={
            "employee_id": 1,
            "workstation_id": 1,
            "date": date.today().isoformat(),
            "period": 1
        },
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == 1
    assert data["workstation_id"] == 1
    
    # Check that the repository methods were called correctly
    mock_repos["employee_repository"].get_by_id.assert_called_once_with(1)
    mock_repos["workstation_repository"].get_by_id.assert_called_once_with(1)
    mock_repos["work_history_repository"].create.assert_called_once()
    employee.can_work.assert_called_once_with(workstation)

def test_create_assignment_unqualified_employee(mock_repositories, mock_auth):
    """Test creating an assignment with an unqualified employee."""
    # Configure mock repositories
    mock_repos = mock_repositories
    
    # Mock employee and workstation
    employee = Employee(id=1, name="John Doe", team_id=1, is_active=True)
    workstation = Workstation(id=1, name="Station 1", team_id=1)
    
    # Configure mock repository responses
    mock_repos["employee_repository"].get_by_id.return_value = employee
    mock_repos["workstation_repository"].get_by_id.return_value = workstation
    
    # Mock the can_work method to return False
    employee.can_work = MagicMock(return_value=False)
    
    # Make request to the endpoint
    response = client.post(
        "/api/v1/assignments/",
        json={
            "employee_id": 1,
            "workstation_id": 1,
            "date": date.today().isoformat(),
            "period": 1
        },
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Check response
    assert response.status_code == 400
    data = response.json()
    assert "message" in data
    assert "not qualified" in data["message"]
    
    # Check that the repository methods were called correctly
    mock_repos["employee_repository"].get_by_id.assert_called_once_with(1)
    mock_repos["workstation_repository"].get_by_id.assert_called_once_with(1)
    mock_repos["work_history_repository"].create.assert_not_called()
    employee.can_work.assert_called_once_with(workstation)