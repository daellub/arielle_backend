# backend/llm/emotion/extractor.py
import json
from typing import Dict

ALLOWED_EMOTIONS = {
    "joyful", "hopeful", "melancholic", "romantic", "peaceful", "nervous",
    "regretful", "admiring", "tense", "nostalgic", "whimsical", "sarcastic",
    "bitter", "apologetic", "affectionate", "solemn", "cheerful",
    "embarrassed", "contemplative"
}

def extract_emotion_json(text: str) -> Dict[str, str]:
    print("🧪 파싱 대상 텍스트:", repr(text))
    
    try:
        data = json.loads(text)
        emotion = data.get("emotion", "neutral")
        tone = data.get("tone", "neutral")
        blendshape = data.get("blendshape", "Neutral")

        if emotion not in ALLOWED_EMOTIONS:
            emotion = "neutral"

        return {
            "emotion": emotion,
            "tone": tone,
            "blendshape": blendshape
        }
    except Exception as e:
        raise ValueError(f"응답 파싱 실패: {text} ({e})")
