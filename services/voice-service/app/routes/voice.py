from fastapi import APIRouter, status, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict
import uuid
import asyncio
import io

router = APIRouter()

class SynthesizeRequest(BaseModel):
    text: str
    voice_id: str = "default_alloy"

class TranscribeResponse(BaseModel):
    recording_id: str
    s3_path: str
    text: str
    language: str

@router.post("/transcribe", status_code=status.HTTP_200_OK, response_model=Dict[str, TranscribeResponse])
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts an audio file, uploads it to MinIO, and calls an STT Model (mocked Whisper) to transcribe it.
    """
    recording_id = str(uuid.uuid4())
    s3_path = f"s3://eaioc-voice-recordings/{recording_id}_{file.filename}"
    
    _file_bytes = await file.read()
    
    # Simulate API call latency to Whisper
    await asyncio.sleep(1.0)
    
    return {
        "data": TranscribeResponse(
            recording_id=recording_id,
            s3_path=s3_path,
            text="This is a mocked transcription of the uploaded audio file.",
            language="en"
        )
    }

@router.post("/synthesize", status_code=status.HTTP_200_OK)
async def synthesize_speech(request: SynthesizeRequest):
    """
    Accepts text and streams back synthesized audio bytes (mocked TTS).
    """
    # Simulate API call latency to TTS model
    await asyncio.sleep(1.0)
    
    # Generate mock audio bytes (just an empty wave or dummy bytes)
    mock_audio = io.BytesIO(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\xbb\x00\x00\x00w\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    
    return StreamingResponse(
        mock_audio, 
        media_type="audio/wav",
        headers={"Content-Disposition": f"attachment; filename=synth_{uuid.uuid4()}.wav"}
    )
