import hashlib
import httpx
import logging
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, FeatureNotFound

from . import config
from .state import state, get_user_timezone, localize_datetime, format_local_time


def make_id(source: str, link: str) -> str:
    return hashlib.md5(f"{source}|{link}".encode()).hexdigest()[:12]


def is_valid_image_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    return any(parsed.path.lower().endswith(ext) for ext in valid_extensions)


async def validate_image_url(client: httpx.AsyncClient, url: str) -> bool:
    try:
        resp = await client.head(url, timeout=10, follow_redirects=True)
        ctype = resp.headers.get("content-type", "")
        return resp.status_code == 200 and ctype.startswith("image/")
    except Exception as e:
        logging.debug(f"Ошибка валидации изображения {url}: {e}")
        return False


def extract_tags(title: str, context: str = "") -> Dict[str, List[str]]:
    tags = {"brands": [], "models": [], "types": [], "colors": []}
    text = f"{title} {context}".lower()
    for brand, keywords in config.BRAND_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                if brand not in tags["brands"]:
                    tags["brands"].append(brand)
                break
    for model, keywords in config.MODEL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                if model not in tags["models"]:
                    tags["models"].append(model)
                break
    for release_type, keywords in config.RELEASE_TYPES.items():
        for keyword in keywords:
            if keyword in text:
                if release_type not in tags["types"]:
                    tags["types"].append(release_type)
                break
    colors = [
        "black",
        "white",
        "red",
        "blue",
        "green",
        "yellow",
        "purple",
        "pink",
        "orange",
        "grey",
        "gray",
        "черный",
        "белый",
        "красный",
        "синий",
        "зеленый",
        "желтый",
        "фиолетовый",
        "розовый",
        "оранжевый",
        "серый",
    ]
    for color in colors:
        if color in text:
            color_en = color if color in [
                "black",
                "white",
                "red",
                "blue",
                "green",
                "yellow",
                "purple",
                "pink",
                "orange",
                "grey",
                "gray",
            ] else None
            if color_en and color_en not in tags["colors"]:
                tags["colors"].append(color_en)
    return tags


def format_tags_for_display(tags: Dict[str, List[str]]) -> str:
    result = []
    if tags.get("brands"):
        result.append(f"🏷 Бренд: {', '.join(tags['brands'])}")
    if tags.get("models"):
        result.append(f"👟 Модель: {', '.join(tags['models'])}")
    if tags.get("types"):
        result.append(f"📌 Тип: {', '.join(tags['types'])}")
    if tags.get("colors"):
        result.append(f"🎨 Цвет: {', '.join(tags['colors'])}")
    return "\n".join(result) if result else ""


def get_hashtags(title: str, category: str) -> str:
    title_lower = title.lower()
    if category == "sneakers":
        for brand, tags in config.HASHTAGS["sneakers"].items():
            if brand != "default" and (
                brand in title_lower or (brand == "jordan" and "air jordan" in title_lower)
            ):
                return tags
        return config.HASHTAGS["sneakers"]["default"]
    else:
        for brand, tags in config.HASHTAGS["fashion"].items():
            if brand != "default" and (
                brand in title_lower or (brand == "offwhite" and "off-white" in title_lower)
            ):
                return tags
        return config.HASHTAGS["fashion"]["default"]


def format_date_for_display(date_str: str) -> str:
    try:
        if isinstance(date_str, str):
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            date = date_str
        local_date = localize_datetime(date)
        now = localize_datetime(datetime.now(timezone.utc))
        diff = now - local_date
        if diff.days == 0:
            return "Сегодня"
        elif diff.days == 1:
            return "Вчера"
        elif diff.days < 7:
            return f"{diff.days} дней назад"
        else:
            return local_date.strftime("%d.%m.%Y")
    except Exception:
        return "Недавно"


def parse_date_from_rss(item) -> datetime:
    try:
        date_elem = item.find("pubDate") or item.find("published") or item.find("dc:date")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
    except Exception:
        pass
    return datetime.now(timezone.utc)


def parse_schedule_time(text: str) -> Optional[datetime]:
    try:
        text = text.strip()
        user_tz = get_user_timezone()
        now = datetime.now(user_tz)
        time_match = re.match(r"^(\d{1,2}):(\d{2})$", text)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                scheduled = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                if scheduled <= now:
                    scheduled += timedelta(days=1)
                return scheduled.astimezone(timezone.utc)
        datetime_match = re.match(r"^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})$", text)
        if datetime_match:
            day = int(datetime_match.group(1))
            month = int(datetime_match.group(2))
            hours = int(datetime_match.group(3))
            minutes = int(datetime_match.group(4))
            year = now.year
            if 1 <= day <= 31 and 1 <= month <= 12 and 0 <= hours <= 23 and 0 <= minutes <= 59:
                scheduled = user_tz.localize(datetime(year, month, day, hours, minutes))
                if scheduled < now:
                    scheduled = scheduled.replace(year=year + 1)
                return scheduled.astimezone(timezone.utc)
        relative_match = re.match(r"^(\+\d+)([hmd])$", text.lower())
        if relative_match:
            amount = int(relative_match.group(1)[1:])
            unit = relative_match.group(2)
            utc_now = datetime.now(timezone.utc)
            if unit == "h" and 1 <= amount <= 24:
                return utc_now + timedelta(hours=amount)
            elif unit == "m" and 1 <= amount <= 1440:
                return utc_now + timedelta(minutes=amount)
            elif unit == "d" and 1 <= amount <= 30:
                return utc_now + timedelta(days=amount)
    except Exception as e:
        logging.error(f"Ошибка парсинга времени: {e}")
    return None