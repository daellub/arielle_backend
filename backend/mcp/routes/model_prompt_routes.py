# backend/mcp/routes/model_prompt_routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from backend.db.database import get_connection

router = APIRouter(prefix="/llm/model")

class PromptLink(BaseModel):
    prompt_ids: List[int]

@router.get("/{model_id}/prompts")
async def get_model_prompts(model_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT prompt_id FROM llm_model_prompts WHERE model_id = %s", (model_id,))
            rows = cursor.fetchall()
            return {"prompt_ids": [row[0] for row in rows]}
    finally:
        conn.close()

@router.patch("/{model_id}/prompts")
async def update_model_prompts(model_id: int, payload: PromptLink):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM llm_model_prompts WHERE model_id = %s", (model_id,))
            for pid in payload.prompt_ids:
                cursor.execute("""
                    INSERT IGNORE INTO llm_model_prompts (model_id, prompt_id)
                    VALUES (%s, %s)
                """, (model_id, pid))
        conn.commit()
        return {"message": "Model prompts updated"}
    finally:
        conn.close()
