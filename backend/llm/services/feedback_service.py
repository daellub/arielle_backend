# backend/llm/services/feedback_service.py

from backend.db.llm_db import save_llm_feedback

def save_feedback_to_db(interaction_id: int, rating: str | None, tone_score: float):
    save_llm_feedback(interaction_id, rating, tone_score)
