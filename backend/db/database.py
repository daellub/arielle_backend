# backend/db/database.py

import json
import pymysql
import pymysql.cursors
from .config import DB_CONFIG
from datetime import datetime
from typing import List, Optional 

from backend.utils.encryption import encrypt

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def _get_logo_by_model_name(model_name: str):
    logo_map = {
        "OpenAI": "OpenAI.svg",
        "PyTorch": "PyTorch.svg",
        "Meta": "Meta.svg",
        "TensorFlow": "Tensorflow.svg",
        "Google": "Transformer.svg"
    }
    return f"/static/icons/{logo_map.get(model_name, 'default.svg')}"

# ── ASR 서버 함수 ──────────────────────────────────────────────────────

def save_result_to_db(model_name: str, text: str, language: str = 'ko'):
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO asr_records (model, transcription, language, created_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (model_name, text, language, datetime.now()))
        conn.commit()
        print("\033[94m" + "[DB] 결과가 저장되었습니다.\n")
    except Exception as e:
        print("\033[91m" + f"[ERROR] {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()

def save_model_to_db(model_id, model_info, latency=None):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO asr_models (id, name, type, framework, device, language, path, endpoint, region, apiKey, status, loaded, latency, created_at, logo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            encrypted_apiKey = encrypt(model_info.apiKey) if model_info.apiKey else None
            cursor.execute(sql, (
                model_id,
                model_info.name,
                model_info.type,
                model_info.framework,
                model_info.device,
                model_info.language,
                model_info.path,
                model_info.endpoint,
                model_info.region,
                encrypted_apiKey,
                model_info.status,
                0,  # loaded

                latency if latency else None,
                datetime.now(),
                _get_logo_by_model_name(model_info.type)
            ))
        conn.commit()
        print("\033[94m" + "[DB] 모델 정보가 저장되었습니다.\n")
    except Exception as e:
        print("\033[91m" + f"[ERROR] {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()

def delete_model_from_db(model_id: str):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "DELETE FROM asr_models WHERE id = %s"
            cursor.execute(sql, (model_id,))
        conn.commit()
        print("\033[94m" + "[DB] 모델이 삭제되었습니다.\n")
    except Exception as e:
        print("\033[91m" + f"[ERROR] {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()

def update_model_loaded_status(model_id: str, loaded: bool, latency: float = None):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                UPDATE asr_models
                SET loaded = %s, latency = %s
                WHERE id = %s
            """
            cursor.execute(sql, (int(loaded), latency, model_id))
        conn.commit()
        print("\033[94m" + "[DB] 모델 상태가 업데이트 되었습니다.\n")
    except Exception as e:
        print("\033[91m" + f"[ERROR] {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()

def update_model_status(model_id: str, status: str):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                UPDATE asr_models
                SET status = %s
                WHERE id = %s
            """
            cursor.execute(sql, (status, model_id))
        conn.commit()
        print("\033[94m" + f"[DB] 모델 상태가 '{status}로 변경되었습니다.")
    except Exception as e:
        print("\033[91m" + f"[ERROR] {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()

def get_models_from_db():
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT id, name, type, framework, device, language, path, endpoint, region, apiKey, status, loaded, latency, created_at, logo FROM asr_models
            """
            cursor.execute(sql)
            models = cursor.fetchall()
        return models  # 최신 모델 리스트 반환
    except Exception as e:
        print("\033[91m" + f"[ERROR] {e}" + "\033[0m")
        return []
    finally:
        if conn:
            conn.close()

# ── ASR 로그 저장 ──────────────────────────────────────────────────────

def save_log_to_db(log_type: str, message: str, source: str = 'SYSTEM'):
    conn = None
    try:
        print(f'[DEBUG] log_type={log_type}, source={source} ({len(source)}), message={message}')
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO asr_logs (type, source, message) VALUES (%s, %s, %s)"
            cursor.execute(sql, (log_type, source, message))
        conn.commit()
        print(f'[LOG] {log_type} | {source} | {message}')
    except Exception as e:
        print(f'[ERROR] 로그 저장 실패: {e}')
    finally:
        if conn:
            conn.close()

# ── 번역 결과 저장 ──────────────────────────────────────────────────────

def save_translation_result(client_id: str, original: str, translated: str, target_lang: str, source_type: str):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO translation_results (client_id, original, translated, target_lang, source_type, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, (client_id, original, translated, target_lang, source_type))
        conn.commit()
        print("\033[94m" + "[DB] 번역 결과가 저장되었습니다.\n")
    except Exception as e:
        print("\033[91m" + f"[ERROR] 번역 결과 저장 실패: {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()

# ── LLM 백엔드 함수 ──────────────────────────────────────────────────────

def save_llm_interaction(
    model_name: str,
    request: str,
    response: str,
    translate_response: str,
    ja_translate_response: str,
    emotion: str,
    tone: str,
) -> int:
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO llm_interactions 
                (model_name, request, response, translate_response, ja_translate_response, emotion, tone)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                model_name,
                request,
                response,
                translate_response,
                ja_translate_response,
                emotion,
                tone,
            ))
            interaction_id = cursor.lastrowid
        conn.commit()
        print("\033[94m" + "[DB] LLM interaction이 저장되었습니다.\n")
        return interaction_id
    except Exception as e:
        print("\033[91m" + f"[ERROR] LLM 저장 실패: {e}" + "\033[0m")
        return None
    finally:
        if conn:
            conn.close()

def save_llm_feedback(interaction_id: int, rating: str | None, tone_score: float):
    """
    LLM 피드백 저장 (up/down/null + tone_score)
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO llm_feedback (interaction_id, rating, tone_score)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (interaction_id, rating, tone_score))
        conn.commit()
        print("\033[94m" + "[DB] LLM 피드백이 저장되었습니다.\n")
    except Exception as e:
        print("\033[91m" + f"[ERROR] 피드백 저장 실패: {e}" + "\033[0m")
    finally:
        if conn:
            conn.close()


def get_llm_interactions(limit: int = 100):
    """
    최근 대화 이력(limit 개) 조회
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT id, model_name, request, response, created_at
                FROM llm_interactions
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    except Exception as e:
        print("\033[91m" + f"[ERROR] LLM 이력 조회 실패: {e}" + "\033[0m")
        return []
    finally:
        if conn:
            conn.close()

# ── LLM 서버 CRUD 함수 ──────────────────────────────────────────────────────

def save_llm_model_to_db(model_info):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO llm_models (name, model_key, type, framework, endpoint, status, enabled, apiKey, token, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                model_info.name,
                model_info.model_key,
                model_info.type,
                model_info.framework,
                model_info.endpoint,
                model_info.status,
                model_info.enabled,
                model_info.apiKey if model_info.apiKey else None,
                model_info.token if model_info.token else None,
                datetime.now()
            ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print("\033[91m" + f"[ERROR] LLM 모델 저장 실패: {e}" + "\033[0m")
        raise
    finally:
        if conn:
            conn.close()

def get_llm_models_from_db():
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT id, model_key, name, type, framework, endpoint, status, enabled, apiKey, token FROM llm_models"
            cursor.execute(sql)
            models = cursor.fetchall()
            return models
    except Exception as e:
        print("\033[91m" + f"[ERROR] LLM 모델 조회 실패: {e}" + "\033[0m")
        return []
    finally:
        if conn:
            conn.close()

def get_llm_model_by_id(model_id: int) -> Optional[dict]:
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT id, name, model_key, endpoint, enabled, framework, type, params
                FROM llm_models
                WHERE id = %s
            """
            cursor.execute(sql, (model_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"[ERROR] LLM 모델 단일 조회 실패: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_llm_model_in_db(model_id: int, model_info):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            data = model_info.model_dump(exclude_unset=True)

            if not data:
                return
            
            fields = []
            values = []
            for key, value in data.items():
                fields.append(f"{key} = %s")
                values.append(value)
            
            values.append(model_id)
            sql = f"UPDATE llm_models SET {', '.join(fields)} WHERE id = %s"

            cursor.execute(sql, values)
            
        conn.commit()
    except Exception as e:
        print(f"[ERROR] 모델 상태 업데이트 실패: {e}")
        raise
    finally:
        if conn:
            conn.close()

def delete_llm_model_from_db(model_id: int):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "DELETE FROM llm_models WHERE id = %s"
            cursor.execute(sql, (model_id,))
        conn.commit()
    except Exception as e:
        print(f"[ERROR] 모델 삭제 실패: {e}")
        raise
    finally:
        if conn:
            conn.close()

def update_llm_model_params(model_id: int, params: dict):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE llm_models SET params = %s WHERE id = %s", (json.dumps(params), model_id))
        conn.commit()
    finally:
        conn.close()

# ── MCP 서버 CRUD 함수 ──────────────────────────────────────────────────────

def list_mcp_servers() -> List[dict]:
    """
    등록된 MCP 서버 목록 조회
    반환: alias, name, endpoint, type, auth_type, enabled, polling_interval 등 전체 컬럼
    """
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM mcp_servers")
            return cursor.fetchall()
    finally:
        conn.close()

def get_mcp_server(alias: str) -> Optional[dict]:
    """
    특정 MCP 서버 조회
    """
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM mcp_servers WHERE alias = %s", (alias,))
            return cursor.fetchone()
    finally:
        conn.close()

def create_mcp_server(data: dict):
    """
    새 MCP 서버 등록
    data: {'alias','name','endpoint','type','auth_type','api_key','token','username','password','enabled','polling_interval'}
    """
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
                data['alias'],
                data['name'],
                data['endpoint'],
                data['type'],
                data['auth_type'],
                data['api_key'],
                data['token'],
                data['username'],
                data['password'],
                int(data['enabled']),
                data['polling_interval']
            ))
        conn.commit()
    finally:
        conn.close()

def update_mcp_server(alias: str, fields: dict):
    """
    MCP 서버 정보 업데이트
    fields에는 변경할 컬럼명:값 쌍만 담아서 넘겨주세요.
    """
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
    """
    MCP 서버 삭제
    """
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

# ── MCP 파라미터 ──────────────────────────────────────────────────────
def get_prompt_templates_by_ids(ids: list[int]) -> list[str]:
    from ..utils.prompt_utils import apply_variables
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if not ids:
                return []
            format_strings = ','.join(['%s'] * len(ids))
            cursor.execute(f"""
                SELECT template, variables FROM mcp_prompts
                WHERE id IN ({format_strings}) AND enabled = 1
            """, ids)
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
