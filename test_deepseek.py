from dotenv import load_dotenv
import os, openai
load_dotenv(dotenv_path='.env', override=True)

client = openai.OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY")
)
res = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[{"role": "user", "content": "日本語で一言挨拶して"}],
    max_tokens=50
)
print(res.choices[0].message.content)
