# backend/llm/services/tool_executor.py

import re
import ast
from urllib.parse import quote
import httpx

def is_safe_math_expr(expr: str) -> bool:
    try:
        parsed = ast.parse(expr, mode='eval')
        allowed = (
            ast.Expression, ast.BinOp, ast.UnaryOp,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
            ast.Num, ast.Constant, ast.UAdd, ast.USub, ast.Load,
            ast.Expr, ast.Call, ast.Name
        )
        return all(isinstance(node, allowed) for node in ast.walk(parsed))
    except:
        return False

def evaluate_math_expr(expr: str) -> str:
    try:
        if not is_safe_math_expr(expr):
            return "Error: Unsafe expression"
        result = str(eval(expr))
        return result
    except Exception as e:
        return f"Error: {e}"

def extract_math_expr(text: str) -> str | None:
    matches = re.findall(r'[\(]?[0-9\.\s\+\-\*/\^()]+[\)]?', text)
    for expr in matches:
        cleaned = expr.strip().replace("^", "**")
        if ' - ' in cleaned:
            continue
        if any(op in cleaned for op in ['+', '-', '*', '/', '**']):
            return cleaned
    return None

def extract_weather_expr(text: str) -> str | None:
    match = re.search(r'\\b(?:weather|forecast)\\s+(?:in\\s+)?([A-Za-z\\s]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_search_query(text: str) -> str | None:
    match = re.search(r'\\b(?:search|find|look\\s+up)\\s+(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_spotify_query(text: str) -> str | None:
    match = re.search(r'\\bplay\\s+(.+?)\\s+(?:on|with)\\s+spotify\\b', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_spotify_command(text: str) -> dict | None:
    text = text.lower()
    if re.search(r'\\b(pause|stop)\\b.*(music|song)?', text): return {"action": "pause"}
    if re.search(r'\\b(resume|continue)\\b.*(music|song)?', text): return {"action": "play"}
    if re.search(r'\\b(skip|next)\\b.*(track|song|music)?', text): return {"action": "next"}
    if re.search(r'\\b(previous|back)\\b.*(track|song)?', text): return {"action": "previous"}
    if re.search(r'\\b(volume\\s+up|turn\\s+up\\s+the\\s+volume|increase\\s+volume)\\b', text): return {"action": "volume_up"}
    if re.search(r'\\b(volume\\s+down|turn\\s+down\\s+the\\s+volume|decrease\\s+volume)\\b', text): return {"action": "volume_down"}
    return None
