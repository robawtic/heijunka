# CSRF Protection in Heijunka

This document explains how CSRF protection is implemented in the Heijunka application and how to use it in your routes.

## Overview

CSRF (Cross-Site Request Forgery) protection is implemented using the `fastapi-csrf-protect` library. This library provides middleware-free CSRF protection through FastAPI dependencies.

## Implementation

The CSRF protection is implemented in the following files:

- `infrastructure/security/csrf.py`: Contains the core CSRF protection functions
- `infrastructure/config/csrf_config.py`: Contains the CSRF configuration
- `infrastructure/api/dependencies_csrf.py`: Contains a reusable dependency for CSRF protection

## Setup

### Generating a Secure CSRF Secret

For security reasons, you should use a strong random secret for CSRF protection. You can generate a secure secret using Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Environment Configuration

Add the following variables to your `.env` file:

```env
# CSRF Protection
CSRF_SECRET=your_generated_secret_here
COOKIE_SECURE=true  # Set to false for local development without HTTPS
SESSION_MAX_AGE=14400  # Session timeout in seconds (4 hours)
```

## How to Use

### Getting a CSRF Token

Before making any state-changing requests (POST, PUT, DELETE), the client needs to obtain a CSRF token. This can be done by calling the `/api/v1/auth/csrf-token` endpoint:

```http
GET /api/v1/auth/csrf-token
```

This will set a CSRF token in a cookie named `csrftoken`.

### Using the CSRF Token

When making state-changing requests, the client must include the CSRF token in the `X-CSRF-Token` header:

```http
POST /api/v1/some-endpoint
X-CSRF-Token: <token-from-cookie>
```

### Protecting Routes

There are two recommended ways to protect routes with CSRF validation:

#### 1. Using the `csrf_protection` dependency

```python
from infrastructure.api.dependencies_csrf import csrf_protection

@router.post("/endpoint", dependencies=[csrf_protection])
async def create_resource(...):
    ...
```

#### 2. Using the `CSRFSecurity` class (Recommended)

The `CSRFSecurity` class is the most idiomatic approach for FastAPI and provides several benefits:
- FastAPI-native dependency injection
- Proper injection of dependencies
- Support for logging
- Reusable across routes

```python
# Method 1: Using dependencies parameter with callable syntax
from infrastructure.security.csrf import CSRFSecurity

@router.post("/endpoint", dependencies=[Depends(CSRFSecurity())])
async def create_resource(...):
    ...
```

```python
# Method 2: Using dependencies parameter with validate method
from infrastructure.security.csrf import CSRFSecurity

@router.post("/endpoint", dependencies=[Depends(CSRFSecurity().validate)])
async def create_resource(...):
    ...
```

```python
# Method 3: Injecting as a parameter (more concise)
from infrastructure.security.csrf import CSRFSecurity

@router.post("/endpoint")
async def create_resource(..., csrf: CSRFSecurity = Depends()):
    # Validate CSRF token inside the route
    csrf.validate()
    ...
```

```python
# Method 4: Using the context manager (validates and sets cookie)
from infrastructure.security.csrf import CSRFSecurity, csrf_protected

@router.post("/endpoint")
async def create_resource(response: Response, csrf: CSRFSecurity = Depends()):
    with csrf_protected(response, csrf):
        # Your code here - CSRF is validated before and cookie is set after
        return {"message": "Resource created with CSRF protection"}
```

For GET endpoints that should set a CSRF token for subsequent requests, use one of the following:

```python
# Using the set_csrf_cookie dependency
from infrastructure.security.csrf import set_csrf_cookie

@router.get("/endpoint")
async def get_resource(response: Response, _=Depends(set_csrf_cookie)):
    ...

# Using the CSRFSecurity class
from infrastructure.security.csrf import CSRFSecurity

@router.get("/endpoint")
async def get_resource(response: Response, csrf: CSRFSecurity = Depends()):
    csrf.set_cookie(response)
    ...
```

## Security Considerations

- The CSRF token is stored in a cookie with the `httponly` flag set to `True` to prevent JavaScript access.
- The `secure` flag is set based on the `COOKIE_SECURE` environment variable (should be `True` in production).
- The `samesite` attribute is set to `lax` to prevent the cookie from being sent in cross-site requests.

## Testing

A test for the CSRF protection is provided in `presentation/api/tests/test_csrf.py`. This test verifies that:

1. The CSRF token can be obtained from the `/api/v1/auth/csrf-token` endpoint
2. The token can be used to make a state-changing request
3. Requests without a valid CSRF token are blocked

To run the test:

```bash
python -m unittest presentation.api.tests.test_csrf
```

## Testing with curl

### 1. Get a CSRF Token

First, get a CSRF token from the server:

```bash
curl -v -X GET "http://localhost:8000/api/v1/auth/csrf-token" \
  -c csrf_cookies.txt
```

This will save the CSRF cookie to a file called `csrf_cookies.txt`.

### 2. Extract the CSRF Token from the Cookie

You can extract the token from the cookie file:

```bash
CSRF_TOKEN=$(grep csrftoken csrf_cookies.txt | awk '{print $7}')
echo $CSRF_TOKEN
```

### 3. Use the CSRF Token in a Protected Request

Now you can use the token in a protected request:

```bash
curl -v -X POST "http://localhost:8000/api/v1/teams" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -b csrf_cookies.txt \
  -d '{"name": "New Team", "description": "Team created with CSRF protection"}'
```

### 4. Test Without CSRF Token (Should Fail)

This request should fail with a 403 Forbidden error:

```bash
curl -v -X POST "http://localhost:8000/api/v1/teams" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Team", "description": "This should fail"}'
```

### 5. Test with Invalid CSRF Token (Should Fail)

This request should also fail with a 403 Forbidden error:

```bash
curl -v -X POST "http://localhost:8000/api/v1/teams" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: invalid_token" \
  -b csrf_cookies.txt \
  -d '{"name": "New Team", "description": "This should fail"}'
```
