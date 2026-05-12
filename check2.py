import pathlib

content = open("astro-site/src/pages/[category].astro", "r", encoding="utf-8").read()
print("現在のファイル長:", len(content))
