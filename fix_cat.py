with open("astro-site/src/pages/[category].astro", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "-webkit-box-orient: vertical; overflow: hidden; }",
    "-webkit-box-orient: vertical; overflow: hidden; \}"
)

with open("astro-site/src/pages/[category].astro", "w", encoding="utf-8", newline="\n") as f:
    f.write(content)
print("修正完了")
