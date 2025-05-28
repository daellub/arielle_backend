# backend/llm/services/emotion_analyzer.py

import re
from typing import Dict
import httpx
from backend.llm.emotion.prompt import PROMPT_TEMPLATE

LLAMA_ENDPOINT = "http://172.27.112.1:8081/v1/completions"
ALLOWED_EMOTIONS = {
    "joyful", "hopeful", "melancholic", "romantic", "peaceful", "nervous",
    "regretful", "admiring", "tense", "nostalgic", "whimsical", "sarcastic",
    "bitter", "apologetic", "affectionate", "solemn", "cheerful",
    "embarrassed", "contemplative"
}

def extract_emotion_json(text: str) -> Dict[str, str]:
    match = re.search(r'{\\s*"emotion"\\s*:\\s*"(.*?)"\\s*,\\s*"tone"\\s*:\\s*"(.*?)"\\s*}', text)
    if not match:
        raise ValueError(f"응답 파싱 실패: {text}")
    emotion, tone = match.group(1), match.group(2)
    if emotion not in ALLOWED_EMOTIONS:
        emotion = "neutral"
    return {"emotion": emotion, "tone": tone}

async def analyze_emotion(text: str) -> Dict[str, str]:
    prompt = PROMPT_TEMPLATE.format(text=text)
    payload = {
        "model": "emotion-analyzer",
        "prompt": prompt,
        "temperature": 0.2,
        "max_tokens": 64,
        "stream": False
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            res = await client.post(LLAMA_ENDPOINT, json=payload)
            res.raise_for_status()
            content = res.json()["choices"][0]["text"].strip()
            return extract_emotion_json(content)
        except Exception as e:
            raise ValueError(f"감정 분석 요청 실패: {e}")
