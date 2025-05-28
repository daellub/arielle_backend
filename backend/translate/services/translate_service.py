# backend/translate/services/translate_service.py

from backend.db.translate_db import save_translation_result
from backend.db.base import get_connection

def save_translation(data: dict):
    save_translation_result(
        client_id=data.get('id'),
        original=data.get('original', ''),
        translated=data.get('translated', ''),
        target_lang=data.get('targetLang', 'en'),
        source_type=data.get('source', 'Direct')
    )

def update_favorite_flag(client_id: str, favorite: bool):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE translation_results SET favorite = %s WHERE client_id = %s",
                (favorite, client_id)
            )
        conn.commit()
    finally:
        conn.close()
