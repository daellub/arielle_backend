# backend/translate/routes/llm.py
from fastapi import APIRouter
from backend.db.database import get_connection

router = APIRouter()

@router.get('/llm/latest')
async def get_latest_llm():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT response FROM llm_interactions ORDER BY created_at DESC LIMIT 1')
            row  = cursor.fetchone()
            return {'text': row[0] if row else ''}
    finally:
        conn.close()