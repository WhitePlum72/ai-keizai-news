import requests
from bs4 import BeautifulSoup

url = "https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(res.text, 'html.parser')
og_image = soup.find('meta', property='og:image')
print("OGP画像:", og_image.get('content', '未取得') if og_image else '未取得')