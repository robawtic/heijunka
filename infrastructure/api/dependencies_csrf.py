from fastapi import Depends
from infrastructure.security.csrf import verify_csrf_token

# Create a dependency that can be used on all state-changing endpoints
csrf_protection = Depends(verify_csrf_token)

# Example usage:
# @router.post("/endpoint", dependencies=[csrf_protection])
# async def create_resource(...):
#     ...
