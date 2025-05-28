# backend/asr/routes/hf_download_route.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.sio import sio
from backend.asr.services import hf_download_service as hf

router = APIRouter(prefix="/models")

class DownloadRequest(BaseModel):
    model_id: str

@router.post("/cancel-download")
async def cancel_download(req: DownloadRequest):
    hf.cancel_download(req.model_id)
    return {"status": "cancel_requested"}

@router.post("/download-model")
async def download_model(req: DownloadRequest):
    try:
        await hf.download_model(req.model_id, sio)
        return {"status": "done"}
    except Exception as e:
        print(f"[ERROR] 다운로드 실패 또는 취소: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        hf.clear_flag(req.model_id)
