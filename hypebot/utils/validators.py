"""
Validation utilities
"""
import re
from urllib.parse import urlparse
from typing import Optional

from ..config.constants import VALID_IMAGE_EXTENSIONS


def is_valid_image_url(url: str) -> bool:
    """Check if URL is a valid image URL"""
    if not url or not isinstance(url, str):
        return False
    
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    
    # Check if path ends with valid image extension
    return any(parsed.path.lower().endswith(ext) for ext in VALID_IMAGE_EXTENSIONS)


def is_valid_channel(channel: str) -> bool:
    """Check if channel format is valid"""
    if not channel:
        return False
    
    # Public channel format: @channelname
    if channel.startswith("@"):
        return len(channel) > 1 and channel[1:].replace("_", "").isalnum()
    
    # Private channel format: -1001234567890
    if channel.startswith("-"):
        return channel.lstrip("-").isdigit() and len(channel) > 5
    
    return False


def is_admin(user_id: int, admin_id: Optional[int]) -> bool:
    """Check if user is admin"""
    if not admin_id:  # No admin restriction
        return True
    return user_id == admin_id


def validate_time_format(text: str) -> Optional[re.Match]:
    """Validate time format patterns"""
    patterns = [
        (r'^(\d{1,2}):(\d{2})$', 'time'),  # HH:MM
        (r'^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})$', 'datetime'),  # DD.MM HH:MM
        (r'^\+(\d+)([hmd])$', 'relative')  # +1h, +30m, +2d
    ]
    
    for pattern, format_type in patterns:
        match = re.match(pattern, text.strip().lower())
        if match:
            return match, format_type
    
    return None, None


def validate_post_data(data: dict) -> bool:
    """Validate post data has required fields"""
    required_fields = ['id', 'title', 'link']
    return all(field in data and data[field] for field in required_fields)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    safe_chars = re.sub(r'[^\w\s\-.]', '', filename)
    # Replace spaces with underscores
    safe_chars = safe_chars.replace(' ', '_')
    # Remove multiple underscores
    safe_chars = re.sub(r'_+', '_', safe_chars)
    return safe_chars.strip('_.')


def is_url_suspicious(url: str) -> bool:
    """Check if URL might be suspicious or harmful"""
    suspicious_patterns = [
        r'bit\.ly', r'tinyurl', r'goo\.gl',  # URL shorteners
        r'\.tk$', r'\.ml$', r'\.ga$',  # Suspicious TLDs
    ]
    
    url_lower = url.lower()
    return any(re.search(pattern, url_lower) for pattern in suspicious_patterns)