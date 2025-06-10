# backend/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import socketio

from backend.sio import sio

# ASR 백엔드 라이브러리
from backend.asr.routes.service_route import router as asr_router
from backend.asr.routes.log_route import router as logs_router
from backend.asr.routes.status_route import router as status_router
from backend.asr.routes.hardware_route import router as hardware_router
from backend.asr.routes.hf_download_route import router as hf_model_router

# 번역 백엔드 라이브러리
from backend.translate.routes.translate_route import router as translate_router
from backend.translate.routes.save_route import router as save_translate_router
from backend.translate.routes.asr_llm_route import router as asr_llm_translate_router

# LLM 백엔드 라이브러리
from backend.llm.routes.chat_route import router as chat_router
from backend.llm.routes.feedback_route import router as feedback_router

# TTS 백엔드 라이브러리
from backend.tts.routes import router as tts_router

# VRM 백엔드 라이브러리
from backend.vrm.routes import router as vrm_router

from backend.db.asr_db import save_log_to_db

fastapi_app = FastAPI(title='Arielle AI Backend Server')

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

fastapi_app.mount("/static", StaticFiles(directory='backend/static'), name='static')

# ASR
fastapi_app.include_router(asr_router, prefix='/asr', tags=['ASR'])
fastapi_app.include_router(logs_router, prefix='/asr', tags=['Logs'])
fastapi_app.include_router(status_router, prefix='/api', tags=['Status'])
fastapi_app.include_router(hardware_router, prefix='/api', tags=['Hardware'])
fastapi_app.include_router(hf_model_router, prefix='/api', tags=['Model'])

# Translate
fastapi_app.include_router(translate_router, prefix='/api', tags=['Translate'])
fastapi_app.include_router(save_translate_router, prefix='/translate', tags=['Translate Save'])
fastapi_app.include_router(asr_llm_translate_router, prefix='/api', tags=['Translate Latest'])

# LLM
fastapi_app.include_router(chat_router, prefix='/llm', tags=['LLM Chat'])
fastapi_app.include_router(feedback_router, prefix='/llm', tags=['LLM Feedback'])

# TTS
fastapi_app.include_router(tts_router, prefix='/tts', tags='TTS')

# VRM
fastapi_app.include_router(vrm_router, prefix='/vrm', tags='VRM')

app = socketio.ASGIApp(
    socketio_server=sio, 
    other_asgi_app=fastapi_app,
    socketio_path="/socket.io"    
)

@sio.event
async def connect(sid, environ):
    print(f"[SOCKET.IO] 클라이언트 연결됨: {sid}")
    save_log_to_db("INFO", f"Socket connected: sid={sid}", "FRONTEND")

@sio.event
async def disconnect(sid):
    print(f"[SOCKET.IO] 클라이언트 연결 해제됨: {sid}")
    save_log_to_db("INFO", f"Socket disconnected: sid={sid}", "FRONTEND")

@fastapi_app.get("/")
def root():
    return {"message": "Arielle Backend Running!"}

@fastapi_app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    save_log_to_db(
        log_type='ERROR',
        message=f'Unhandled Exception: {str(exc)}',
        source='SYSTEM'
    )
    return JSONResponse(
        status_code=500,
        content={'detail': '서버 내부 오류가 발생했습니다.'}
    )

@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    save_log_to_db(
        log_type='ERROR',
        message=f'Validation error: {exc.errors()}',
        source='SYSTEM'
    )
    return JSONResponse(
        status_code=422,
        content={'detail': exc.errors()}
    )