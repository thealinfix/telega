# hypebot/__init__.py
"""
HypeBot - Modern Telegram bot for monitoring sneaker and fashion releases
"""

__version__ = "2.0.0"
__author__ = "HypeBot Team"

# hypebot/config/__init__.py
"""
Configuration modules
"""

from .settings import BotConfig, IMAGE_STYLES, setup_logging
from .constants import (
    HASHTAGS, BRAND_KEYWORDS, MODEL_KEYWORDS, RELEASE_TYPES,
    SOURCE_EMOJIS, AVAILABLE_TIMEZONES, COLOR_KEYWORDS,
    VALID_IMAGE_EXTENSIONS, OPENAI_MODELS,
    CAPTION_SYSTEM_PROMPT, THOUGHTS_SYSTEM_PROMPT
)
from .sources import SOURCES, DEFAULT_HEADERS, SNEAKER_KEYWORDS

__all__ = [
    'BotConfig', 'IMAGE_STYLES', 'setup_logging',
    'HASHTAGS', 'BRAND_KEYWORDS', 'MODEL_KEYWORDS', 'RELEASE_TYPES',
    'SOURCE_EMOJIS', 'AVAILABLE_TIMEZONES', 'COLOR_KEYWORDS',
    'VALID_IMAGE_EXTENSIONS', 'OPENAI_MODELS',
    'CAPTION_SYSTEM_PROMPT', 'THOUGHTS_SYSTEM_PROMPT',
    'SOURCES', 'DEFAULT_HEADERS', 'SNEAKER_KEYWORDS'
]

# hypebot/models/__init__.py
"""
Data models
"""

from .post import Post, PostTags, ThoughtPost
from .schedule import ScheduledPost
from .state import BotState, PreviewMode, WaitingState

__all__ = [
    'Post', 'PostTags', 'ThoughtPost',
    'ScheduledPost',
    'BotState', 'PreviewMode', 'WaitingState'
]

# hypebot/services/__init__.py
"""
Service modules
"""

from .state_manager import StateManager
from .ai_service import AIService
from .image_service import ImageService
from .publisher import PublisherService
from .fetcher import ContentFetcher
from .tag_extractor import TagExtractor

__all__ = [
    'StateManager', 'AIService', 'ImageService',
    'PublisherService', 'ContentFetcher', 'TagExtractor'
]

# hypebot/handlers/__init__.py
"""
Handler modules
"""

from .base import BaseHandler
from .commands import CommandHandler
from .messages import MessageHandler
from .callbacks import CallbackHandler
from .menu import MenuHandler
from .preview import PreviewHandler

__all__ = [
    'BaseHandler', 'CommandHandler', 'MessageHandler',
    'CallbackHandler', 'MenuHandler', 'PreviewHandler'
]

# hypebot/utils/__init__.py
"""
Utility modules
"""

from .validators import (
    is_valid_image_url, is_valid_channel, is_admin,
    validate_time_format, validate_post_data,
    sanitize_filename, is_url_suspicious
)

from .time_utils import (
    get_user_timezone, localize_datetime, format_local_time,
    format_date_for_display, parse_schedule_time,
    parse_date_from_rss, is_post_old, get_time_until
)

from .formatters import (
    format_tags_for_display, get_hashtags_for_post,
    format_post_for_channel, format_preview_text,
    format_moderation_text, truncate_text, escape_html,
    format_stats_text, format_scheduled_post_info
)

from .decorators import (
    admin_only, log_errors, with_typing_action,
    answer_callback_query, require_args, rate_limit
)

__all__ = [
    # validators
    'is_valid_image_url', 'is_valid_channel', 'is_admin',
    'validate_time_format', 'validate_post_data',
    'sanitize_filename', 'is_url_suspicious',
    
    # time_utils
    'get_user_timezone', 'localize_datetime', 'format_local_time',
    'format_date_for_display', 'parse_schedule_time',
    'parse_date_from_rss', 'is_post_old', 'get_time_until',
    
    # formatters
    'format_tags_for_display', 'get_hashtags_for_post',
    'format_post_for_channel', 'format_preview_text',
    'format_moderation_text', 'truncate_text', 'escape_html',
    'format_stats_text', 'format_scheduled_post_info',
    
    # decorators
    'admin_only', 'log_errors', 'with_typing_action',
    'answer_callback_query', 'require_args', 'rate_limit'
]