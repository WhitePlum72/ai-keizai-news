f = open('astro-site/src/pages/article/[category]/[slug].astro', encoding='utf-8')
content = f.read()
f.close()

old = "const ogImage = article.data.image_url || 'https://aikeizai.jp/ogp.png';"
new = "const ogImage = article.data.image_url ? (article.data.image_url.startsWith('http') ? article.data.image_url : 'https://aikeizai.jp' + article.data.image_url) : 'https://aikeizai.jp/ogp.png';"

if old in content:
    content = content.replace(old, new)
    f = open('astro-site/src/pages/article/[category]/[slug].astro', 'w', encoding='utf-8', newline='\n')
    f.write(content)
    f.close()
    print('修正完了')
else:
    print('対象文字列が見つかりません')
