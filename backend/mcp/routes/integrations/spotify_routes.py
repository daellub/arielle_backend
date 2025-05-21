# backend/mcp/routes/integrations/spotify_routes.py
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import os, requests

router = APIRouter(prefix="/integrations")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

access_token = None

@router.get("/spotify/login")
async def login():
    scope = "user-modify-playback-state user-read-playback-state"
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?client_id={SPOTIFY_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        f"&scope={scope}"
    )
    return RedirectResponse(auth_url)

@router.get("/spotify/callback")
async def callback(code: str = Query(...)):
    global access_token
    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(token_url, data=payload, headers=headers)
    if res.status_code == 200:
        access_token = res.json().get("access_token")
        return HTMLResponse(content="""
            <html>
                <body style="background: #1a1a1a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh;">
                    <div>
                        <h3>✅ Spotify 로그인 완료</h3>
                        <p>잠시 후 창이 닫힙니다...</p>
                        <script>
                            setTimeout(() => {
                                window.opener?.postMessage({ type: 'spotify-login', success: true }, '*')
                                window.close()
                            }, 300)
                        </script>
                    </div>
                </body>
            </html>
        """)
    return {"error": res.text}

@router.get("/spotify/devices")
async def get_devices():
    global access_token
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get("https://api.spotify.com/v1/me/player/devices", headers=headers)
    return res.json()

@router.post("/spotify/play")
async def play(track_uri: str = Query(...), device_id: str = Query(None)):
    global access_token
    if not access_token:
        return {"error": "Spotify 인증 안됨"}
    headers = {"Authorization": f"Bearer {access_token}"}
    body = {"uris": [track_uri]}
    params = {"device_id": device_id} if device_id else {}
    res = requests.put("https://api.spotify.com/v1/me/player/play", headers=headers, json=body, params=params)
    return {"status": res.status_code, "result": res.json() if res.content else "No content"}

@router.post("/spotify/execute")
async def execute_spotify_action(request: Request):
    global access_token
    data = await request.json()
    action = data.get("action")
    query = data.get("query")
    device_id = data.get("device_id")

    if not access_token:
        return {"error": "Spotify 인증 안됨"}
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    if action == "play" and query:
        headers = {"Authorization": f"Bearer {access_token}"}
        search_res = requests.get(
            "https://api.spotify.com/v1/search",
            headers=headers,
            params={"q": query, "type": "track", "limit": 1}
        )

        if search_res.status_code != 200:
            return {"error": "Spotify 검색 실패", "details": search_res.text}

        tracks = search_res.json().get("tracks", {}).get("items", [])
        if not tracks:
            return {"error": f"No track found for '{query}'"}

        track_uri = tracks[0]["uri"]


        body = {"uris": [track_uri]}
        params = {"device_id": device_id} if device_id else {}

        play_res = requests.put(
            "https://api.spotify.com/v1/me/player/play",
            headers=headers,
            json=body,
            params=params
        )

        return {
            "track": tracks[0]["name"],
            "artist": tracks[0]["artists"][0]["name"],
            "uri": track_uri,
            "status": play_res.status_code,
            "result": play_res.json() if play_res.content else "No content"
        }
    
    elif action == "pause":
        res = requests.put("https://api.spotify.com/v1/me/player/pause", headers=headers)
        
        if res.status_code == 204:
            return {"status": 204, "message": "Paused"}
        
        try:
            data = res.json()
        except Exception:
            data = {}
        
        return {"status": res.status_code, "result": data, "message": data.get("message", "Paused")}

    elif action == "next":
        res = requests.post("https://api.spotify.com/v1/me/player/next", headers=headers)
        return {
            "status": res.status_code,
            "message": "Skipped to next track"
        }


    elif action == "previous":
        res = requests.post("https://api.spotify.com/v1/me/player/previous", headers=headers)
        return {
            "status": res.status_code,
            "message": "Reverted to previous track"
        }

    elif action == "volume_up" or action == "volume_down":
        devices = requests.get("https://api.spotify.com/v1/me/player/devices", headers=headers).json()
        active = next((d for d in devices["devices"] if d["is_active"]), None)
        if not active:
            return {"error": "No active device"}
        
        current_volume = active["volume_percent"]
        new_volume = current_volume + 10 if action == "volume_up" else current_volume - 10
        new_volume = max(0, min(100, new_volume))

        res = requests.put(
            f"https://api.spotify.com/v1/me/player/volume?volume_percent={new_volume}",
            headers=headers
        )
        return {"status": res.status_code, "result": f"Volume set to {new_volume}%"}

    return {"error": "지원하지 않는 action입니다"}

@router.get("/spotify/status")
async def spotify_status():
    if access_token:
        return {"logged_in": True}
    return {"logged_in": False}

@router.get("/spotify/healthz")
async def spotify_healthz():
    from fastapi.responses import JSONResponse

    if access_token:
        return JSONResponse(content={"status": "ok", "message": "Spotify connected"}, status_code=200)
    else:
        return JSONResponse(content={"status": "unavailable", "message": "Not logged in"}, status_code=503)
