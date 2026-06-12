import os
import jwt
from fastapi import Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from eaioc_core.exceptions import APIException
import redis.asyncio as redis

security = HTTPBearer()

# In production, load public key from Vault
PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "mock_public_key")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "fallback_secret")

# Redis connection for caching authorization decisions
redis_client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))

async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Validates the JWT token and returns the decoded payload.
    """
    token = credentials.credentials
    try:
        if JWT_ALGORITHM == "HS256":
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"], audience="eaioc-api")
        else:
            payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"], audience="eaioc-api")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise APIException(status_code=401, title="Token Expired", detail="The access token has expired.", error_type="auth/token-expired")
    except jwt.InvalidTokenError:
        raise APIException(status_code=401, title="Invalid Token", detail="The access token is invalid.", error_type="auth/invalid-token")

class RequirePermission:
    """
    Dependency class to enforce RBAC permissions.
    Checks the JWT roles and queries Redis to see if the roles grant the required resource:action.
    """
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action

    async def __call__(self, token_payload: dict = Depends(get_current_user_token)):
        user_id = token_payload.get("sub")
        roles = token_payload.get("roles", [])
        
        if not user_id:
            raise APIException(status_code=401, title="Invalid Token", detail="Subject missing from token.", error_type="auth/invalid-token")
            
        # Super Admin override bypasses checks
        if "super_admin" in roles:
            return token_payload

        # Mock RBAC check
        # In reality, this queries Redis: `await redis_client.get(f"rbac:{user_id}:{self.resource}:{self.action}")`
        # and falls back to database if not cached.
        
        # For scaffold, allow if developer
        if "developer" in roles:
            return token_payload
            
        raise APIException(
            status_code=403,
            title="Forbidden",
            detail=f"You do not have permission to perform {self.action} on {self.resource}.",
            error_type="auth/forbidden"
        )
