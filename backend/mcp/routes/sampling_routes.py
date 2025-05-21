# backend/mcp/routes/sampling_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.database import get_connection, insert_mcp_log

router = APIRouter(prefix="/api")

class SamplingSettings(BaseModel):
    temperature: float
    top_k: int
    top_p: float
    repetition_penalty: float

@router.get("/sampling/settings")
async def get_sampling_settings():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM llm_sampling_settings ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "temperature": row[1],
                    "top_k": row[2],
                    "top_p": row[3],    
                    "repetition_penalty": row[4]
                }
            else:
                raise HTTPException(status_code=404, detail="No sampling settings found")
    finally:
        conn.close()

@router.post("/sampling/settings")
async def save_sampling_settings(settings: SamplingSettings):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO llm_sampling_settings (
                    temperature, top_k, top_p, repetition_penalty
                ) VALUES (%s, %s, %s, %s)
            ''', (settings.temperature, settings.top_k, settings.top_p, settings.repetition_penalty))
            conn.commit()

            insert_mcp_log(
                "INFO",
                "SAMPLING",
                f"Initial sampling settings saved: temp={settings.temperature}, top_k={settings.top_k}, top_p={settings.top_p}, penalty={settings.repetition_penalty}"
            )
            return {"message": "Sampling settings saved"}
    finally:
        conn.close()

@router.patch("/sampling/settings")
async def update_sampling_settings(settings: SamplingSettings):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                UPDATE llm_sampling_settings
                SET temperature = %s, top_k = %s, top_p = %s, repetition_penalty = %s
                WHERE id = 1
            ''', (settings.temperature, settings.top_k, settings.top_p, settings.repetition_penalty))
            conn.commit()

            insert_mcp_log(
                "INFO",
                "SAMPLING",
                f"Updated sampling: temp={settings.temperature}, top_k={settings.top_k}, top_p={settings.top_p}, penalty={settings.repetition_penalty}"
            )
            return {"message": "Sampling settings updated"}
    finally:
        conn.close()