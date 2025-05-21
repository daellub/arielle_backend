# backend/mcp/routes/log_routes.py
from fastapi import APIRouter
from backend.db.database import get_connection

router = APIRouter(prefix="/api")

@router.get("/logs")
async def get_mcp_logs():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT timestamp, type, source, message
                FROM mcp_logs
                ORDER BY timestamp DESC
                LIMIT 200
            ''')
            rows = cursor.fetchall()
            return [
                {
                    "timestamp": row[0].strftime("%H:%M:%S"),
                    "type": row[1],
                    "source": row[2],
                    "message": row[3]
                }
                for row in rows
            ]
    finally:
        conn.close()
