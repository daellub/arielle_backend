# backend/llm/services/context_manager.py

from backend.llm.memory.context_builder import build_context
from backend.utils.source_loader import load_text_from_local_sources

async def build_llm_context(model_id, system_prompt, user_messages, memory_settings):
    return await build_context(
        model_id=model_id,
        system_prompt=system_prompt,
        user_messages=user_messages,
        memory_settings=memory_settings
    )

def append_local_sources(context: list[dict], source_ids: list[int]) -> None:
    if not source_ids:
        return

    texts = load_text_from_local_sources(source_ids)

    print(f"[📁 로컬 소스 ID 목록]: {source_ids}")
    print(f"[📁 로컬 소스 참고 문서 수]: {len(texts)}개")

    for idx, text in enumerate(texts):
        header = text.split('\\n')[0] if '\\n' in text else text[:50]
        print(f"[📄 문서 {idx+1}] 헤더: {header}")

    for text in texts:
        role_intro = "This is character information:" if " is a " in text else "This is background knowledge:"
        context.append({
            "role": "system",
            "content": f"{role_intro}\\n{text[:500]}"
        })
