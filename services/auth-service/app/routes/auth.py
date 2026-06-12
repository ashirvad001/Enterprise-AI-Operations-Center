from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, EmailStr
from ..security import get_password_hash, verify_password, create_access_token
from eaioc_core.exceptions import APIException
import uuid

router = APIRouter()

# --- Pydantic Schemas ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- Endpoints ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user and organization.
    In a real implementation, this interacts with eaioc-database via SQLAlchemy session.
    """
    # Mocking database interaction for scaffold
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    # Simulate saving hash
    _hashed_pw = get_password_hash(request.password)
    
    return {
        "data": {
            "user_id": user_id,
            "email": request.email,
            "tenant_id": tenant_id,
            "organization_name": request.organization_name,
            "is_verified": False,
            "message": "Verification email sent. Please check your inbox."
        }
    }

@router.post("/login", status_code=status.HTTP_200_OK)
async def login(request: LoginRequest):
    """
    Authenticate with email and password.
    Returns an RS256 signed JWT if credentials are valid.
    """
    # Mock DB fetch and verify
    # In reality: user = await session.execute(select(User).where(User.email == request.email))
    
    # We will accept any login for local dev scaffolding right now
    if not request.email or not request.password:
        raise APIException(
            status_code=401,
            title="Invalid Credentials",
            detail="The email or password provided is incorrect.",
            error_type="auth/invalid-credentials"
        )
        
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    roles = ["developer"]
    
    token = create_access_token(user_id=user_id, tenant_id=tenant_id, email=request.email, roles=roles)
    
    return {
        "data": {
            "access_token": token,
            "refresh_token": "rt_mock_token_123",
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {
                "id": user_id,
                "email": request.email,
                "full_name": "Test User",
                "tenant_id": tenant_id,
                "roles": roles
            }
        }
    }
