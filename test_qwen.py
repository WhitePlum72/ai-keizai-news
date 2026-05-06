import openai

client = openai.OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dummy"
)

response = client.chat.completions.create(
    model="Qwen3.6-27B-UD-Q4_K_XL.gguf",
    messages=[{"role": "user", "content": "テストです。一言返してください"}],
    max_tokens=200,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}}
)

print("応答:", response.choices[0].message.content)
print("トークン数:", response.usage.completion_tokens)