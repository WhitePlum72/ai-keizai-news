with open("astro-site/src/pages/[category].astro", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }",
    "display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
)
content = content.replace(
    "display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }",
    "display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;"
)

with open("astro-site/src/pages/[category].astro", "w", encoding="utf-8", newline="\n") as f:
    f.write(content)
print("修正完了")
