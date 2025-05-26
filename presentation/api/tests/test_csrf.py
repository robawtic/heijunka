import unittest
from fastapi.testclient import TestClient
from presentation.api.app import app

class TestCSRFProtection(unittest.TestCase):
    """Test cases for CSRF protection."""

    def setUp(self):
        """Set up the test client."""
        self.client = TestClient(app)

    def test_csrf_token_roundtrip(self):
        """Test the CSRF token roundtrip flow."""
        # Step 1: GET token
        res = self.client.get("/api/v1/auth/csrf-token")
        assert res.status_code == 200
        assert "message" in res.json()
        
        # Check that the CSRF cookie was set
        csrf_token = res.cookies.get("csrftoken")
        assert csrf_token is not None
        
        # Step 2: Use it on a protected endpoint (login)
        headers = {"X-CSRF-Token": csrf_token}
        login_data = {"username": "testuser", "password": "testpassword"}
        res = self.client.post(
            "/api/v1/auth/token", 
            json=login_data, 
            headers=headers, 
            cookies=res.cookies
        )
        
        # This might fail if the test user doesn't exist, but we're testing CSRF flow
        # not authentication success
        assert res.status_code != 403, "CSRF protection failed"
        
    def test_csrf_protection_blocks_requests(self):
        """Test that requests without CSRF token are blocked."""
        # Try to access a protected endpoint without CSRF token
        login_data = {"username": "testuser", "password": "testpassword"}
        res = self.client.post("/api/v1/auth/token", json=login_data)
        
        # Should be blocked with 403 Forbidden
        assert res.status_code == 403
        assert "Invalid CSRF token" in res.json().get("detail", "")

if __name__ == "__main__":
    unittest.main()