# backend/asr/models.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from huggingface_hub import list_repo_files, hf_hub_url
import requests, time, os, anyio
from backend.sio import sio
from threading import Event

router = APIRouter(prefix="/models")
CACHE_DIR = os.getenv("HF_CACHE_DIR", "./.hf_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

download_cancel_flags = {}

class DownloadRequest(BaseModel):
    model_id: str

def get_directory_size(directory):
    total = 0
    for path, dirs, files in os.walk(directory):
        for f in files:
            fp = os.path.join(path, f)
            total += os.path.getsize(fp)
    return total

@router.post("/cancel-download")
async def cancel_download(req: DownloadRequest):
    download_cancel_flags[req.model_id] = True
    return {"status": "cancel_requested"}

@router.post("/download-model")
async def download_model(req: DownloadRequest):
    repo_id = req.model_id
    download_cancel_flags[repo_id] = False
    try:
        files = await anyio.to_thread.run_sync(list_repo_files, repo_id)
        total_files = len(files)

        for idx, filename in enumerate(files, start=1):
            if download_cancel_flags.get(repo_id):
                print(f"⛔️ 다운로드 취소됨: {repo_id}")
                return {"status": "cancelled"}

            await sio.emit('hf_download_progress', {
                'model_id': repo_id,
                'file': filename,
                'index': idx,
                'total': total_files,
                'phase': 'start'
            })
            
            url = hf_hub_url(repo_id, filename)
            local_dir = os.path.join(CACHE_DIR, repo_id)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, filename)

            resp = requests.get(url, stream=True)
            resp.raise_for_status()
            total_bytes = int(resp.headers.get("content-length", 0))
            downloaded = 0
            start_time = time.time()

            with open(local_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if download_cancel_flags.get(repo_id):
                        raise Exception("Download canceled by user")
                    
                    f.write(chunk)
                    downloaded += len(chunk)

                    await sio.emit("hf_download_progress", {
                        "model_id": repo_id,
                        "file": filename,
                        "index": idx,
                        "total": total_files,
                        "phase": "chunk",
                        "loaded": downloaded,
                        "total_bytes": total_bytes
                    })

            duration = time.time() - start_time
            size_bytes = total_bytes
            safe_duration = duration if duration > 0 else 1e-6
            speed_mbps = (size_bytes / safe_duration) / (1024 * 1024)

            await sio.emit("hf_download_progress", {
                "model_id": repo_id,
                "file": filename,
                "index": idx,
                "total": total_files,
                "phase": "end",
                "size_bytes": size_bytes,
                "speed_mbps": speed_mbps
            })

        model_dir = os.path.abspath(os.path.join(CACHE_DIR, repo_id))
        total_size = get_directory_size(model_dir)

        download_cancel_flags.pop(repo_id, None)

        await sio.emit('hf_download_complete', {
            'model_id': repo_id,
            'path': model_dir,
            'total_size_bytes': total_size
        })
        return {'path': 'done'}
    except Exception as e:
        print(f"[ERROR] 다운로드 실패 또는 취소: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        download_cancel_flags.pop(repo_id, None)