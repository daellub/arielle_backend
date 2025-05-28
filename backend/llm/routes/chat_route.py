# backend/llm/routes/chat_route.py

from fastapi import APIRouter, WebSocket
from backend.llm.services.chat_handler import handle_chat

router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await handle_chat(ws)
