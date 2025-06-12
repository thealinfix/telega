import io
import json
import builtins
from src import state
from src import config


def teardown_function(function):
    state._state = None


def test_load_state_missing(monkeypatch):
    def fake_open(*args, **kwargs):
        raise FileNotFoundError
    monkeypatch.setattr(builtins, "open", fake_open)
    result = state.load_state()
    assert result == {"sent_links": [], "pending": {}, "timezone": config.DEFAULT_TIMEZONE}


def test_load_state_invalid(monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda *a, **kw: io.StringIO("invalid"))
    result = state.load_state()
    assert result == {"sent_links": [], "pending": {}, "timezone": config.DEFAULT_TIMEZONE}


def test_save_state(monkeypatch):
    class DummyFile(io.StringIO):
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            pass

    buf = DummyFile()
    def fake_open(self, mode="r", encoding=None):
        buf.seek(0)
        buf.truncate(0)
        return buf
    monkeypatch.setattr(state.Path, "open", fake_open)
    state._state = {"sent_links": ["a"], "pending": {"x": 1}, "timezone": "UTC"}
    state.save_state()
    buf.seek(0)
    data = json.load(buf)
    assert data == state._state
