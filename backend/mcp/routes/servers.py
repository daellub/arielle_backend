# backend/mcp/routes/servers.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from typing import List
import time, httpx

from backend.db.database import (
    list_mcp_servers,
    get_mcp_server,
    create_mcp_server,
    update_mcp_server,
    delete_mcp_server,
    insert_mcp_log
)

router = APIRouter()

class ServerIn(BaseModel):
    alias: str = Field(..., max_length=50)
    name: str
    endpoint: HttpUrl
    type: str
    auth_type: str = 'none'
    api_key: str = None
    token: str = None
    username: str = None
    password: str = None
    enabled: bool = True
    polling_interval: int = 30

class ServerOut(ServerIn):
    api_key: str = ''
    token: str = ''
    username: str = ''
    password: str = ''

@router.get("/servers", response_model=List[ServerOut])
async def api_list_servers():
    servers = list_mcp_servers()
    for server in servers:
        server['api_key'] = server.get('api_key', '') or ''
        server['token'] = server.get('token', '') or ''
        server['username'] = server.get('username', '') or ''
        server['password'] = server.get('password', '') or ''
    return servers

@router.post("/servers", status_code=201)
async def api_create_server(server: ServerIn):
    if get_mcp_server(server.alias):
        raise HTTPException(status_code=400, detail="Alias 중복")
    create_mcp_server(server.model_dump())
    insert_mcp_log("INFO", "MCP-SERVER", f"Registered server: alias={server.alias}, type={server.type}")
    return {"ok": True}

@router.patch("/servers/{alias}")
async def api_update_server(alias: str, fields: ServerIn):
    if not get_mcp_server(alias):
        raise HTTPException(status_code=404, detail="서버 없음")
    update_mcp_server(alias, fields.model_dump(exclude_unset=True))
    updated_fields = ", ".join(fields.model_dump(exclude_unset=True).keys())
    insert_mcp_log("INFO", "MCP-SERVER", f"Updated server '{alias}' fields: {updated_fields}")
    return {"ok": True}

@router.delete("/servers/{alias}", status_code=204)
async def api_delete_server(alias: str):
    if not get_mcp_server(alias):
        raise HTTPException(status_code=404, detail="서버 없음")
    delete_mcp_server(alias)
    insert_mcp_log("INFO", "MCP-SERVER", f"Deleted server: alias={alias}")

@router.get("/servers/{alias}/status")
async def api_server_status(alias: str):
    srv = get_mcp_server(alias)
    if not srv:
        raise HTTPException(status_code=404, detail="서버 없음")
    
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            await cli.get(f"{srv['endpoint'].rstrip('/')}/healthz")
        status = "active"
    except Exception:
        status = "inactive"
        
    latency = int((time.monotonic() - start) * 1000)
    insert_mcp_log("PROCESS", "MCP-SERVER", f"Checked status of '{alias}': {status}, {latency}ms")
    return {
        "status": status,
        "latency": latency,
        "lastChecked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

@router.get("/healthz")
async def health_check():
    try:
        # 서버 상태 확인
        return {"status": "ok", "message": "Server is healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
