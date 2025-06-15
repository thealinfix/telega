"""
AI service for text and image generation
"""
import base64
import logging
from typing import Optional, List
from openai import AsyncOpenAI

from ..config.settings import BotConfig, IMAGE_STYLES
from ..config.constants import CAPTION_SYSTEM_PROMPT, THOUGHTS_SYSTEM_PROMPT, OPENAI_MODELS


class AIService:
    """Service for OpenAI interactions"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
    
    async def generate_caption(
        self,
        title: str,
        context: str,
        category: str = "sneakers",
        is_thought: bool = False,
        image_description: str = ""
    ) -> str:
        """Generate caption for post"""
        if is_thought:
            return await self._generate_thought(title, image_description)
        else:
            return await self._generate_post_caption(title, context, category)
    
    async def _generate_thought(self, topic: str, image_description: str = "") -> str:
        """Generate thought-style post"""
        system_prompt = THOUGHTS_SYSTEM_PROMPT
        
        if image_description:
            user_prompt = (
                f"Напиши пост-размышление на основе изображения и темы.\n"
                f"Тема: {topic}\n"
                f"Описание изображения: {image_description}"
            )
        else:
            user_prompt = f"Напиши пост-размышление о: {topic}"
        
        return await self._generate_with_fallback(
            system_prompt,
            user_prompt,
            temperature=0.9,
            max_tokens=300,
            default_response=f"💭 {topic}\n\nИнтересная тема для размышлений!"
        )
    
    async def _generate_post_caption(self, title: str, context: str, category: str) -> str:
        """Generate regular post caption"""
        system_prompt = CAPTION_SYSTEM_PROMPT
        user_prompt = (
            f"Заголовок: {title}\n"
            f"Детали: {context[:500] if context else 'Нет информации'}"
        )
        
        caption = await self._generate_with_fallback(
            system_prompt,
            user_prompt,
            temperature=0.8,
            max_tokens=300,
            default_response=f"🔥 Новый релиз. Подробности скоро!"
        )
        
        # Add title if not present
        if title.lower() not in caption.lower():
            caption = f"<b>{title}</b>\n\n{caption}"
        
        return caption
    
    async def _generate_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: int = 300,
        default_response: str = ""
    ) -> str:
        """Generate text with model fallback"""
        for model in OPENAI_MODELS:
            try:
                logging.info(f"Generating with model {model}")
                
                response = await self.client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                )
                
                generated = response.choices[0].message.content.strip()
                if generated:
                    logging.info(f"Successfully generated with {model}")
                    return generated
                    
            except Exception as e:
                logging.error(f"Error with model {model}: {type(e).__name__}: {str(e)}")
                continue
        
        logging.error("All models failed, using default response")
        return default_response
    
    async def generate_image(self, prompt: str, style: str = "photographic") -> Optional[str]:
        """Generate image using DALL-E 3"""
        try:
            logging.info(f"Generating image: {prompt[:50]}...")
            
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logging.info("Image generated successfully")
            return image_url
            
        except Exception as e:
            logging.error(f"Error generating image: {e}")
            return None
    
    async def analyze_image(self, image_bytes: bytes) -> str:
        """Analyze image using GPT-4 Vision"""
        try:
            # Convert to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            response = await self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Опиши что изображено на этой картинке. "
                                    "Особое внимание удели деталям, цветам, стилю. "
                                    "Если это кроссовки или одежда - опиши модель, бренд, особенности дизайна."
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error analyzing image: {e}")
            return ""
    
    def get_image_prompt(self, title: str, style_key: str = "sneakers", custom_prompt: str = None) -> str:
        """Get prompt for image generation"""
        if custom_prompt:
            return custom_prompt
        
        style_config = IMAGE_STYLES.get(style_key, IMAGE_STYLES["sneakers"])
        
        if style_key == "custom":
            return style_config["prompt_template"].format(custom_prompt=custom_prompt or title)
        elif style_key == "thoughts":
            return style_config["prompt_template"].format(topic=title)
        else:
            return style_config["prompt_template"].format(title=title)