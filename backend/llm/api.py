# backend/llm/api.py
import requests
from sseclient import SSEClient
from pathlib import Path
import json
import re

def load_prompt(path='backend\\llm\\prompt\\arielle_prompt.txt'):
    return Path(path).read_text(encoding='utf-8')

def remove_stage_directions(text: str) -> str:
    return re.sub(r'\*.*?\*', '', text).strip()

def stream_talk_to_arielle(user_input: str):
    headers={
        "Content-Type": "application/json"
    }
    payload={
        "model": "arielle-q6",
        "messages": [
            {"role": "system", "content": load_prompt()},
            {"role": "user", "content": user_input}
        ],
        "max_tokens": 96,
        "stop": ["User:"],
        "stream": True
    }

    print('Arielle: ', end='', flush=True)

    try:
        response = requests.post('http://localhost:8080/v1/chat/completions', headers=headers, json=payload, stream=True)
        client = SSEClient(response)

        full_text = ''

        for event in client.events():
            # print(f"[DEBUG] event: {event.data}")
            if event.data == '[DONE]':
                break

            data = json.loads(event.data)
            delta = data['choices'][0]['delta'].get('content', '')
            full_text += delta
            print(delta, end='', flush=True)

        print('\n')
        return remove_stage_directions(full_text.strip())
    except Exception as e:
        print(f'\nError: {e}')
        return None
    
if __name__ == "__main__":
    while True:
        query = input("You: ")
        if query.lower() in ["exit", "quit"]: break
        _ = stream_talk_to_arielle(query)
