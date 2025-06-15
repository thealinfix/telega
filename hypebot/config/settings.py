"""
Configuration settings for HypeBot
"""
import os
from typing import Optional
from dataclasses import dataclass, field
import logging


@dataclass
class BotConfig:
    """Bot configuration"""
    telegram_token: str
    telegram_channel: str
    admin_chat_id: Optional[int]
    openai_api_key: str
    
    # File paths
    state_file: str = "state.json"
    
    # Intervals
    check_interval_seconds: int = 1800
    
    # Limits
    max_pending_posts: int = 100
    max_post_age_days: int = 7
    max_images_per_post: int = 10
    
    # Timezone
    default_timezone: str = "Europe/Moscow"
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Create config from environment variables"""
        telegram_token = os.getenv("TELEGRAM_TOKEN", "")
        if not telegram_token:
            raise ValueError("TELEGRAM_TOKEN is required")
            
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        admin_chat_id_str = os.getenv("ADMIN_CHAT_ID", "")
        admin_chat_id = None
        if admin_chat_id_str and admin_chat_id_str != "123456789":
            try:
                admin_chat_id = int(admin_chat_id_str)
            except ValueError:
                logging.warning(f"Invalid ADMIN_CHAT_ID: {admin_chat_id_str}")
        
        return cls(
            telegram_token=telegram_token,
            telegram_channel=os.getenv("TELEGRAM_CHAT_ID", "@channelusername"),
            admin_chat_id=admin_chat_id,
            openai_api_key=openai_api_key
        )


# Image generation styles configuration
IMAGE_STYLES = {
    "sneakers": {
        "prompt_template": "Modern minimalist sneaker promotional image, {title}, clean background, professional product photography, studio lighting, high quality, 4k",
        "style": "photographic"
    },
    "fashion": {
        "prompt_template": "Fashion editorial style image, {title}, trendy streetwear aesthetic, urban background, magazine quality",
        "style": "editorial"
    },
    "thoughts": {
        "prompt_template": "Artistic abstract representation of {topic}, modern digital art, vibrant colors, emotional expression, Instagram story format",
        "style": "artistic"
    },
    "custom": {
        "prompt_template": "{custom_prompt}",
        "style": "creative"
    }
}


# Logging configuration
def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)