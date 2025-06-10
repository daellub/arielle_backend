# backend/vrm/routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter()

connected_clients: List[WebSocket] = []

@router.websocket("/expressions")
async def expression_websocket(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print("[VRM WS] 연결됨")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[VRM WS] 수신 데이터: {data}")

            for client in connected_clients:
                if client != websocket:
                    await client.send_text(data)

    except WebSocketDisconnect:
        print("[VRM WS] 연결 종료됨")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
