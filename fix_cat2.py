with open("astro-site/src/pages/[category].astro", "r", encoding="utf-8") as f:
    content = f.read()

# is:global を追加
content = content.replace("<style>", "<style is:global>")

with open("astro-site/src/pages/[category].astro", "w", encoding="utf-8", newline="\n") as f:
    f.write(content)
print("修正完了")
