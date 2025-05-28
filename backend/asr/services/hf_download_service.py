# backend/asr/services/hf_download_service.py

import os, time, requests, anyio
from huggingface_hub import list_repo_files, hf_hub_url

CACHE_DIR = os.getenv("HF_CACHE_DIR", "./.hf_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

download_cancel_flags = {}

def cancel_download(model_id: str):
    download_cancel_flags[model_id] = True

def is_canceled(model_id: str):
    return download_cancel_flags.get(model_id, False)

def clear_flag(model_id: str):
    download_cancel_flags.pop(model_id, None)

def get_directory_size(directory):
    total = 0
    for path, _, files in os.walk(directory):
        for f in files:
            total += os.path.getsize(os.path.join(path, f))
    return total

async def download_model(repo_id: str, sio):
    download_cancel_flags[repo_id] = False
    files = await anyio.to_thread.run_sync(list_repo_files, repo_id)
    total_files = len(files)

    for idx, filename in enumerate(files, start=1):
        if is_canceled(repo_id):
            raise Exception("Download canceled by user")

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
                if is_canceled(repo_id):
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
        speed_mbps = (total_bytes / duration) / (1024 * 1024) if duration > 0 else 0

        await sio.emit("hf_download_progress", {
            "model_id": repo_id,
            "file": filename,
            "index": idx,
            "total": total_files,
            "phase": "end",
            "size_bytes": total_bytes,
            "speed_mbps": speed_mbps
        })

    model_dir = os.path.abspath(os.path.join(CACHE_DIR, repo_id))
    total_size = get_directory_size(model_dir)

    clear_flag(repo_id)

    await sio.emit('hf_download_complete', {
        'model_id': repo_id,
        'path': model_dir,
        'total_size_bytes': total_size
    })

    return model_dir