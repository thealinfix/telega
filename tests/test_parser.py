from src.utils import parser

class DummyResponse:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass

    def raise_for_status(self):
        pass

def test_parse_news(monkeypatch):
    html = """
    <div class='news-item'><span class='title'>First</span><a href='https://ex/1'>a</a></div>
    <div class='news-item'><span class='title'>Second</span><a href='/2'>a</a></div>
    """
    def fake_get(url):
        return DummyResponse(html)
    monkeypatch.setattr(parser.requests, "get", fake_get)
    items = parser.parse_news()
    assert len(items) == 2
    assert items[0].title == "First"
    assert items[0].link == "https://ex/1"
    assert items[1].title == "Second"
    assert items[1].link == "/2"
