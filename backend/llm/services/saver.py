# backend/llm/services/saver.py

from backend.db.llm_db import save_llm_interaction

def save_interaction_and_build_response(
    model_name: str,
    user_input: str,
    stream_text: str,
    ko_translation: str,
    ja_translation: str,
    emotion: str,
    tone: str,
    blendshape: str,
    tool_call: dict | None
) -> dict:
    interaction_id = save_llm_interaction(
        model_name=model_name,
        request=user_input,
        response=stream_text.strip(),
        translate_response=ko_translation,
        ja_translate_response=ja_translation,
        emotion=emotion,
        tone=tone,
        blendshape=blendshape
    )

    return {
        "type": "interaction_id",
        "id": interaction_id,
        "translated": ko_translation,
        "ja_translated": ja_translation,
        "emotion": emotion,
        "tone": tone,
        "blendshape": blendshape,
        "toolCall": tool_call
    }
