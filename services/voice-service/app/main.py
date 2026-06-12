from fastapi import FastAPI
from eaioc_core.app import create_app
from eaioc_core.exceptions import api_exception_handler, APIException
from .routes import voice

app = create_app(
    title="Voice Service",
    description="EAIOC Speech-to-Text and Text-to-Speech API Wrapper",
    version="0.1.0",
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice"])
