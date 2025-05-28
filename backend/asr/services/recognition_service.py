# # backend/asr/services/recognition_service.py

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from backend.asr.managers.model_manager import model_manager
from backend.db.asr_db import save_log_to_db, delete_model_from_db, get_models_from_db

def register_model(model):
    return model_manager.register(model)

def load_model(model_id):
    model_manager.load_model(model_id)
    info = model_manager.models[model_id]['info']
    save_log_to_db("INFO", f'Model {info.name} loaded (device={info.device})', "MODEL")
    return info

def unload_model(model_id):
    ok = model_manager.unload_model(model_id)
    if ok:
        info = model_manager.models[model_id]['info']
        save_log_to_db("INFO", f'Model {info.name} unloaded', "MODEL")
    return ok

def delete_model(model_id):
    if model_id in model_manager.models:
        del model_manager.models[model_id]
    delete_model_from_db(model_id)

def list_models():
    models = get_models_from_db()
    for m in models:
        m['logo'] = m.get('logo', '/static/icons/default.svg')
    return models

async def handle_websocket_inference(websocket: WebSocket, model_id: str):
    await websocket.accept()

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
        await websocket.send_text("🎙 Azure 모델은 프론트엔드에서 처리됩니다.")
        await websocket.close()
        return
    else:
        await websocket.send_text('error: 지원하지 않는 모델 프레임워크입니다.')
        await websocket.close()
