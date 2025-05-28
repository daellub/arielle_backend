# backend/tts/routes.py
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
import requests
import uuid

router = APIRouter()

TTS_SERVER_URL = "http://host.docker.internal:5000/voice"

class TTSRequest(BaseModel):
    text: str
    model_id: int = 0
    speaker_id: int = 0
    style: str = "Neutral"
    language: str = "JP"
    
@router.post("/synthesize")
def synthesize_tts(req: TTSRequest):
    try:
        response = requests.post(TTS_SERVER_URL, json=req.dict())
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = f"{uuid.uuid4().hex}.wav"
    return Response(
        content=response.content,
        media_type="audio/wav",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )