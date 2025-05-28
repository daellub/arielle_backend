# backend/db/llm_db.py
import json
import pymysql
from datetime import datetime
from typing import Optional
from backend.db.base import get_connection

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
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
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
        with get_connection().cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT id, model_key, name, type, framework, endpoint, status, enabled, apiKey, token
                FROM llm_models
            """
            cursor.execute(sql)
            return cursor.fetchall()
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
        with conn.cursor() as cursor:
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