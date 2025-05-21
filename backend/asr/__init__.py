# backend/asr/__init__.py

from typing import Dict

model_registry: Dict[str, dict] = {}

def register_model(model_id: str, path: str, device: str, language: str):
    model_registry[model_id] = {
        "path": path,
        "device": device,
        "language": language,
        "status": "idle",
        "instance": None,
        "latency": None,
        "loaded_time": None
    }