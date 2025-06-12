from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from requests import RequestException

NEWS_URL = 'https://example.com/latest'


@dataclass
class News:
    title: str
    link: str

def parse_news():
    try:
        resp = requests.get(NEWS_URL)
        resp.raise_for_status()
    except RequestException:
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    items = []
    for tag in soup.select('.news-item'):
        title = tag.select_one('.title').get_text(strip=True)
        link = tag.select_one('a')['href']
        items.append(News(title=title, link=link))
    return items
