# backend/mcp/routes/memory_routes.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
import json

from backend.db.database import get_connection, insert_mcp_log

router = APIRouter(prefix="/api")

class MemoryContextSettings(BaseModel):
    memory_strategy: str
    max_tokens: int
    include_history: bool
    save_memory: bool
    context_prompts: list

@router.get("/memory/settings")
async def get_memory_settings():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM llm_memory_settings ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "memory_strategy": row[1],
                    "max_tokens": row[2],
                    "include_history": row[3],
                    "save_memory": row[4],
                    "context_prompts": json.loads(row[5]) if row[5] else []
                }
            else:
                return {
                    "memory_strategy": "Hybrid",
                    "max_tokens": 2048,
                    "include_history": True,
                    "save_memory": True,
                    "context_prompts": []
                }
    finally:
        conn.close()

@router.post("/memory/settings")
async def save_memory_settings(settings: MemoryContextSettings):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO llm_memory_settings (
                    memory_strategy, max_tokens, include_history, save_memory, context_prompts
                ) VALUES (%s, %s, %s, %s, %s)
            ''', (settings.memory_strategy, settings.max_tokens, settings.include_history, settings.save_memory, json.dumps(settings.context_prompts)))
            
            conn.commit()

            insert_mcp_log(
                "INFO",
                "MEMORY",
                f"Initial memory settings saved: strategy={settings.memory_strategy}, max_tokens={settings.max_tokens}"
            )

            return {"message": "Settings saved successfully"}
    finally:
        conn.close()

@router.patch("/memory/settings")
async def update_memory_settings(settings: MemoryContextSettings):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                UPDATE llm_memory_settings
                SET memory_strategy = %s, max_tokens = %s, include_history = %s, save_memory = %s, context_prompts = %s
                WHERE id = 1
            ''', (settings.memory_strategy, settings.max_tokens, settings.include_history, settings.save_memory, json.dumps(settings.context_prompts)))
            
            conn.commit()

            insert_mcp_log(
                "INFO",
                "MEMORY",
                f"Updated memory settings: strategy={settings.memory_strategy}, max_tokens={settings.max_tokens}, history={settings.include_history}, save={settings.save_memory}, prompts={len(settings.context_prompts)}"
            )

            return {"message": "Settings updated successfully"}
    finally:
        conn.close()