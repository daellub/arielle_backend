# backend/llm/routes/feedback_route.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from backend.llm.services.feedback_service import save_feedback_to_db

router = APIRouter()

class FeedbackRequest(BaseModel):
    interaction_id: int
    rating: Literal['up', 'down'] | None = None
    tone_score: float = Field(..., ge=0.0, le=1.0)

@router.post("/feedback")
async def save_feedback(req: FeedbackRequest):
    try:
        save_feedback_to_db(req.interaction_id, req.rating, req.tone_score)
        return {"message": "피드백 저장 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 저장 실패: {e}")
