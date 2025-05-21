# backend/mcp/routes/data_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.db.database import get_connection, insert_mcp_log
from urllib.parse import urlparse
import pymysql

router = APIRouter(prefix="/api")

class LocalSourceIn(BaseModel):
    name: str
    path: str
    type: str = 'folder'
    status: str = 'active'
    enabled: bool = True
    host: Optional[str] = None
    port: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class LocalSourceOut(LocalSourceIn):
    id: int

class RemoteSourceIn(BaseModel):
    name: str
    endpoint: str
    auth: bool
    status: str = 'active'
    enabled: bool = True

class RemoteSourceOut(RemoteSourceIn):
    id: int

def parse_mysql_uri(uri: str):
    parsed = urlparse(uri)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "username": parsed.username,
        "password": parsed.password,
        "db": parsed.path.lstrip('/'),
    }

@router.post("/local-sources", response_model=LocalSourceOut)
async def create_local_source(source: LocalSourceIn):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO local_sources (name, path, type, status, enabled, host, port, username, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (source.name, source.path, source.type, source.status, source.enabled, source.host, source.port, source.username, source.password))
            conn.commit()
            insert_mcp_log("INFO", "DATA", f"Created local source: {source.name} → {source.path}")
            return {**source.dict(), 'id': cursor.lastrowid}
    finally:
        conn.close()

@router.post("/remote-sources", response_model=RemoteSourceOut)
async def create_remote_source(source: RemoteSourceIn):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO remote_sources (name, endpoint, auth, status, enabled)
                VALUES (%s, %s, %s, %s, %s)
            """, (source.name, source.endpoint, source.auth, source.status, source.enabled))
            conn.commit()
            insert_mcp_log("INFO", "DATA", f"Created remote source: {source.name} → {source.endpoint}")
            return {**source.dict(), 'id': cursor.lastrowid}
    finally:
        conn.close()

@router.get("/local-sources", response_model=List[LocalSourceOut])
async def get_local_sources():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM local_sources")
            local_sources = cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in local_sources]
    finally:
        conn.close()

@router.get("/remote-sources", response_model=List[RemoteSourceOut])
async def get_remote_sources():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM remote_sources")
            remote_sources = cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in remote_sources]
    finally:
        conn.close()

@router.patch("/local-sources/{source_id}", response_model=LocalSourceOut)
async def update_local_source(source_id: int, source: LocalSourceIn):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE local_sources
                SET name = %s, path = %s, type = %s, status = %s, enabled = %s, host = %s, port = %s, username = %s, password = %s
                WHERE id = %s
            """, (source.name, source.path, source.type, source.status, source.enabled, source.host, source.port, source.username, source.password, source_id))
            conn.commit()
            insert_mcp_log("INFO", "DATA", f"Updated local source (id={source_id}): {source.name}")
            return {**source.dict(), 'id': source_id}
    finally:
        conn.close()

@router.patch("/remote-sources/{source_id}", response_model=RemoteSourceOut)
async def update_remote_source(source_id: int, source: RemoteSourceIn):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE remote_sources
                SET name = %s, endpoint = %s, auth = %s, status = %s, enabled = %s
                WHERE id = %s
            """, (source.name, source.endpoint, source.auth, source.status, source.enabled, source_id))
            conn.commit()
            insert_mcp_log("INFO", "DATA", f"Updated remote source (id={source_id}): {source.name}")
            return {**source.dict(), 'id': source_id}
    finally:
        conn.close()

@router.delete("/local-sources/{source_id}")
async def delete_local_source(source_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM local_sources WHERE id = %s", (source_id,))
            conn.commit()
            insert_mcp_log("INFO", "DATA", f"Deleted local source (id={source_id})")
            return {"message": "Local source deleted successfully"}
    finally:
        conn.close()

@router.delete("/remote-sources/{source_id}")
async def delete_remote_source(source_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM remote_sources WHERE id = %s", (source_id,))
            conn.commit()
            insert_mcp_log("INFO", "DATA", f"Deleted remote source (id={source_id})")
            return {"message": "Remote source deleted successfully"}
    finally:
        conn.close()

@router.get("/local-sources/{source_id}/preview")
async def preview_local_source(source_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM local_sources WHERE id = %s", (source_id,))
            source = cursor.fetchone()
            if not source or source[2] != "database":
                raise HTTPException(status_code=404, detail="Database source not found.")

            columns = [col[0] for col in cursor.description]
            source_dict = dict(zip(columns, source))

            db_config = {
                "host": source_dict["host"],
                "port": int(source_dict["port"]),
                "user": source_dict["username"],
                "password": source_dict["password"],
                "database": source_dict["path"].split("/")[-1],
                "charset": "utf8mb4",
                "cursorclass": pymysql.cursors.DictCursor
            }

        preview_conn = pymysql.connect(**db_config)
        with preview_conn.cursor() as preview_cursor:
            preview_cursor.execute("SELECT name, race, role, personality, backstory FROM characters LIMIT 5")
            rows = preview_cursor.fetchall()

        return {"preview": rows}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
