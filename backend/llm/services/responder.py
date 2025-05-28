# backend/llm/services/responder.py

import json
import httpx
from fastapi import WebSocket

async def stream_llm_response(ws: WebSocket, payload: dict, endpoint: str) -> str:
    stream_text = ""

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{endpoint}/v1/chat/completions", json=payload) as res:
                async for line in res.aiter_lines():
                    if line.startswith("data: "):
                        content = line.removeprefix("data: ").strip()
                        if content == "[DONE]":
                            await ws.send_text("[DONE]")
                            break
                        try:
                            chunk = json.loads(content)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            stream_text += delta
                            await ws.send_text(delta)
                        except Exception as e:
                            print(f"[ERROR] JSON decode 실패: {e}")
                            await ws.send_text("[ERROR] 스트리밍 처리 중 예외 발생")
                            continue
    except Exception as e:
        print(f"[STREAM ERROR] 스트리밍 중 예외: {e}")
        await ws.send_text(f"[ERROR] 스트리밍 중 예외 발생: {e}")
        await ws.close()
        raise

    return stream_text
