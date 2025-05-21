# backend/mcp/routes/security_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.database import get_connection, insert_mcp_log
import json

router = APIRouter(prefix="/api")

class SecuritySettings(BaseModel):
    api_key_required: bool
    allowed_origins: str
    rate_limit: int
    use_jwt: bool
    disable_auth: bool

@router.get("/security/settings")
async def get_security_settings():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM llm_security_settings ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "api_key_required": row[1],
                    "allowed_origins": row[2],
                    "rate_limit": row[3],
                    "use_jwt": row[4],
                    "disable_auth": row[5]
                }
            else:
                raise HTTPException(status_code=404, detail="No security settings found")
    finally:
        conn.close()

@router.post("/security/settings")
async def save_security_settings(settings: SecuritySettings):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO llm_security_settings (
                    api_key_required, allowed_origins, rate_limit, use_jwt, disable_auth
                ) VALUES (%s, %s, %s, %s, %s)
            ''', (
                settings.api_key_required,
                settings.allowed_origins,
                settings.rate_limit,
                settings.use_jwt,
                settings.disable_auth
            ))
            conn.commit()

            insert_mcp_log(
                "INFO",
                "SECURITY",
                f"Initial security settings saved: apiKeyRequired={settings.api_key_required}, rateLimit={settings.rate_limit}, useJWT={settings.use_jwt}, disableAuth={settings.disable_auth}"
            )
            return {"message": "Security settings saved"}
    finally:
        conn.close()

@router.patch("/security/settings")
async def update_security_settings(settings: SecuritySettings):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                UPDATE llm_security_settings
                SET api_key_required = %s,
                    allowed_origins = %s,
                    rate_limit = %s,
                    use_jwt = %s,
                    disable_auth = %s
                WHERE id = 1
            ''', (
                settings.api_key_required,
                settings.allowed_origins,
                settings.rate_limit,
                settings.use_jwt,
                settings.disable_auth
            ))
            conn.commit()

            insert_mcp_log(
                "INFO",
                "SECURITY",
                f"Updated security settings: apiKeyRequired={settings.api_key_required}, rateLimit={settings.rate_limit}, useJWT={settings.use_jwt}, disableAuth={settings.disable_auth}, origins={settings.allowed_origins}"
            )
            return {"message": "Security settings updated"}
    finally:
        conn.close()
