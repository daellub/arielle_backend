from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
import httpx
import time

router = APIRouter(prefix="/llm/model")

class ModelLoadRequest(BaseModel):
    response_time: float
    result: str

@router.get("/{alias}/test", response_model=ModelLoadRequest)
async def test_model_response(alias: str = Path(...)):
    try:
        url = "http://localhost:8080/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": alias,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            "temperature": 0.7,
            "max_tokens": 32
        }

        start = time.perf_counter()

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        end = time.perf_counter()
        result = (response.json().get("choices", [{}])[0].get("message", {}).get("content") or "").strip()

        return {
            "response_time": round(end - start, 3),
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{alias}/check")
async def check_model_loaded(alias: str = Path(...)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/v1/models")
            response.raise_for_status()

        models = response.json().get("data", [])
        model_ids = [m["id"] for m in models]

        return {"loaded": alias in model_ids}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
