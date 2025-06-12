import unittest
from unittest.mock import patch, Mock
import requests

from src.utils.parser import parse_news, News

class ParseNewsTests(unittest.TestCase):
    @patch('src.utils.parser.requests.get')
    def test_parse_news_success(self, mock_get):
        html = (
            "<div class='news-item'><span class='title'>Title1</span><a href='link1'></a></div>"
            "<div class='news-item'><span class='title'>Title2</span><a href='link2'></a></div>"
        )
        mock_resp = Mock(status_code=200, text=html)
        mock_get.return_value = mock_resp

        items = parse_news()
        self.assertEqual(items, [
            News(title='Title1', link='link1'),
            News(title='Title2', link='link2')
        ])

    @patch('src.utils.parser.requests.get')
    def test_parse_news_error(self, mock_get):
        mock_get.side_effect = requests.RequestException
        items = parse_news()
        self.assertEqual(items, [])

if __name__ == '__main__':
    unittest.main()
