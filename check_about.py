with open("astro-site/src/pages/about.astro", "r", encoding="utf-8") as f:
    content = f.read()
print("ファイル長:", len(content))
print("免責事項あり:", "免責事項" in content)
print("ミッションあり:", "ミッション" in content)
