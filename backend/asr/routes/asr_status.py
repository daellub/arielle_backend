# backend/asr/routes/asr_status.py

from fastapi import APIRouter
from backend.db.database import get_connection

router = APIRouter()

@router.get("/asr/status")
def get_asr_status():
    db_ok = False
    model_ok = False

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # DB 체크
            cursor.execute("SELECT 1")
            db_ok = True

            # 모델 체크
            cursor.execute("SELECT COUNT(*) FROM asr_models WHERE loaded = 1")
            result = cursor.fetchone()
            model_ok = result[0] > 0

    except Exception as e:
        print(f"[ERROR] 상태 확인 실패: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

    return {
        "db": db_ok,
        "model": model_ok,
        "mic": False,       # 추후 연동
        "hardware": True    # 하드웨어는 기본 활성화 처리
    }

@router.get("/asr/db/info")
def get_db_info():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]

            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]

        return {
            "db_name": db_name,
            "tables": tables
        }

    except Exception as e:
        print(f"[ERROR] DB 정보 조회 실패: {e}")
        return {
            "db_name": None,
            "tables": [],
            "error": str(e)
        }
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@router.get("/asr/model/info")
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
            else:
                return { "loaded": False }

    except Exception as e:
        print(f"[ERROR] 모델 정보 조회 실패: {e}")
        return { "loaded": False, "error": str(e) }
    finally:
        if 'conn' in locals() and conn:
            conn.close()