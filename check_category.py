with open("astro-site/src/pages/[category].astro", "r", encoding="utf-8") as f:
    content = f.read()
print("ファイル長:", len(content))
print("canonical あり:", "canonical" in content)
print("getArticleUrl スラッシュあり:", "slug}/`" in content)
