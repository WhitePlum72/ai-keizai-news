import openai

client = openai.OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-523269ebbe734797948432db9eecf42c"
)
try:
    res = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": "日本語で一言挨拶して"}],
        max_tokens=50
    )
    print(res.choices[0].message.content)
except Exception as e:
    print(f"エラー: {e}")
