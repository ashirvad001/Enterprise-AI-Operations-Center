from fastapi import FastAPI
from eaioc_core.app import create_app
from eaioc_core.exceptions import api_exception_handler, APIException
from .routes import edge

app = create_app(
    title="Edge Manager",
    description="EAIOC Edge Device Control Plane",
    version="0.1.0",
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(edge.router, prefix="/api/v1/edge", tags=["Edge Management"])
