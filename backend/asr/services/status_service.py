# backend/asr/services/status_service.py

from backend.db.base import get_connection

def check_asr_status():
    db_ok = False
    model_ok = False

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = True

            cursor.execute("SELECT COUNT(*) FROM asr_models WHERE loaded = 1")
            result = cursor.fetchone()
            model_ok = result[0] > 0

    finally:
        if 'conn' in locals() and conn:
            conn.close()

    return {
        "db": db_ok,
        "model": model_ok,
        "mic": False,
        "hardware": True
    }

def get_db_info():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
        return {"db_name": db_name, "tables": tables}
    except Exception as e:
        return {"db_name": None, "tables": [], "error": str(e)}
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_loaded_model_info():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT name, framework, device, language, loaded, created_at
                FROM asr_models
                WHERE loaded = 1
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "name": row[0],
                    "framework": row[1],
                    "device": row[2],
                    "language": row[3],
                    "loaded": bool(row[4]),
                    "created_at": row[5],
                }
    except Exception as e:
        return { "loaded": False, "error": str(e) }
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    return { "loaded": False }
