# backend/llm/memory/context_builder.py

from backend.llm.memory.summarizer import get_summary
from typing import List, Dict

async def build_context(
    model_id: int,
    system_prompt: str,
    user_messages: List[Dict],
    memory_settings: Dict
) -> List[Dict]:
    """
    memory.strategy에 맞는 context 메시지 리스트를 생성합니다.
    """

    strategy = memory_settings.get("strategy", "None")
    max_tokens = memory_settings.get("max_tokens", 64)
    include_history = memory_settings.get("includeHistory", True)

    context = [{"role": "system", "content": system_prompt}]

    if strategy == "None":
        context += user_messages[-1:]

    elif strategy == "Window":
        window_size = max_tokens // 4
        context += user_messages[-window_size:] if include_history else user_messages[-1:]

    elif strategy == "Summary":
        summary = await get_summary(model_id)
        context.append({"role": "system", "content": summary})
        context += user_messages[-1:]

    elif strategy == "Hybrid":
        summary = await get_summary(model_id)
        window_size = max_tokens // 4
        context.append({"role": "system", "content": summary})
        context += user_messages[-window_size:] if include_history else user_messages[-1:]

    else:
        context += user_messages[-1:]

    return context