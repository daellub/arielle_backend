# backend/asr/services/log_service.py

from backend.db.base import get_connection
import pymysql

def fetch_logs(limit=50, offset=0, type=None, query=None, since=None):
    conn = None
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
    finally:
        if conn:
            conn.close()

def fetch_log_suggestions(q: str):
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
    finally:
        if conn:
            conn.close()
