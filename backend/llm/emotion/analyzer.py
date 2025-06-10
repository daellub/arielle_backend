# backend/llm/emotion/analyzer.py
import httpx
from typing import Dict
from backend.llm.emotion.generator import generate_prompt
from backend.llm.emotion.extractor import extract_emotion_json

# 📌 실제 llama.cpp 서버가 실행 중인 IP로 고정
LLAMA_ENDPOINT = "http://host.docker.internal:8081/v1/completions"

async def analyze_emotion(text: str) -> Dict[str, str]:
    try:
        prompt = generate_prompt(text)
        # print("✅ generate_prompt 성공:", prompt)
    except Exception as e:
        # print("❌ generate_prompt 실패:", e)
        raise
    payload = {
        "model": "emotion-analyzer",
        "prompt": prompt,
        "temperature": 0.2,
        "max_tokens": 64,
        "stream": False
    }

    # print("\n[🧠 감정 분석 시작]")
    # print("📨 입력 텍스트:", text)
    # print("📤 전송 프롬프트:\n", prompt)
    # print("📦 Payload:", payload)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(LLAMA_ENDPOINT, json=payload)
            res.raise_for_status()
            content = res.json()["choices"][0]["text"].strip()
            print("📥 LLM 응답 원문:\n", content)
    except httpx.RequestError as e:
        print("❌ RequestError:", e)
        raise ValueError(f"Request failed: {e}")
    except httpx.TimeoutException:
        print("❌ TimeoutException")
        raise ValueError("The request timed out after 60 seconds.")
    except httpx.HTTPStatusError as e:
        print("❌ HTTPStatusError:", e.response.status_code)
        raise ValueError(f"HTTP error occurred: {e.response.status_code}")

    try:
        parsed = extract_emotion_json(content)
        print("✅ 파싱된 결과:", parsed)
        return parsed
    except Exception as e:
        print("❌ 파싱 실패:", e)
        print("❓ 원문 응답 다시 출력:", repr(content))
        raise ValueError(f"감정 분석 응답 파싱 실패: {e}")
