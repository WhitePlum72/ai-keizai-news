import requests
import json

url = "https://api.deepseek.com/chat/completions"
headers = {
    "Authorization": "Bearer sk-523269ebbe734797948432db9eecf42c",
    "Content-Type": "application/json"
}
body = {
    "model": "deepseek-v4-pro",
    "messages": [{"role": "user", "content": "日本語で一言挨拶して"}],
    "max_tokens": 50
}

try:
    res = requests.post(url, headers=headers, json=body, timeout=30)
    print(f"ステータス: {res.status_code}")
    print(res.text[:500])
except Exception as e:
    print(f"エラー: {e}")