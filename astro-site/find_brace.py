with open("astro-site/src/pages/[category].astro", "r", encoding="utf-8") as f:
    lines = f.readlines()
print(f"総行数: {len(lines)}")
for i, line in enumerate(lines, start=1):
    if "}" in line and "{" not in line and i > 80:
        print(f"{i}: {repr(line[:80])}")
