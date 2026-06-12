import os
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext

# Use Argon2id for password hashing per Security Architecture
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT Configuration
# In production, these would be loaded from HashiCorp Vault or AWS KMS
JWT_ALGORITHM = "RS256"
JWT_EXPIRATION_MINUTES = 15
JWT_ISSUER = "eaioc"
JWT_AUDIENCE = "eaioc-api"

# For local dev, we expect RS256 keys to be mounted or injected via env vars.
# If not present, we will fallback to HS256 for local dev simplicity if strictly configured,
# but our plan specified RS256. We'll simulate loading RS256 keys here.
PRIVATE_KEY = os.environ.get("JWT_PRIVATE_KEY", "mock_private_key")
PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "mock_public_key")
USE_HS256_FALLBACK = os.environ.get("JWT_ALGORITHM", JWT_ALGORITHM) == "HS256"
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "fallback_secret")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(
    user_id: str, 
    tenant_id: str, 
    email: str, 
    roles: list[str], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create an RS256 signed JWT access token."""
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        
    to_encode = {
        "sub": user_id,
        "tid": tenant_id,
        "email": email,
        "roles": roles,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": datetime.now(UTC),
        "exp": expire,
    }

    if USE_HS256_FALLBACK:
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm="HS256")
    else:
        # RS256 requires real PEM keys. If we hit the mock string, it'll fail in a real environment.
        # This is expected behavior enforcing proper key injection.
        encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm="RS256")
        
    return encoded_jwt
