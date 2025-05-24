# Heijunka API Authentication Guide

This guide explains how to properly authenticate with the Heijunka API and access protected endpoints.

## Authentication Flow

The Heijunka API uses JWT (JSON Web Token) authentication. The flow is as follows:

1. Send a POST request to `/api/v1/auth/token` with your username and password to get an access token
2. Include the token in the `Authorization` header of subsequent requests with the format `Bearer {token}`

## Common Authentication Issues

### "Not authenticated" Error

If you're getting a "Not authenticated" error when trying to access protected endpoints, it's likely because:

1. You haven't included the token in your request
2. The token is not formatted correctly in the Authorization header
3. The token has expired

### Correct Way to Include the Token

The token must be included in the `Authorization` header with the format `Bearer {token}`:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Note the space between "Bearer" and the token.

## Example Code

### Python Example

```python
import requests

# Get a token
auth_url = "http://localhost:8888/api/v1/auth/token"
response = requests.post(
    auth_url,
    data={"username": "admin", "password": "password"}
)
token = response.json()["access_token"]

# Use the token to access a protected endpoint
teams_url = "http://localhost:8888/api/v1/teams/"
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(teams_url, headers=headers)
teams = response.json()
```

### JavaScript Example

```javascript
// Get a token
const formData = new FormData();
formData.append('username', 'admin');
formData.append('password', 'password');

fetch('http://localhost:8888/api/v1/auth/token', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    const token = data.access_token;
    
    // Use the token to access a protected endpoint
    fetch('http://localhost:8888/api/v1/teams/', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => response.json())
    .then(teams => console.log(teams));
});
```

## Using the Swagger UI

The API provides a Swagger UI at `/docs` that you can use to explore and test the API:

1. Navigate to `http://localhost:8888/docs`
2. Click the "Authorize" button (🔓 icon) at the top right
3. Enter your username and password
4. Click "Authorize"
5. Now you can use the Swagger UI to test protected endpoints

## Available Test Users

The API has the following predefined test users:

| Username  | Password  | Role       | Permissions                        |
|-----------|-----------|------------|-----------------------------------|
| admin     | password  | ADMIN      | Full access to all resources      |
| scheduler | password  | SCHEDULER  | Create and manage schedules       |
| operator  | password  | OPERATOR   | View and update assignments       |
| viewer    | password  | VIEWER     | Read-only access to resources     |

## Token Expiration

Tokens have an expiration time (default is 30 minutes). When a token expires, you'll need to request a new one.

## Complete Examples

For complete working examples, see:

- `examples/auth_example.py` - Python example
- `examples/auth_example.html` - Browser-based example