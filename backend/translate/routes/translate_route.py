# backend/translate/routes/translate.py
import os
import uuid
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

class TranslateRequest(BaseModel):
    text: str
    from_lang: str = 'ko'
    to: str

@router.post('/translate')
async def translate_text(req: TranslateRequest):
    endpoint = os.getenv('AZURE_TRANSLATOR_ENDPOINT')
    key = os.getenv('AZURE_TRANSLATOR_KEY')
    region = os.getenv('AZURE_TRANSLATOR_REGION')

    if not endpoint or not key or not region:
        raise HTTPException(status_code=500, detail="Azure Translator API 설정이 누락되었습니다.")

    print("[DEBUG] endpoint:", endpoint)
    print("[DEBUG] key:", key)
    print("[DEBUG] region:", region)

    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Ocp-Apim-Subscription-Region': region,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4()),
    }

    params = {
        'api-version': '3.0',
        'from': req.from_lang,
        'to': [req.to],
    }

    body = [{ 'text': req.text }]

    async with httpx.AsyncClient() as client:
        response = await client.post(f'{endpoint}/translate', params=params, headers=headers, json=body)
        response.encoding = 'utf-8'

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    try:
        result = response.json()

        # ✅ 방어 코드: 리스트가 비어있거나 예상 구조가 아니면 예외 처리
        if not isinstance(result, list) or not result or 'translations' not in result[0]:
            raise ValueError(f"Unexpected Azure response: {result}")

        translated = result[0]['translations'][0]['text']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"번역 실패: {str(e)}")

    return JSONResponse(content={"translated": translated})
