import requests

# API base URL
base_url = "http://localhost:8888"

# Step 1: Get an access token
def get_token(username, password):
    """Get an access token from the API."""
    auth_url = f"{base_url}/api/v1/auth/token"
    
    # Important: Use form data, not JSON
    response = requests.post(
        auth_url,
        data={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        print(f"Error getting token: {response.status_code} - {response.text}")
        return None

# Step 2: Use the token to access protected endpoints
def get_teams(token):
    """Get teams using the access token."""
    teams_url = f"{base_url}/api/v1/teams/"
    
    # Include the token in the Authorization header
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(teams_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting teams: {response.status_code} - {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    # Get a token for the admin user
    token = get_token("admin", "password")
    
    if token:
        print(f"Successfully obtained token: {token[:20]}...")
        
        # Use the token to get teams
        teams = get_teams(token)
        
        if teams:
            print(f"Successfully retrieved {len(teams)} teams:")
            for team in teams:
                print(f"  - {team['name']} (ID: {team['id']})")