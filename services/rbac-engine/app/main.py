from fastapi import FastAPI
from eaioc_core.app import create_app
from eaioc_core.exceptions import api_exception_handler, APIException
from .routes import roles

app = create_app(
    title="RBAC Engine",
    description="EAIOC Role-Based Access Control and Authorization Service",
    version="0.1.0",
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(roles.router, prefix="/api/v1/rbac", tags=["RBAC"])
