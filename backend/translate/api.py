# backend/translate/routes/translate.py
import os
import uuid
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dotenv import load_dotenv

router = APIRouter()

class TranslateRequest(BaseModel):
    text: str
    from_lang: str = 'ko'
    to: str

@router.post('/translate')
async def translate_text(req: TranslateRequest):
    print("📝 입력 텍스트:", req.text)

    endpoint = os.getenv('AZURE_TRANSLATOR_ENDPOINT')
    key = os.getenv('AZURE_TRANSLATOR_KEY')
    region = os.getenv('AZURE_TRANSLATOR_REGION')

    if not endpoint or not key or not region:
        raise HTTPException(status_code=500, detail="Azure Translator API 설정이 누락되었습니다.")
    
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

    print("📤 Azure 요청 바디:", body)

    async with httpx.AsyncClient() as client:
        response = await client.post(f'{endpoint}/translate', params=params, headers=headers, json=body)
        response.encoding = 'utf-8'
        print("🌐 Azure 응답 내용:", response.text)

    result = response.json()
    translated = result[0]['translations'][0]['text']
    print("🔁 번역 결과:", translated)
    
    return JSONResponse(content={"translated": translated})
