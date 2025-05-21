# backend/asr/service.py

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Body
import numpy as np

from backend.asr.model_manager import model_manager
from backend.asr.schemas import ModelRegister
from backend.db.database import delete_model_from_db, get_models_from_db, save_result_to_db, save_log_to_db

router = APIRouter()

@router.post('/models/register')
def register_model(model: ModelRegister):
    model_id = model_manager.register(model)
    return {'status': 'registered', 'model_id': model_id}

@router.post('/models/load/{model_id}')
def load_model(model_id: str):
    model_manager.load_model(model_id)

    model_info = model_manager.models[model_id]['info']
    save_log_to_db(
        log_type='INFO',
        message=f'Model {model_info.name} loaded (device={model_info.device})',
        source='MODEL'
    )

    return {'status': 'loaded', 'model_id': model_id}

@router.post('/models/unload/{model_id}')
def unload_model(model_id: str):
    ok = model_manager.unload_model(model_id)

    if ok:
        model_info = model_manager.models[model_id]['info']
        save_log_to_db(
            log_type="INFO",
            message=f"Model {model_info.name} unloaded",
            source="MODEL"
        )

    return {
        'status': 'success' if ok else 'skipped', 'model_id': model_id
    }

@router.post('/save/result')
async def save_transcription(
    model: str = Body(...),
    text: str = Body(...),
    language: str = Body('ko')
):
    try:
        save_result_to_db(model_name=model, text=text, language=language)
        save_log_to_db(
            log_type='DB',
            message=f'Saved transcription result to DB (model={model})',
            source='BACKEND'
        )
        return {'status': 'saved'}
    except Exception as e:
        save_log_to_db(
            log_type='ERROR',
            message=f'DB Save Failed: {str(e)}',
            source='BACKEND'
        )
        raise

@router.get('/models')
def list_models():
    models = get_models_from_db()
    for m in models:
        m['logo'] = m.get('logo', '/static/icons/default.svg')
    return models

@router.delete('/models/{model_id}')
def delete_model(model_id: str):
    if model_id in model_manager.models:
        del model_manager.models[model_id]
    delete_model_from_db(model_id)
    return {'status': 'deleted', 'model_id': model_id}

@router.websocket('/ws/inference/{model_id}')
async def websocket_inference(websocket: WebSocket, model_id: str):
    await websocket.accept()

    # 모델 유효성 검사
    if model_id not in model_manager.models:
        await websocket.send_text("error: 모델이 존재하지 않습니다.")
        await websocket.close()
        return
    
    entry = model_manager.models[model_id]
    if not entry['loaded']:
        await websocket.send_text('error: 모델이 로드되지 않음')
        await websocket.close()
        return
    
    inst = entry["instance"]
    fw = entry["info"].framework.lower()

    if fw == 'openvino':
        save_log_to_db("INFO", f"Whisper WebSocket opened: model_id={model_id}", "MODEL")
        await websocket.send_text('🎙 Whisper 전사 준비 완료')
        try:
            while True:
                audio_bytes = await websocket.receive_bytes()
                audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
                texts = inst['pipeline'].generate(audio_np, language='<|ko|>').texts
                for t in texts:
                    await websocket.send_text(t)
        except WebSocketDisconnect:
            print(f'[INFO] Whisper WebSocket 종료: {model_id}')

    elif fw == 'azure':
        print('Azure API는 Socket에서 직접 처리합니다.')

    else:
        await websocket.send_text('error: 지원하지 않는 모델 프레임워크입니다.')
        await websocket.close()