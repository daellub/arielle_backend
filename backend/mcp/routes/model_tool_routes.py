# backend/mcp/routes/model_tool_routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from backend.db.database import get_connection

router = APIRouter(prefix="/llm/model")

class ToolLink(BaseModel):
    tool_ids: List[int]

class LinkedToolOut(BaseModel):
    id: int
    tool_id: int
    created_at: str

@router.get("/{model_id}/tools", response_model=List[LinkedToolOut])
async def get_model_tools(model_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, tool_id, created_at
                FROM llm_model_tools
                WHERE model_id = %s
            """, (model_id,))
            rows = cursor.fetchall()
            return [
                {"id": row[0], "tool_id": row[1], "created_at": row[2].isoformat()}
                for row in rows
            ]
    finally:
        conn.close()

@router.patch("/{model_id}/tools")
async def update_model_tools(model_id: int, payload: ToolLink):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM llm_model_tools WHERE model_id = %s", (model_id,))
            for tid in payload.tool_ids:
                cursor.execute("""
                    INSERT IGNORE INTO llm_model_tools (model_id, tool_id)
                    VALUES (%s, %s)
                """, (model_id, tid))
        conn.commit()
        return {"message": "Model tools updated"}
    finally:
        conn.close()
