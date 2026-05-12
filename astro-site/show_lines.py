with open("astro-site/src/pages/[category].astro", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[80:95], start=81):
    print(f"{i}: {repr(line)}")
