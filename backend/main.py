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
from backend.asr.service import router as asr_router
from backend.asr.models import router as model_router
from backend.asr.routes.logs import router as logs_router
from backend.asr.routes.asr_status import router as asr_status_router
from backend.asr.routes.hardware_info import router as hardware_router
import backend.asr.socket_handlers

# 번역 백엔드 라이브러리
from backend.translate.api import router as translate_api_router
from backend.translate.service import router as translate_router
from backend.translate.routes.asr import router as fetching_asr_router

# LLM 백엔드 라이브러리
from backend.llm.service import router as llm_router

from backend.db.database import save_log_to_db

fastapi_app = FastAPI(title='Arielle AI Backend Server')

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

fastapi_app.mount("/static", StaticFiles(directory='backend/static'), name='static')

fastapi_app.include_router(asr_router, prefix='/asr', tags='ASR')
fastapi_app.include_router(logs_router, prefix='/asr', tags='Logs')
fastapi_app.include_router(asr_status_router, prefix='/api', tags='Status')
fastapi_app.include_router(hardware_router, prefix='/api', tags='Hardware')
fastapi_app.include_router(model_router, prefix='/api', tags='Model')
fastapi_app.include_router(translate_api_router, prefix='/api', tags='Translate')
fastapi_app.include_router(fetching_asr_router, prefix='/api', tags='ASR Fetch')
fastapi_app.include_router(translate_router, prefix='/translate', tags='Save Translate Result')
fastapi_app.include_router(llm_router, prefix='/llm', tags='LLM')

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