# backend/mcp/routes/prompt_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.db.database import get_connection, insert_mcp_log
import json

router = APIRouter(prefix="/api")


class PromptIn(BaseModel):
    name: str
    description: Optional[str] = None
    full: str
    variables: list[str]
    enabled: bool = True

    class Config:
        from_attributes = True

class PromptOut(PromptIn):
    id: int
    full: str

@router.get("/prompts", response_model=List[PromptOut])
async def get_prompts():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM mcp_prompts")
            prompts = cursor.fetchall()
            
            return [
                PromptOut(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    full=row[3],
                    variables=json.loads(row[4])    
                ) for row in prompts
            ]
    finally:
        conn.close()

@router.post("/prompts", response_model=PromptOut)
async def create_prompt(prompt: PromptIn):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO mcp_prompts (name, description, template, variables)
                VALUES (%s, %s, %s, %s)
            """, (prompt.name, prompt.description, prompt.full, json.dumps(prompt.variables)))
            conn.commit()
            
            insert_mcp_log("INFO", "PROMPT", f"Created prompt: {prompt.name}")
            
            return PromptOut(
                id=cursor.lastrowid,
                name=prompt.name,
                description=prompt.description,
                full=prompt.full,
                variables=prompt.variables
            )
    finally:
        conn.close()

@router.patch("/prompts/{prompt_id}", response_model=PromptOut)
async def update_prompt_in_db(prompt_id: int, prompt: PromptIn):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM mcp_prompts WHERE id = %s", (prompt_id,))
            existing_prompt = cursor.fetchone()
            
            if not existing_prompt:
                raise HTTPException(status_code=404, detail="Prompt not found")

        update_fields = []
        update_values = []

        if prompt.name != existing_prompt[1]:
            update_fields.append("name = %s")
            update_values.append(prompt.name)
        if prompt.description != existing_prompt[2]:
            update_fields.append("description = %s")
            update_values.append(prompt.description)
        if prompt.full != existing_prompt[3]:
            update_fields.append("template = %s")
            update_values.append(prompt.full)
        if prompt.variables != json.loads(existing_prompt[4]):
            update_fields.append("variables = %s")
            update_values.append(json.dumps(prompt.variables))
        if prompt.enabled != existing_prompt[5]:
            update_fields.append("enabled = %s")
            update_values.append(prompt.enabled)
        
        if not update_fields:
            return PromptOut(
                id=prompt_id,
                name=existing_prompt[1],
                description=existing_prompt[2],
                full=existing_prompt[3],
                variables=json.loads(existing_prompt[4]),
                enabled=existing_prompt[5]
            )
        
        update_fields_str = ", ".join(update_fields)
        update_values.append(prompt_id)

        with conn.cursor() as cursor:
            cursor.execute(f"""
                UPDATE mcp_prompts
                SET {update_fields_str}
                WHERE id = %s
            """, tuple(update_values))
            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Prompt not found")

            changed_fields = [label for field, label in zip(
                [prompt.name != existing_prompt[1],
                prompt.description != existing_prompt[2],
                prompt.full != existing_prompt[3],
                prompt.variables != json.loads(existing_prompt[4]),
                prompt.enabled != existing_prompt[5]],
                ['name', 'description', 'template', 'variables', 'enabled']
            ) if field]

            insert_mcp_log("INFO", "PROMPT", f"Updated prompt (id={prompt_id}): {prompt.name} ({', '.join(changed_fields)})")

            return PromptOut(
                id=prompt_id,
                name=prompt.name,
                description=prompt.description,
                full=prompt.full,
                variables=prompt.variables,
                enabled=prompt.enabled
            )
    finally:
        conn.close()

@router.delete("/prompts/{prompt_id}", status_code=204)
async def delete_prompt(prompt_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM mcp_prompts WHERE id = %s", (prompt_id,))
            conn.commit()

            insert_mcp_log("INFO", "PROMPT", f"Deleted prompt: id={prompt_id}")
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Prompt not found")
    finally:
        conn.close()
    return