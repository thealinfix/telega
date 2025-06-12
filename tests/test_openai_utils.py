import os
import httpx
import pytest
import openai
import asyncio

os.environ["OPENAI_API_KEY"] = "test"

from src import openai_utils

def test_generate_image_api_error(monkeypatch):
    async def fake_generate(*args, **kwargs):
        raise openai.APIError("boom", httpx.Request('GET', 'https://x'), body=None)
    monkeypatch.setattr(openai_utils.client.images, 'generate', fake_generate)
    with pytest.raises(openai.APIError):
        asyncio.run(openai_utils.generate_image('test'))

def test_analyze_image_connection_error(monkeypatch):
    async def fake_create(*args, **kwargs):
        raise openai.APIConnectionError(request=httpx.Request('GET', 'https://x'))
    monkeypatch.setattr(openai_utils.client.chat.completions, 'create', fake_create)
    with pytest.raises(openai.APIConnectionError):
        asyncio.run(openai_utils.analyze_image(b'test'))
