from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import List
import uuid

from ..middleware import RequirePermission

router = APIRouter()

class PermissionSchema(BaseModel):
    resource: str
    action: str

class CreateRoleRequest(BaseModel):
    name: str
    description: str
    permissions: List[PermissionSchema]

@router.get("/roles", status_code=status.HTTP_200_OK)
async def list_roles(token: dict = Depends(RequirePermission("rbac", "manage"))):
    """
    List roles in tenant. Requires 'rbac:manage' permission.
    """
    return {
        "data": [
            {
                "id": str(uuid.uuid4()),
                "name": "ML Engineer",
                "is_system_role": False
            }
        ]
    }

@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(request: CreateRoleRequest, token: dict = Depends(RequirePermission("rbac", "manage"))):
    """
    Create a custom role. Requires 'rbac:manage' permission.
    """
    role_id = str(uuid.uuid4())
    return {
        "data": {
            "id": role_id,
            "name": request.name,
            "description": request.description,
            "is_system_role": False,
            "permissions": [p.model_dump() for p in request.permissions],
            "created_at": "2026-06-13T00:00:00Z"
        }
    }
