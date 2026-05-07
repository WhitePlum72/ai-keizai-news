import openai

client = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

title = "Musk's Lawyer Pushes OpenAI's Brockman to Give Back $29 Billion"
summary = "OpenAI co-founder and President Greg Brockman testified that his stake in the startup is now worth almost $30 billion, prompting an attorney for Elon Musk to ask why he had not donated the bulk of his wealth to the nonprofit that controls OpenAI."

prompt = f"""あなたはITmedia・Bloomberg・日経クロステック級の日本人経済記者だ。
以下のニュース情報を元に、高品質な日本語経済ニュース記事を生成せよ。

【元記事情報】
タイトル: {title}
内容: {summary}

【絶対ルール】
・1行目: タイトル（32〜42文字、重要ワードを前半に、誇張禁止）
・2行目: 空行
・本文1200〜1800文字
・だ・である調
・マークダウン禁止
・機械翻訳調禁止
・同じ論点の繰り返し禁止

【本文構成】
1. リード文（2〜3文、最重要ポイントを最初に提示）
2. 何が起きたか（具体的な数字・固有名詞を含める）
3. なぜ今重要なのか（業界・市場への影響）
4. 背景と競合状況（他社との比較・業界構造）
5. 投資家・企業戦略視点での考察
6. 今後の展望（抽象論禁止・具体的な予測）

【品質基準】
・数字・固有名詞・企業名を積極的に使う
・「今後の動向に注目です」等の締めは禁止
・日本市場・日本企業への影響を必ず1箇所含める"""

res = client.chat.completions.create(
    model="deepseek-ai/deepseek-v4-pro",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=2500
)
print(res.choices[0].message.content)