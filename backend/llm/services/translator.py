# backend/llm/services/translator.py

import os
import httpx

AZURE_TRANSLATE_URL = os.getenv("AZURE_TRANSLATOR_ENDPOINT")
AZURE_TRANSLATE_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_TRANSLATE_REGION = os.getenv("AZURE_TRANSLATOR_REGION")

async def translate(text: str, from_lang: str, to_lang: str) -> str:
    if not AZURE_TRANSLATE_URL or not AZURE_TRANSLATE_KEY or not AZURE_TRANSLATE_REGION:
        raise RuntimeError("Azure Translator API 설정이 누락되었습니다.")

    headers = {
        'Ocp-Apim-Subscription-Key': AZURE_TRANSLATE_KEY,
        'Ocp-Apim-Subscription-Region': AZURE_TRANSLATE_REGION,
        'Content-type': 'application/json',
    }

    params = {
        'api-version': '3.0',
        'from': from_lang,
        'to': [to_lang],
    }

    body = [{ 'text': text }]

    async with httpx.AsyncClient() as client:
        res = await client.post(f'{AZURE_TRANSLATE_URL}/translate', params=params, headers=headers, json=body)
        res.raise_for_status()
        result = res.json()
        return result[0]['translations'][0]['text']

async def translate_to_ko_and_ja(text: str) -> tuple[str, str]:
    ko = await translate(text, from_lang='en', to_lang='ko')
    ja = await translate(text, from_lang='en', to_lang='ja')
    return ko, ja
