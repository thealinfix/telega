import logging
import base64
import httpx
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI
from . import config

openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

async def generate_image(prompt: str, style: str = "photographic") -> str | None:
    try:
        logging.info(f"Генерирую изображение: {prompt[:50]}...")
        response = await openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        logging.error(f"Ошибка при генерации изображения: {e}")
        return None

async def download_image(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logging.error(f"Ошибка при скачивании изображения: {e}")
        return None

async def analyze_image(image_bytes: bytes) -> str:
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = await openai_client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Опиши что изображено на этой картинке"
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка при анализе изображения: {e}")
        return ""