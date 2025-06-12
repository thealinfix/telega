import requests
from bs4 import BeautifulSoup

NEWS_URL = 'https://example.com/latest'

def parse_news():
    resp = requests.get(NEWS_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = []
    for tag in soup.select('.news-item'):
        title = tag.select_one('.title').get_text(strip=True)
        link = tag.select_one('a')['href']
        items.append(type('News', (), {'title': title, 'link': link}))
    return items
