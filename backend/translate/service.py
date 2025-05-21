# backend/translate/service.py
from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.db.database import save_translation_result, get_connection

router = APIRouter()

class FavoriteUpdate(BaseModel):
    id: str
    favorite: bool

@router.post('/save_translation')
async def save_translation(request: Request):
    data = await request.json()
    save_translation_result(
        client_id=data.get('id'),
        original=data.get('original', ''),
        translated=data.get('translated', ''),
        target_lang=data.get('targetLang', 'en'),
        source_type=data.get('source', 'Direct')
    )
    return {'status': 'ok'}

@router.patch("/favorite")
async def toggle_favorite(data: dict):
    client_id = data["id"]
    favorite = data["favorite"]

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "UPDATE translation_results SET favorite = %s WHERE client_id = %s"
            cursor.execute(sql, (favorite, client_id))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()