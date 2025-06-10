# backend/llm/services/chat_handler.py

import pymysql
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import json
from urllib.parse import quote
import httpx

from backend.llm.services.prompt_builder import build_system_prompt
from backend.llm.services.context_manager import build_llm_context, append_local_sources
from backend.llm.services.tool_executor import (
    extract_math_expr, extract_weather_expr, extract_search_query,
    extract_spotify_query, extract_spotify_command, evaluate_math_expr
)
from backend.llm.services.responder import stream_llm_response
from backend.llm.services.translator import translate_to_ko_and_ja
from backend.llm.emotion.analyzer import analyze_emotion
from backend.llm.services.saver import save_interaction_and_build_response

from backend.db.llm_db import get_llm_model_by_id, get_connection

async def safe_ws_close(ws: WebSocket):
    try:
        await ws.close()
    except RuntimeError:
        pass

def get_tools_by_ids(tool_ids: list[int]):
    if not tool_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            q = f"SELECT id, name, type, command, enabled FROM mcp_tools WHERE id IN ({','.join(['%s'] * len(tool_ids))})"
            cursor.execute(q, tuple(tool_ids))
            return cursor.fetchall()
    finally:
        conn.close()

async def handle_chat(ws: WebSocket):
    await ws.accept()
    print("[WS] 연결 수립")

    try:
        while True:
            try:
                data = await ws.receive_json()
            except WebSocketDisconnect:
                print("[WS] 연결 종료")
                break

            try:
                model_id = data.get("model_id")
                if not model_id:
                    await ws.send_text("[ERROR] 모델 ID 없음")
                    await ws.close()
                    return

                model = get_llm_model_by_id(model_id)
                print("[DEBUG] model type:", type(model))
                print("[DEBUG] model:", model)
                
                if not model or not model["enabled"]:
                    await ws.send_text("[ERROR] 모델이 비활성화됨")
                    await ws.close()
                    return

                model_name = model["model_key"]
                endpoint = model["endpoint"]
                params = json.loads(model.get("params") or "{}")

                # 1. 프롬프트
                system_prompt = build_system_prompt(params)

                # 2. 옵션/메시지 추출
                sampling = params.get("sampling", {})
                memory = params.get("memory", {})
                opts = {
                    "max_tokens": memory.get("maxTokens", 96),
                    "temperature": sampling.get("temperature", 0.85),
                    "top_k": sampling.get("topK", 40),
                    "top_p": sampling.get("topP", 0.9),
                    "repeat_penalty": sampling.get("repetitionPenalty", 1.1),
                }
                msgs = data.get("messages", [])
                tool_ids = params.get("tools", [])
                tool_defs = get_tools_by_ids(tool_ids)

                # 3. 도구 감지
                user_text = msgs[-1]["content"]
                expr = extract_math_expr(user_text)
                weather_query = extract_weather_expr(user_text)
                search_query = extract_search_query(user_text)
                spotify_query = extract_spotify_query(user_text)
                spotify_cmd = extract_spotify_command(user_text)

                tool_result = None
                if expr:
                    tool = next((t for t in tool_defs if t["name"] == "calculate" and t["enabled"]), None)
                    if tool:
                        tool_result = evaluate_math_expr(expr)

                weather_result = None
                if weather_query:
                    tool = next((t for t in tool_defs if t["name"] == "fetch_weather" and t["enabled"]), None)
                    if tool:
                        try:
                            url = tool["command"].replace("{{expr}}", quote(weather_query))
                            async with httpx.AsyncClient() as client:
                                res = await client.get(url)
                                weather_result = res.text.strip()
                        except: pass

                search_result = None
                if search_query:
                    tool = next((t for t in tool_defs if t["name"] == "search" and t["enabled"]), None)
                    if tool:
                        try:
                            encoded = quote(search_query)
                            url = f"http://localhost:8500/mcp/api/tools/search?query={encoded}"
                            async with httpx.AsyncClient() as client:
                                res = await client.get(url)
                                data = res.json()
                                if "title" in data:
                                    search_result = f"{data['title']}: {data['summary']} ({data['link']})"
                        except: pass

                tool_call = None
                if spotify_query:
                    tool_call = {"integration": "spotify", "action": "play", "query": spotify_query}
                elif spotify_cmd:
                    tool_call = {"integration": "spotify", **spotify_cmd}

                # 4. context 빌드
                context = await build_llm_context(model_id, system_prompt, msgs, memory)

                if params.get("local_sources"):
                    append_local_sources(context, params["local_sources"])

                if tool_result:
                    context.append({"role": "system", "content": f"The result of '{expr}' is {tool_result}."})
                if weather_result:
                    context.append({"role": "system", "content": f"The weather in {weather_query} is: {weather_result}."})
                if search_result:
                    context.append({"role": "system", "content": f"Here is the result for '{search_query}': {search_result}."})

                # 5. LLM 호출
                payload = { "model": model_name, "messages": context, "stream": True, **opts }
                stream_text = await stream_llm_response(ws, payload, endpoint)

                # 6. 번역 & 감정
                ko, ja = await translate_to_ko_and_ja(stream_text)

                try:
                    print("[DEBUG] 감정 분석 진입함")
                    emo = await analyze_emotion(stream_text)
                    print("[DEBUG] 감정 분석 종료")
                    emotion = emo.get("emotion", "neutral")
                    tone = emo.get("tone", "neutral")
                    blendshape = emo.get("blendshape", "Neutral")
                except Exception as e:
                    print("❌ 감정 분석 예외 발생:", e)
                    emotion, tone = "neutral", "neutral"

                # 7. 저장 및 응답
                result = save_interaction_and_build_response(
                    model_name=model_name,
                    user_input=user_text,
                    stream_text=stream_text,
                    ko_translation=ko,
                    ja_translation=ja,
                    emotion=emotion,
                    tone=tone,
                    blendshape=blendshape,
                    tool_call=tool_call
                )

                await ws.send_json(result)

            except Exception as e:
                print(f"[ERROR] 메시지 처리 중 오류: {e}")
                try:
                    await ws.send_text(f"[ERROR] 처리 실패: {e}")
                except RuntimeError:
                    pass  # 이미 닫힌 경우 무시
                await safe_ws_close(ws)
                return

    except WebSocketDisconnect:
        print("[WS] 클라이언트 연결 종료")
    except Exception as e:
        print(f"[WS] 처리 중 예외: {e}")
        await safe_ws_close(ws)
