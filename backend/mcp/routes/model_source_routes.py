# backend/mcp/routes/model_source_routes.py
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.db.database import get_connection, update_llm_model_params

class SourceItem(BaseModel):
    source_id: int
    source_type: str

class SourceIdsIn(BaseModel):
    sources: List[SourceItem]

router = APIRouter(prefix="/llm/model")

@router.get("/{model_id}/sources")
async def get_model_sources(model_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT source_id, source_type FROM llm_model_sources WHERE model_id = %s
            """, (model_id,))
            rows = cursor.fetchall()
            return {"sources": [{"source_id": row[0], "source_type": row[1]} for row in rows]}
    finally:
        conn.close()

@router.patch("/{model_id}/sources")
async def update_model_sources(
    model_id: int,
    payload: SourceIdsIn,
    source_type: str
):
    conn = get_connection()
    try:
        source_ids = [s.source_id for s in payload.sources]

        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM llm_model_sources
                WHERE model_id = %s AND source_type = %s
            """, (model_id, source_type))

            for source_id in source_ids:
                cursor.execute("""
                    INSERT IGNORE INTO llm_model_sources (model_id, source_id, source_type)
                    VALUES (%s, %s, %s)
                """, (model_id, source_id, source_type))

            conn.commit()

            cursor.execute("SELECT params FROM llm_models WHERE id = %s", (model_id,))
            row = cursor.fetchone()
            params = json.loads(row[0] or '{}')

            if source_type == 'local':
                params["local_sources"] = source_ids
            elif source_type == 'remote':
                params["remote_sources"] = source_ids

            cursor.execute(
                "UPDATE llm_models SET params = %s WHERE id = %s",
                (json.dumps(params), model_id)
            )

        return {"message": "Model sources updated successfully"}
    finally:
        conn.close()



@router.delete("/{model_id}/sources/{source_id}")
async def delete_model_source(model_id: int, source_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM llm_model_sources WHERE model_id = %s AND source_id = %s
            """, (model_id, source_id))
        conn.commit()
        return {"message": "Model source deleted successfully"}
    finally:
        conn.close()