import feedparser

keywords = [
    'ai', 'ml', 'llm', 'gpt', 'model', 'language', 'neural', 'learning',
    'openai', 'anthropic', 'llama', 'agent', 'claude', 'gemini'
]

feed = feedparser.parse('https://news.ycombinator.com/rss')
print('HN全件数:', len(feed.entries))

matched = [e.title for e in feed.entries if any(k in e.title.lower() for k in keywords)]
print('マッチ件数:', len(matched))
for t in matched:
    print(t)