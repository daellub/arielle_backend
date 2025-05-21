# backend/asr/schemas.py

from pydantic import BaseModel
from typing import Optional

class ModelRegister(BaseModel):
    name: str
    type: str
    framework: str
    device: str
    language: str
    path: str
    status: Optional[str] = "idle"
    main: Optional[str] = ""
    endpoint: Optional[str] = ""
    region: Optional[str] = ""
    apiKey: Optional[str] = ""

class InferenceRequest(BaseModel):
    model_id: str
    audio: list[float]
    language: Optional[str] = "<|ko|>"