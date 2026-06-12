from fastapi import FastAPI
from eaioc_core.app import create_app
from eaioc_core.exceptions import api_exception_handler, APIException
from .routes import mlops

app = create_app(
    title="MLOps Service",
    description="EAIOC Model Registry and Telemetry Tracker",
    version="0.1.0",
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(mlops.router, prefix="/api/v1/mlops", tags=["MLOps"])
