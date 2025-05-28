# backend/llm/emotion/generator.py
from backend.llm.emotion.prompt import PROMPT_TEMPLATE

def generate_prompt(text: str) -> str:
    return PROMPT_TEMPLATE.format(text=text)
