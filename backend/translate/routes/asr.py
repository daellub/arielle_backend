# backend/translate/routes/asr.py

from fastapi import APIRouter
from backend.db.database import get_connection

router = APIRouter()

@router.get("/asr/latest")
async def get_latest_asr():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT transcription FROM asr_records ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            return {"text": row[0] if row else ""}
    finally:
        conn.close()