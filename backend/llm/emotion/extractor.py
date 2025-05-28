# backend/llm/emotion/extractor.py
import re
from typing import Dict

ALLOWED_EMOTIONS = {
    "joyful", "hopeful", "melancholic", "romantic", "peaceful", "nervous",
    "regretful", "admiring", "tense", "nostalgic", "whimsical", "sarcastic",
    "bitter", "apologetic", "affectionate", "solemn", "cheerful",
    "embarrassed", "contemplative"
}

def extract_emotion_json(text: str) -> Dict[str, str]:
    match = re.search(r'{\\s*\"emotion\"\\s*:\\s*\"(.*?)\"\\s*,\\s*\"tone\"\\s*:\\s*\"(.*?)\"\\s*}', text)
    if not match:
        raise ValueError(f"응답 파싱 실패: {text}")

    emotion, tone = match.group(1), match.group(2)
    if emotion not in ALLOWED_EMOTIONS:
        emotion = "neutral"

    return {"emotion": emotion, "tone": tone}
