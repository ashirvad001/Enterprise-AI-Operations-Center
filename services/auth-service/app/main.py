from fastapi import FastAPI
from eaioc_core.app import create_app
from eaioc_core.exceptions import api_exception_handler, APIException
from .routes import auth

app = create_app(
    title="Auth Service",
    description="EAIOC Authentication and Identity Provider",
    version="0.1.0",
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
