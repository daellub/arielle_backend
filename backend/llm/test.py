import requests

res = requests.post("http://localhost:8000/llm/chat", json={
    "messages": [
        {"role": "user", "content": "Who are you?"}
    ]
})

print(res.status_code)
print(res.json())
