# backend/asr/routes/service_route.py

from fastapi import HTTPException, APIRouter, WebSocket, Body
from backend.asr.schemas import ModelRegister
from backend.utils.encryption import decrypt
from backend.db.asr_db import get_model_by_id
from backend.asr.services import recognition_service as recog, log_service as logs

router = APIRouter()

@router.post('/models/register')
def register_model(model: ModelRegister):
    model_id = recog.register_model(model)
    return {'status': 'registered', 'model_id': model_id}

@router.post('/models/load/{model_id}')
def load_model(model_id: str):
    info = recog.load_model(model_id)
    return {'status': 'loaded', 'model_id': model_id}

@router.post('/models/unload/{model_id}')
def unload_model(model_id: str):
    ok = recog.unload_model(model_id)
    return {'status': 'success' if ok else 'skipped', 'model_id': model_id}

@router.post('/save/result')
def save_transcription(model: str = Body(...), text: str = Body(...), language: str = Body('ko')):
    logs.save_transcription_to_db(model, text, language)
    return {'status': 'saved'}

@router.get('/models')
def list_models():
    return recog.list_models()

@router.get('/models/{model_id}/credentials')
def get_model_credentials(model_id: str):
    model = get_model_by_id(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다.")
    
    try:
        decrypted_apiKey = decrypt(model['apiKey'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API 키 복호화 실패: {str(e)}")
    
    return {
        'id': model['id'],
        'name': model['name'],
        'apiKey': decrypted_apiKey,
        'region': model['region'],
        'endpoint': model['endpoint'],
        'language': model['language'] or 'ko-KR'
    }
    
@router.delete('/models/{model_id}')
def delete_model(model_id: str):
    recog.delete_model(model_id)
    return {'status': 'deleted', 'model_id': model_id}

@router.websocket('/ws/inference/{model_id}')
async def websocket_inference(websocket: WebSocket, model_id: str):
    await recog.handle_websocket_inference(websocket, model_id)
