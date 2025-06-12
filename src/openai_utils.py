import base64
import logging
from openai import AsyncOpenAI

from .config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_image(prompt: str, style: str = "photographic") -> str:
    """Generate an image with DALL·E."""
    logging.info("Generating image via OpenAI")
    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="standard",
    )
    return response.data[0].url


async def analyze_image(image_bytes: bytes) -> str:
    """Analyze an image with GPT-4 Vision."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
            },
        ],
    }
    resp = await client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[message],
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()
