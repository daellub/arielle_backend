# backend/db/translate_db.py
from backend.db.base import get_connection

def save_translation_result(client_id: str, original: str, translated: str, target_lang: str, source_type: str):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO translation_results (client_id, original, translated, target_lang, source_type, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, (client_id, original, translated, target_lang, source_type))
        conn.commit()
        print("\033[94m" + "[DB] 번역 결과가 저장되었습니다.\n")
    except Exception as e:
        print("\033[91m" + f"[ERROR] 번역 결과 저장 실패: {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()