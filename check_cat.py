with open("astro-site/src/pages/[category].astro", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[85:100], start=86):
    print(f"{i}: {line}", end="")
