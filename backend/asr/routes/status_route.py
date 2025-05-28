# backend/asr/routes/status_route.py

from fastapi import APIRouter
from backend.asr.services import status_service as status

router = APIRouter()

@router.get("/asr/status")
def get_asr_status():
    return status.check_asr_status()

@router.get("/asr/db/info")
def get_db_info():
    return status.get_db_info()

@router.get("/asr/model/info")
def get_loaded_model_info():
    return status.get_loaded_model_info()
