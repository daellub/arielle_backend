# backend/db/mcp_db.py
import json
import pymysql
from datetime import datetime
from typing import List, Optional
from backend.db.base import get_connection
from backend.utils.prompt_utils import apply_variables

def list_mcp_servers() -> List[dict]:
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM mcp_servers")
            return cursor.fetchall()
    finally:
        conn.close()

def get_mcp_server(alias: str) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM mcp_servers WHERE alias = %s", (alias,))
            return cursor.fetchone()
    finally:
        conn.close()

def create_mcp_server(data: dict):
    data['api_key'] = data.get('api_key', '')
    data['token'] = data.get('token', '')
    data['username'] = data.get('username', '')
    data['password'] = data.get('password', '')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO mcp_servers
                    (alias, name, endpoint, type, auth_type, api_key, token, username, password, enabled, polling_interval)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['alias'], data['name'], data['endpoint'], data['type'],
                data['auth_type'], data['api_key'], data['token'],
                data['username'], data['password'], int(data['enabled']),
                data['polling_interval']
            ))
        conn.commit()
    finally:
        conn.close()

def update_mcp_server(alias: str, fields: dict):
    if not fields:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sets = ", ".join(f"{k}=%s" for k in fields.keys())
            sql = f"UPDATE mcp_servers SET {sets} WHERE alias = %s"
            cursor.execute(sql, (*fields.values(), alias))
        conn.commit()
    finally:
        conn.close()

def delete_mcp_server(alias: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM mcp_servers WHERE alias = %s", (alias,))
        conn.commit()
    finally:
        conn.close()

def insert_mcp_log(type: str, source: str, message: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO mcp_logs (type, source, message)
                VALUES (%s, %s, %s)
            ''', (type, source, message))
        conn.commit()
    finally:
        conn.close()

def get_prompt_templates_by_ids(ids: list[int]) -> list[str]:
    if not ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            format_strings = ','.join(['%s'] * len(ids))
            cursor.execute(f'''
                SELECT template, variables FROM mcp_prompts
                WHERE id IN ({format_strings}) AND enabled = 1
            ''', ids)
            rows = cursor.fetchall()
            prompts = []
            for row in rows:
                template = row['template']
                vars = json.loads(row['variables'] or "[]")
                values = {
                    "time": datetime.now().strftime("%H:%M"),
                    "user_name": "다엘",
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                prompts.append(apply_variables(template, vars, values))
            return prompts
    finally:
        conn.close()