# backend/utils/source_loader.py
import requests
from pathlib import Path
from backend.db.database import get_connection

def load_text_from_local_sources(source_ids: list[int]) -> list[str]:
    texts = []
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT path FROM local_sources WHERE id IN (%s)
            """ % ','.join(['%s'] * len(source_ids))
            cursor.execute(sql, source_ids)
            rows = cursor.fetchall()

            for (source_id, path_str, source_type) in rows:
                if source_type == 'folder':
                    path = Path(path_str)
                    if path.exists() and path.is_dir():
                        for file in path.glob("*"):
                            if file.suffix in [".txt", ".md", ".csv", ".json"]:
                                try:
                                    content = file.read_text(encoding="utf-8")
                                    snippet = content.strip()[:1000]
                                    texts.append(f"[{file.name}]\n{snippet}")
                                except Exception as e:
                                    print(f"[파일 로딩 실패] {file}: {e}")
                elif source_type == 'database':
                    try:
                        res = requests.get(f"http://localhost:8000/api/local-sources/{source_id}/preview")
                        res.raise_for_status()
                        data = res.json()
                        for item in data.get("preview", []):
                            if all(k in item for k in ("name", "race", "role", "personality", "backstory")):
                                text = (
                                    f"{item['name']} is a {item['race']} who serves as {item['role']}. "
                                    f"They are {item['personality']}. "
                                    f"Background: {item['backstory']}"
                                )
                                texts.append(text)
                    except Exception as e:
                        print(f"[DB 소스 로딩 실패] source_id={source_id}: {e}")
    finally:
        conn.close()
    return texts