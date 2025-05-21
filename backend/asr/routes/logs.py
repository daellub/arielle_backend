# backend/asr/routes/logs.py
from fastapi import APIRouter, Query
from typing import Optional, List

import pymysql.cursors
from backend.db.database import get_connection
import pymysql

router = APIRouter()

@router.get('/logs')
def get_logs(
    limit: int = Query(50, ge=1),
    offset: int =Query(0, ge=0),
    type: Optional[str] = None,
    query: Optional[str] = None,
    since: Optional[str] = Query(None, description='ISO timestamp')
):
    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT id, timestamp, type, source, message FROM asr_logs"
            conditions = []
            params = []

            if type:
                conditions.append("type = %s")
                params.append(type)

            if query:
                conditions.append("(message LIKE %s OR source LIKE %s)")
                like_query = f"%{query}%"
                params.extend([like_query, like_query])

            if since:
                conditions.append("timestamp >= %s")
                params.append(since)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            sql += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        return {'error': str(e)}
    finally:
        if conn:
            conn.close()

@router.get('/log-suggestions', response_model=List[str])
def get_log_suggestions(
    q: str = Query(..., min_length=1, description='검색어 앞글자')
):
    """
    'q'로 시작하는 메시지나 소스 조합에서 중복을 제거한 뒤
    최대 10개까지 앞쪽부터 반환합니다
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT DISTINCT message AS suggestion
                FROM asr_logs
                WHERE message LIKE %s
                   OR source  LIKE %s
                ORDER BY suggestion ASC
                LIMIT 10
            """
            like_q = f"%{q}%"
            cursor.execute(sql, [like_q, like_q])
            return [r['suggestion'] for r in cursor.fetchall()]
    except Exception as e:
        return []
    finally:
        if conn:
            conn.close()