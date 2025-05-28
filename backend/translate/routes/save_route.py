# backend/translate/routes/save_route.py

from fastapi import APIRouter, Request
from backend.translate.services import translate_service

router = APIRouter()

@router.post('/save_translation')
async def save_translation(request: Request):
    data = await request.json()
    translate_service.save_translation(data)
    return {'status': 'ok'}

@router.patch('/favorite')
async def toggle_favorite(data: dict):
    translate_service.update_favorite_flag(data['id'], data['favorite'])
    return {'status': 'ok'}
