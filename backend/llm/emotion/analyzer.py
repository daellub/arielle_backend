# backend/llm/emotion/analyzer.py
import httpx
from typing import Dict
from backend.llm.emotion.generator import generate_prompt
from backend.llm.emotion.extractor import extract_emotion_json

LLAMA_ENDPOINT = "http://172.27.112.1:8081/v1/completions"

async def analyze_emotion(text: str) -> Dict[str, str]:
    prompt = generate_prompt(text)
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
        except httpx.RequestError as e:
            raise ValueError(f"Request failed: {e}")
        except httpx.TimeoutException:
            raise ValueError("The request timed out after 60 seconds.")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error occurred: {e.response.status_code}")

    return extract_emotion_json(content)
