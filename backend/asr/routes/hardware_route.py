# backend/asr/routes/hardware_route.py

from fastapi import APIRouter
from backend.asr.services import hardware_service

router = APIRouter()

@router.get("/hardware/info")
def get_hardware_info():
    return hardware_service.get_hardware_info()
