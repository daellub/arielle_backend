# backend/asr/routes/log_route.py

from fastapi import APIRouter, Query
from typing import Optional, List
from backend.asr.services import log_service

router = APIRouter()

@router.get('/logs')
def get_logs(
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    type: Optional[str] = None,
    query: Optional[str] = None,
    since: Optional[str] = Query(None, description='ISO timestamp')
):
    return log_service.fetch_logs(limit, offset, type, query, since)

@router.get('/log-suggestions', response_model=List[str])
def get_log_suggestions(q: str = Query(..., min_length=1, description='검색어 앞글자')):
    return log_service.fetch_log_suggestions(q)
