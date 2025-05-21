# backend/llm/service.py

import os
import requests
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Literal

import httpx
import json
from pathlib import Path
import re
import ast

from backend.db.database import save_llm_interaction, save_llm_feedback
from backend.llm.emotion.service import analyze_emotion

router = APIRouter()

def load_system_prompt() -> str:
    return Path("backend/llm/prompt/arielle_prompt.txt").read_text(encoding="utf-8")

def clean_text(text: str) -> str:
    return re.sub(r'\*.*?\*', '', text).strip()

def is_safe_math_expr(expr: str) -> bool:
    try:
        parsed = ast.parse(expr, mode='eval')
        allowed = (
            ast.Expression, ast.BinOp, ast.UnaryOp,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
            ast.Num, ast.Constant, ast.UAdd, ast.USub, ast.Load,
            ast.Expr, ast.Call, ast.Name
        )
        for node in ast.walk(parsed):
            if not isinstance(node, allowed):
                print(f"[⛔️ BLOCKED NODE] {type(node).__name__}")
                return False
        return True
    except Exception as e:
        print(f"[⛔️ PARSE ERROR]: {e}")
        return False
    
def evaluate_math_expr(expr: str) -> str:
    try:
        print(f"[DEBUG] 수식 평가: {expr}")

        if not is_safe_math_expr(expr):
            raise ValueError("안전하지 않은 수식이 감지되었습니다.")
        
        result = str(eval(expr))
        print(f"[✅ 계산 성공] 결과: {result}")
        return result
    except Exception as e:
        print(f"[❌ 계산 실패] {expr} -> {e}")
        return f"Error: {e}"
    
def extract_weather_expr(text: str) -> str | None:
    match = re.search(r'\b(?:weather|forecast)\s+(?:in\s+)?([A-Za-z\s]+)', text, re.IGNORECASE)
    if match:
        location = match.group(1).strip()
        print(f"[🌤️ 감지된 날씨 위치]: {location}")
        return location
    return None

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    max_tokens: int = Field(96, ge=1, le=1024)
    temperature: float = Field(0.85, ge=0.0, le=2.0)
    top_k: int = Field(40, ge=0)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    repeat_penalty: float = Field(1.1, ge=1.0, le=2.0)

# @router.post("/chat")
# async def chat(req: ChatRequest):
#     user_messages = [
#         {"role": m.role, "content": m.content}
#         for m in req.messages
#     ]
    
#     payload = {
#         "model": "arielle-q6",
#         "messages": [
#             {"role": "system", "content": load_system_prompt()}
#         ] + user_messages,
#         "max_tokens": req.max_tokens,
#         "temperature": req.temperature,
#         "top_k": req.top_k,
#         "top_p": req.top_p,
#         "repeat_penalty": req.repeat_penalty,
#         "stop": ["User:"],
#         "stream": False
#     }

#     try:
#         res = requests.post("http://localhost:8080/v1/chat/completions", json=payload)
#         res.raise_for_status()
#         data = res.json()
#         content = data["choices"][0]["message"]["content"]
#         return {"content": clean_text(content)}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"LLM 서버 요청 실패: {e}")

@router.websocket('/ws/chat')
async def websocket_chat(ws: WebSocket):
    from backend.db.database import get_connection, get_llm_model_by_id, get_prompt_templates_by_ids
    from backend.utils.prompt_utils import apply_variables
    from backend.llm.memory.context_builder import build_context
    import re
    from datetime import datetime
    from urllib.parse import quote

    def extract_variables(template: str) -> list[str]:
        return re.findall(r"\{([\w_]+)\}", template)
    
    def resolve_variables(vars: list[str]) -> dict:
        now = datetime.now()
        return {
            var: (
                now.strftime("%H:%M") if var == "time" else
                now.strftime("%Y-%m-%d") if var == "date" else
                "Dael" if var == "user_name" else f"<{var}>"
            ) for var in vars
        }
    
    def get_tools_by_ids(tool_ids: list[int]):
        if not tool_ids:
            return []
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                q = f"SELECT id, name, type, command, enabled FROM mcp_tools WHERE id IN ({','.join(['%s'] * len(tool_ids))})"
                cursor.execute(q, tuple(tool_ids))
                return [
                    {"id": r[0], "name": r[1], "type": r[2], "command": r[3], "enabled": r[4]}
                    for r in cursor.fetchall()
                ]
        finally:
            conn.close()

    def extract_math_expr(text: str) -> str | None:
        lowered = text.lower()

        if 'spotify' in lowered or 'play' in lowered or 'music' in lowered:
            return None
        
        matches = re.findall(r'[\(]?[0-9\.\s\+\-\*/\^()]+[\)]?', text)
        
        for expr in matches:
            cleaned = expr.strip().replace("^", "**")
            if ' - ' in cleaned:
                continue
            if any(op in cleaned for op in ['+', '-', '*', '/', '**']):
                print(f"[🧠 감지된 수식]: {cleaned}")
                return cleaned
        
        return None
    
    def extract_search_query(text: str) -> str | None:
        match = re.search(r'\b(?:search|find|look\s+up)\s+(.+)', text, re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            print(f"[🔍 감지된 검색어]: {query}")
            return query
        return None
    
    def extract_spotify_query(text: str) -> str | None:
        match = re.search(r'\bplay\s+(.+?)\s+(?:on|with)\s+spotify\b', text, re.IGNORECASE)
        if match:
            song = match.group(1).strip()
            print(f"[🎵 Spotify 요청 감지]: {song}")
            return song
        return None
    
    def extract_spotify_command(text: str) -> dict | None:
        text = text.lower()

        if re.search(r'\b(pause|stop)\b.*(music|song)?', text):
            return {"action": "pause"}
        if re.search(r'\b(resume|continue)\b.*(music|song)?', text):
            return {"action": "play"}
        if re.search(r'\b(skip|next)\b.*(track|song|music)?', text):
            return {"action": "next"}
        if re.search(r'\b(previous|back)\b.*(track|song)?', text):
            return {"action": "previous"}
        if re.search(r'\b(volume\s+up|turn\s+up\s+the\s+volume|increase\s+volume)\b', text):
            return {"action": "volume_up"}
        if re.search(r'\b(volume\s+down|turn\s+down\s+the\s+volume|decrease\s+volume)\b', text):
            return {"action": "volume_down"}
        
        return None

    await ws.accept()

    try:
        while True:
            data = await ws.receive_json()

            model_id = data.get("model_id")
            if model_id is None:
                await ws.send_text("[NOTICE] 모델 ID가 없습니다! 웹소켓을 다시 연결해 주세요!")
                await ws.close()
                return
            
            model = get_llm_model_by_id(model_id)
            if not model or not model["enabled"]:
                await ws.send_text("[NOTICE] 사용 불가능한 모델입니다! 웹소켓을 다시 연결해 주세요!")
                await ws.close()
                return
            
            model_name = model["model_key"]
            endpoint = model["endpoint"]

            try:
                params = json.loads(model.get("params") or "{}")
            except Exception as e:
                await ws.send("[NOTICE] 모델 파라미터 디코딩에 실패했습니다! 웹소켓을 다시 연결해 주세요!")
                print(f"[ERROR] 모델 파라미터 JSON 디코드 실패: {e}")
                await ws.close()
                return
            
            # 프롬프트
            prompt_ids = params.get("prompts", [])
            manual_prompt = params.get("prompt", "").strip()
            template_prompts = get_prompt_templates_by_ids(prompt_ids)

            if manual_prompt:
                system_prompt = manual_prompt
            elif template_prompts:
                system_prompt = "\n\n".join(template_prompts)
            else:
                system_prompt = load_system_prompt()

            # 프롬프트 변수 처리
            vars = extract_variables(system_prompt)
            system_prompt = apply_variables(system_prompt, vars, resolve_variables(vars))
            
            # Sampling & Memory
            sampling = params.get("sampling", {})
            memory = params.get("memory", {})

            opts = {
                "max_tokens": memory.get("maxTokens", 96),
                "temperature": sampling.get("temperature", 0.85),
                "top_k": sampling.get("topK", 40),
                "top_p": sampling.get("topP", 0.9),
                "repeat_penalty": sampling.get("repetitionPenalty", 1.1),
            }
            
            msgs = data.get('messages', [])

            tool_ids = params.get("tools", [])
            tool_defs = get_tools_by_ids(tool_ids)

            print(f"[🧰 tool_defs 목록]: {tool_defs}")

            weather_query = extract_weather_expr(msgs[-1]["content"])
            weather_result = None

            if weather_query:
                weather_tool = next((t for t in tool_defs if t["name"] == "fetch_weather" and t["enabled"]), None)
                if weather_tool:
                    try:
                        url = weather_tool["command"].replace("{{expr}}", quote(weather_query))
                        print(f"[🌤️ fetch_weather 실행 URL]: {url}")
                        async with httpx.AsyncClient() as client:
                            res = await client.get(url)
                            weather_result = res.text.strip()
                        print(f"[🌤️ 날씨 결과]: {weather_result}")
                    except Exception as e:
                        print(f"[❌ fetch_weather 실행 실패]: {e}")

            search_query = extract_search_query(msgs[-1]["content"])
            search_result = None

            if search_query:
                search_tool = next((t for t in tool_defs if t["name"] == "search" and t["enabled"]), None)
                if search_tool:
                    try:
                        encoded = quote(search_query)
                        url = f"http://localhost:8500/mcp/api/tools/search?query={encoded}"
                        print(f"[🔍 search 실행 URL]: {url}")
                        async with httpx.AsyncClient() as client:
                            res = await client.get(url)
                            data = res.json()
                            if "title" in data:
                                search_result = f"{data['title']}: {data['summary']} ({data['link']})"
                                print(f"[🔍 검색 결과]: {search_result}")
                    except Exception as e:
                        print(f"[❌ search 실행 실패]: {e}")

            spotify_query = extract_spotify_query(msgs[-1]["content"])
            spotify_cmd = extract_spotify_command(msgs[-1]["content"])

            tool_call = None

            if spotify_query:
                tool_call = {
                    "integration": "spotify",
                    "action": "play",
                    "query": spotify_query
                }
            elif spotify_cmd:
                tool_call = {
                    "integration": "spotify",
                    **spotify_cmd
                }

            expr = extract_math_expr(msgs[-1]["content"])
            tool_result = None

            if expr:
                print(f"[🧪 수식 감지됨]: {expr}")
                calc_tool = next((t for t in tool_defs if t["name"] == "calculate" and t["enabled"]), None)
                if calc_tool:
                    print(f"[🧪 calculate 도구 사용] {calc_tool}")
                    tool_result = evaluate_math_expr(expr)
                else:
                    print("[⚠️ calculate 도구가 등록되어 있지 않음]")

            context = await build_context(
                model_id=model_id,
                system_prompt=system_prompt,
                user_messages=msgs,
                memory_settings=memory
            )

            local_source_ids = params.get("local_sources", [])
            if local_source_ids:
                from backend.utils.source_loader import load_text_from_local_sources
                texts = load_text_from_local_sources(local_source_ids)

                print(f"[📁 로컬 소스 ID 목록]: {local_source_ids}")
                print(f"[📁 로컬 소스 참고 문서 수]: {len(texts)}개")

                for idx, text in enumerate(texts):
                    header = text.split('\n')[0] if '\n' in text else text[:50]
                    print(f"[📄 문서 {idx+1}] 헤더: {header}")

                for text in texts:
                    role_intro = "This is character information:" if " is a " in text else "This is background knowledge:"
                    context.append({
                        "role": "system",
                        "content": f"{role_intro}\n{text[:500]}"
                    })

            if tool_result:
                print(f"[🧪 LLM 전달용 결과] '{expr}' = {tool_result}")
                context.append({
                    "role": "system",
                    "content": f"The result of '{expr}' is {tool_result}. Include this result in your reply."
                })

            if weather_result:
                context.append({
                    "role": "system",
                    "content": f"The weather in {weather_query} is: {weather_result}. Please include this in your response if relevant."
                })

            if search_result:
                context.append({
                    "role": "system",
                    "content": f"Here is the result for '{search_query}': {search_result}. Include this in your reply if helpful."
                })

            stream_text = ""
            payload = {
                "model": model_name,
                "messages": context,
                "stream": True,
                **opts
            }

            if os.getenv("DEBUG_LLM_PAYLOAD") == "1":
                print(f"[▶️ 요청 payload]\n{json.dumps(payload, indent=2)}")

            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", f"{endpoint}/v1/chat/completions", json=payload) as res:
                    async for line in res.aiter_lines():
                        if line.startswith("data: "):
                            content = line.removeprefix("data: ")
                            if content.strip() == "[DONE]":
                                await ws.send_text("[DONE]")
                                break
                            try:
                                chunk = json.loads(content)
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                stream_text += delta
                                await ws.send_text(delta)
                            except Exception as e:
                                print(f"[ERROR] JSON decode 실패: {e}")
                                continue
            
            # 번역 및 감정 분석
            try:
                async with httpx.AsyncClient() as client:
                    ko_res = await client.post("http://localhost:8000/api/translate", json={
                        "text": stream_text,
                        "from_lang": "en",
                        "to": "ko"
                    })
                    ko_translation = ko_res.json().get("translated", "")

                    ja_res = await client.post("http://localhost:8000/api/translate", json={
                        "text": stream_text,
                        "from_lang": "en",
                        "to": "ja"
                    })
                    ja_translation = ja_res.json().get("translated", "")

                try:
                    emo_data = await analyze_emotion(stream_text)
                    emotion = emo_data.get("emotion", "neutral")
                    tone = emo_data.get("tone", "neutral")
                except Exception as e:
                    print(f"[ERROR] 감정 분석 실패: {e}")
                    emotion = "neutral"
                    tone = "neutral"

                interaction_id = save_llm_interaction(
                    model_name=model_name,
                    request=msgs[-1]["content"],
                    response=stream_text.strip(),
                    translate_response=ko_translation,
                    ja_translate_response=ja_translation,
                    emotion=emotion,
                    tone=tone
                )

                # print("[✅ WebSocket 번역 결과]", {
                #     "id": interaction_id,
                #     "ko": ko_translation,
                #     "ja": ja_translation
                # })
                await ws.send_json({
                    "type": "interaction_id",
                    "id": interaction_id,
                    "translated": ko_translation,
                    "ja_translated": ja_translation,
                    "emotion": emotion,
                    "tone": tone,
                    "toolCall": tool_call
                })
            except Exception as e:
                print(f"[ERROR] 번역 또는 DB 저장 실패: {e}")
        
    except WebSocketDisconnect:
        print("[WS] 클라이언트 연결 종료")
    except Exception as e:
        print(f"[WS ERROR]: {e}")
        await ws.close()

class FeedbackRequest(BaseModel):
    interaction_id: int
    rating: Literal['up', 'down'] | None = None
    tone_score: float = Field(..., ge=0.0, le=1.0)

@router.post("/feedback")
async def save_feedback(req: FeedbackRequest):
    try:
        save_llm_feedback(
            interaction_id=req.interaction_id,
            rating=req.rating,
            tone_score=req.tone_score
        )
        return {"message": "피드백 저장 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 저장 실패: {e}")