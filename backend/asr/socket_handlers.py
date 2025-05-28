# backend/asr/socket_handlers.py

import asyncio
import numpy as np

from backend.sio import sio
from backend.db.asr_db import save_log_to_db
from backend.asr.managers.model_manager import model_manager

# sid 별 SpeechRecognizer 및 done_future 저장
recognizers = {}

# Whisper / HuggingFace용 로컬 모델 처리 메커니즘
@sio.on('start_transcribe')
async def start_transcribe(sid, data):
    print(f"[DEBUG] ▶ start_transcribe called: sid={sid}, data={data}")
    model_id = data.get("model_id")

    if model_id not in model_manager.models:
        return await sio.emit('transcript', {'text': '❌ 모델을 찾을 수 없습니다.'}, room=sid)
    
    model = model_manager.models[model_id]["instance"]
    if model is None:
        await sio.emit('transcript', {'text': '❌ 모델이 로드되지 않았습니다.'}, to=sid)
        return
    
    await sio.save_session(sid, {'model_id': model_id})

    await sio.emit('transcript', {'text': '🎙 전사 준비 완료'}, to=sid)

@sio.on('audio_chunk')
async def audio_chunk(sid, data):
    session = await sio.get_session(sid)
    model_id = session.get("model_id")

    if not model_id or model_id not in model_manager.models:
        await sio.emit('transcript', {'text': '⚠️ 유효하지 않은 모델입니다.'},  to=sid)
        return
    
    try:
        audio_np = np.array(data, dtype=np.float32)

        texts = model_manager.infer(model_id, audio_np, language="<|ko|>")
        # print("[DEBUG] 전사 결과: ", texts)
        if texts:
            await sio.emit('transcript', {'text': texts[0]}, to=sid)
    except Exception as e:
        # print(f"[ERROR] audio_chunk 처리 중 오류: {e}")
        await sio.emit('transcript', {'text': '❌ 전사 실패'}, to=sid)

@sio.on('stop_transcribe')
async def stop_transcribe(sid):
    print(f'[SOCKET] stop_transcribe 요청 받음 from {sid}')