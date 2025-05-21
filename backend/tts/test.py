import requests

url = "http://210.183.228.222:5000/voice"

params = {
    "text": "おはよう、今日もがんばろう！",
    "model_id": 0,
    "speaker_id": 0,
    "style": "Neutral",
    "language": "JP"
}

response = requests.post(url, params=params)

if response.status_code == 200:
    with open("reika_test.wav", "wb") as f:
        f.write(response.content)
    print("✅ 저장 완료: reika_test.wav")
else:
    print("❌ 오류 발생:", response.status_code, response.text)
