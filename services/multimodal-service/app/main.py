from fastapi import FastAPI
from eaioc_core.app import create_app
from eaioc_core.exceptions import api_exception_handler, APIException
from .routes import analyze

app = create_app(
    title="Multimodal Service",
    description="EAIOC Image parsing and Vision AI wrapper",
    version="0.1.0",
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(analyze.router, prefix="/api/v1/multimodal", tags=["Multimodal"])
