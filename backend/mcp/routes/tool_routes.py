# backend/mcp/routes/tool_routes.py
import os
from fastapi import APIRouter, HTTPException, Query
import httpx
from pydantic import BaseModel
from typing import List
from backend.db.database import get_connection, insert_mcp_log

import subprocess
import shlex
import urllib.parse

router = APIRouter(prefix="/api")

# ──────── Pydantic Models ────────

class ToolIn(BaseModel):
    name: str
    type: str
    command: str
    status: str
    enabled: bool

class ToolOut(ToolIn):
    id: int

# ──────── CRUD Endpoints ────────

@router.get("/tools", response_model=List[ToolOut])
async def get_tools():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM mcp_tools")
            rows = cursor.fetchall()
            return [ToolOut(
                id=row[0],
                name=row[1],
                type=row[2],
                command=row[3],
                status=row[4],
                enabled=row[5]
            ) for row in rows]
    finally:
        conn.close()

@router.post("/tools", response_model=ToolOut)
async def create_tool(tool: ToolIn):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO mcp_tools (name, type, command, status, enabled)
                VALUES (%s, %s, %s, %s, %s)
            """, (tool.name, tool.type, tool.command, tool.status, tool.enabled))
            conn.commit()

            insert_mcp_log("INFO", "TOOL", f"Created tool: {tool.name} ({tool.type})")
            return ToolOut(id=cur.lastrowid, **tool.dict())
    finally:
        conn.close()

@router.patch("/tools/{tool_id}", response_model=ToolOut)
async def update_tool(tool_id: int, tool: ToolIn):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE mcp_tools
                SET name=%s, type=%s, command=%s, status=%s, enabled=%s
                WHERE id=%s
            """, (tool.name, tool.type, tool.command, tool.status, tool.enabled, tool_id))
            conn.commit()
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tool not found")
            
            insert_mcp_log("INFO", "TOOL", f"Updated tool (id={tool_id}): {tool.name}")
            return ToolOut(id=tool_id, **tool.dict())
    finally:
        conn.close()

@router.delete("/tools/{tool_id}", status_code=204)
async def delete_tool(tool_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM mcp_tools WHERE id = %s", (tool_id,))
            conn.commit()
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tool not found")
            
            insert_mcp_log("INFO", "TOOL", f"Deleted tool: id={tool_id}")
    finally:
        conn.close()

# ──────── Tools ────────
@router.get("/tools/python")
async def execute_python_script(command: str = Query(..., description="Python command to execute")):
    try:
        # URL 디코딩
        decoded_command = urllib.parse.unquote(command)

        result = subprocess.run(
            ['python', '-c', decoded_command],
            text=True, capture_output=True, check=True
        )

        insert_mcp_log("PROCESS", "TOOL", f"Executed python tool: {decoded_command}")
        return {"result": result.stdout.strip()}
    except subprocess.CalledProcessError as e:
        insert_mcp_log("ERROR", "TOOL", f"Python tool execution failed: {decoded_command}")
        return {"error": f"Execution failed: {e.stderr}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@router.get("/tools/powershell")
async def execute_powershell_script(command: str = Query(..., description="PowerShell command to execute")):
    try:
        result = subprocess.run(
            ['powershell', '-Command', command],
            text=True, capture_output=True, check=True
        )

        insert_mcp_log("PROCESS", "TOOL", f"Executed PowerShell tool: {command}")
        return {"result": result.stdout}
    except subprocess.CalledProcessError as e:
        insert_mcp_log("ERROR", "TOOL", f"PowerShell execution failed: {command}")
        return {"error": f"Execution failed: {e.stderr}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
    
@router.get("/tools/search")
async def search_google(query: str = Query(..., description="검색어")):
    GOOGLE_API_KEY = os.getenv("GOOGLE_SEARCHENGINE_KEY")
    GOOGLE_CX = os.getenv("GOOGLE_SEARCHENGINE_ID")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query
    }

    async with httpx.AsyncClient() as client:
        res = await client.get(url, params=params)
        data = res.json()

    if "items" not in data or len(data["items"]) == 0:
        return {"error": "검색 결과 없음 또는 API 오류", "raw": data}
    
    first = data["items"][0]
    return {
        "title": first.get("title"),
        "summary": first.get("snippet"),
        "link": first.get("link"),
    }