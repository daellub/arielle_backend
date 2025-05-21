# backend/mcp/routes/llm_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator
from typing import List, Optional
import json

router = APIRouter()

class LLMModelIn(BaseModel):
    name: str
    model_key: str
    endpoint: str
    type: str
    framework: str
    status: str = 'inactive'
    enabled: bool = True
    apiKey: Optional[str] = None
    token: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    def check_status(cls, values):
        status = values.get('status')
        if status not in ['active', 'inactive']:
            raise ValueError('status must be either "active" or "inactive"')
        return values
    
class LLMModelOut(LLMModelIn):
    id: int
    model_key: Optional[str]

class LLMModelPatch(BaseModel):
    name: Optional[str] = None
    model_key: Optional[str] = None
    endpoint: Optional[str] = None
    type: Optional[str] = None
    framework: Optional[str] = None
    status: Optional[str] = None
    enabled: Optional[bool] = None
    apiKey: Optional[str] = None
    token: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    def check_status(cls, values):
        if 'status' in values:
            status = values.get('status')
            if status not in ['active', 'inactive']:
                raise ValueError('status must be either "active" or "inactive"')
        return values

@router.get("/llm/model")
async def get_llm_models():
    try:
        from backend.db.database import get_llm_models_from_db
        models = get_llm_models_from_db()
        return {"models": [LLMModelOut(**m) for m in models]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 조회 실패: {str(e)}")

@router.post("/llm/model")
async def register_llm_model(model_info: LLMModelIn):
    try:
        from backend.db.database import save_llm_model_to_db
        model_id = save_llm_model_to_db(model_info)
        return {"message": "LLM 모델 등록 성공", "model_id": model_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 모델 등록 실패: {str(e)}")

@router.patch("/llm/model/{model_id}")
async def update_llm_model(model_id: str, model_info: LLMModelPatch):
    try:
        print(f"Received model info: {model_info}")
        from backend.db.database import update_llm_model_in_db
        update_llm_model_in_db(model_id, model_info)
        return {"message": "LLM 모델 업데이트 성공"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 모델 업데이트 실패: {str(e)}")
    
@router.delete("/llm/model/{model_id}")
async def delete_llm_model(model_id: int):
    try:
        from backend.db.database import delete_llm_model_from_db
        delete_llm_model_from_db(model_id)
        return {"message": "LLM 모델 삭제 성공"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 모델 삭제 실패: {str(e)}")
    
@router.get("/llm/model/{model_id}/integrations")
async def get_model_integrations(model_id: int):
    from backend.db.database import get_llm_models_from_db
    models = get_llm_models_from_db()
    model = next((m for m in models if m["id"] == model_id), None)
    if model is None:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다.")
    
    try:
        params = json.load(model.get("params") or "{}")
        return {"integrations": params.get("integrations", [])}
    except Exception:
        return {"integrations": []}
    
@router.patch("/llm/model/{model_id}/integrations")
async def update_model_integrations(model_id: int, payload: dict):
    from backend.db.database import get_connection
    conn = get_connection()
    try:
        integrations: List[str] = payload.get("integrations", [])
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT params FROM llm_models WHERE id = %s
                """, (model_id,))
            row = cursor.fetchone()
            current_params = json.loads(row[0] or '{}')
            current_params["integrations"] = integrations

            cursor.execute("""
                UPDATE llm_models SET params = %s WHERE id = %s
            """, (json.dumps(current_params), model_id))
        conn.commit()
        return {"message": "Integrations updated", "model_id": model_id}
    finally:
        conn.close()

@router.get("/llm/model/{model_id}/params")
async def get_model_params(model_id: int):
    from backend.db.database import get_connection
    import json

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT params FROM llm_models WHERE id = %s", (model_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다.")
            try:
                params = json.loads(row[0] or '{}')
            except Exception:
                params = {}
            return params
    finally:
        conn.close()

@router.patch("/llm/model/{model_id}/params")
async def update_model_params(model_id: int, payload: dict):
    from backend.db.database import get_connection
    import json

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT params FROM llm_models WHERE id = %s", (model_id,))
            row = cursor.fetchone()
            current = json.loads(row[0]) if row and row[0] else {}

            merged = {**current, **payload}

            cursor.execute("""
                UPDATE llm_models SET params = %s WHERE id = %s
            """, (json.dumps(merged), model_id))
        conn.commit()
        return {"message": "Params updated", "model_id": model_id}
    finally:
        conn.close()
