# backend/llm/services/prompt_builder.py

import re
from datetime import datetime
from pathlib import Path
from backend.utils.prompt_utils import apply_variables
from backend.db.mcp_db import get_prompt_templates_by_ids

def load_default_prompt() -> str:
    return Path("backend/llm/prompt/arielle_prompt.txt").read_text(encoding="utf-8")

def extract_variables(template: str) -> list[str]:
    return re.findall(r"\{([\w_]+)\}", template)

def resolve_variables(vars: list[str]) -> dict:
    now = datetime.now()
    return {
        var: (
            now.strftime("%H:%M") if var == "time" else
            now.strftime("%Y-%m-%d") if var == "date" else
            "Dael" if var == "user_name" else f"<{var}>"
        ) for var in vars
    }

def build_system_prompt(params: dict) -> str:
    prompt_ids = params.get("prompts", [])
    manual_prompt = params.get("prompt", "").strip()

    if manual_prompt:
        system_prompt = manual_prompt
    elif prompt_ids:
        template_prompts = get_prompt_templates_by_ids(prompt_ids)
        system_prompt = "\n\n".join(template_prompts)
    else:
        system_prompt = load_default_prompt()

    vars = extract_variables(system_prompt)
    system_prompt = apply_variables(system_prompt, vars, resolve_variables(vars))

    return system_prompt
