# backend/asr/socket_handlers.py

import asyncio
import azure.cognitiveservices.speech as speechsdk
import numpy as np

from backend.sio import sio
from backend.db.database import save_log_to_db
from backend.asr.model_manager import model_manager
from backend.utils.encryption import decrypt
from backend.utils.device_resolver import resolve_input_device_id

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

# Azure API용 모델 메커니즘
@sio.on('start_azure_mic')
async def start_azure_mic(sid, data):
    save_log_to_db("PROCESS", "Mic started capturing audio", "MIC")
    # print(f'[SOCKET] start_azure_mic 요청 받음 from {sid}')

    # 이전 세션 삭제
    if sid in recognizers:
        # print(f"[INFO] 이전 recognizer 세션 삭제: {sid}")
        recognizer = recognizers[sid]['recognizer']
        recognizer.stop_continuous_recognition()
        del recognizers[sid]

    model_id = data.get('model_id')
    device_label = data.get('deviceLabel')

    if not model_id or model_id not in model_manager.models:
        await sio.emit('transcript', {'text': '❌ 모델을 찾을 수 없습니다.'}, to=sid)
        return

    entry = model_manager.models[model_id]
    instance = entry["instance"]
    info = entry["info"]
    framework = info.framework.lower()

    if instance is None and framework != 'azure':
        return await sio.emit('transcript', {'text': '❌ 모델이 로드되지 않아 사용할 수 없습니다.'}, to=sid)
    
    if not getattr(info, '_decrypted', False):
        info.apiKey = decrypt(info.apiKey)
        setattr(info, '_decrypted', True)

    await recognized_from_microphone(sid, info, device_label=device_label)

async def recognized_from_microphone(sid: str, model_info, device_label=None):
    save_log_to_db("PROCESS", "Audio stream started", "MIC")

    if sid in recognizers:
        del recognizers[sid]
    
    apiKey = model_info.apiKey
    endpoint = model_info.endpoint
    region = model_info.region

    if not apiKey:
        raise ValueError('❌ API Key가 없습니다.')
    
    if endpoint:
        speech_config = speechsdk.SpeechConfig(subscription=apiKey, endpoint=endpoint)
    elif region:
        speech_config = speechsdk.SpeechConfig(subscription=apiKey, region=region)
    else:
        raise ValueError("❌ 엔드포인트와 리전이 모두 없습니다.")
    
    speech_config.speech_recognition_language = 'ko-KR'

    if device_label and device_label != 'default':
        device_id = resolve_input_device_id(device_label)
        if device_id:
            print(f'[INFO] 선택된 장치 ID: {device_id}')
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=False, device_name=device_id)
        else:
            save_log_to_db("ERROR", "No input device detected", "MIC")
            print(f'[WARN] 지정된 장치를 찾을 수 없어 기본 마이크를 사용합니다.')
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    else:
        print(f'[INFO] 기본 마이크 사용')
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    loop = asyncio.get_running_loop()
    done_future = loop.create_future()

    recognizers[sid] = { 
        'recognizer': speech_recognizer,
        'done_future': done_future,    
    }

    def recognizing_cb(evt):
        text = evt.result.text
        if text:
            
            asyncio.run_coroutine_threadsafe(
                sio.emit('recognizing', {'text': text}, to=sid),
                loop
            )
    
    def recognized_cb(evt):
        text = evt.result.text
        if text:
            save_log_to_db("RESULT", "Azure Audio Transcribe Successful.", "MODEL")
            asyncio.run_coroutine_threadsafe(
                sio.emit('recognized', {'text': text}, to=sid),
                loop
            )
        else:
            save_log_to_db("ERROR", "Transcription failed: No Match", "MODEL")

    def session_stopped_cb(evt):
        if not done_future.done():
            loop.call_soon_threadsafe(done_future.set_result, True)

    def canceled_cb(evt):
        save_log_to_db("ERROR", "Transcription canceled", "MODEL")
        if not done_future.done():
            loop.call_soon_threadsafe(done_future.set_result, True)
    
    save_log_to_db("PROCESS", "Azure transcription started", "MODEL")

    speech_recognizer.recognizing.connect(recognizing_cb)
    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_stopped.connect(session_stopped_cb)
    speech_recognizer.canceled.connect(canceled_cb)

    await sio.emit('transcript', {'text': '🎙 Azure 스트리밍 준비 완료'}, to=sid)

    speech_recognizer.start_continuous_recognition()
    await done_future
    save_log_to_db("PROCESS", "Audio stream stopped after silence", "MIC")
    speech_recognizer.stop_continuous_recognition()
    await sio.emit('transcript', {'text': '🎙 Azure 스트리밍 종료'}, to=sid)

    if sid in recognizers:
        del recognizers[sid]

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

# Azure 전사 중단
@sio.on('stop_azure_mic')
async def stop_azure_mic(sid, data):
    entry = recognizers.get(sid)
    if entry:
        recognizer = entry['recognizer']
        done_future = entry['done_future']

        if not done_future.done():
            done_future.set_result(True)
            #print(f"[INFO] SpeechRecognizer 중지 완료 for {sid}")
        else:
            print(f"[INFO] 이미 done 상태 for {sid}")

        recognizer.stop_continuous_recognition()
        del recognizers[sid]
    else:
        print(f"[WARN] stop_azure_mic: recognizer 없음 for {sid}")