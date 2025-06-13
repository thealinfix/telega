#!/usr/bin/env python3
# hypebot.py — улучшенная версия с исправлениями временных зон и новыми функциями

import os
import json
import logging
import hashlib
import asyncio
import warnings
import httpx
import base64
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI
from bs4 import BeautifulSoup, FeatureNotFound, XMLParsedAsHTMLWarning
from telegram import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, Update, PhotoSize
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import TelegramError, Conflict, BadRequest
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import re
import pytz

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Конфигурация ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "ТВОЙ_ТЕЛЕГРАМ_ТОКЕН"
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHAT_ID") or "@channelusername"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID") or "123456789"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "sk-...."
STATE_FILE = "state.json"
CHECK_INTERVAL_SECONDS = 1800
MAX_PENDING_POSTS = 100
MAX_POST_AGE_DAYS = 7
MAX_IMAGES_PER_POST = 10  # Максимум изображений в посте

# Временная зона (по умолчанию Москва)
DEFAULT_TIMEZONE = "Europe/Moscow"

# Стили для генерации изображений
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

# Хэштеги для постов
HASHTAGS = {
    "sneakers": {
        "nike": "#nike #sneakers #кроссовки #найк #никебутик",
        "adidas": "#adidas #sneakers #кроссовки #адидас #threestripes", 
        "jordan": "#jordan #airjordan #кроссовки #джордан #jumpman",
        "newbalance": "#newbalance #nb #кроссовки #ньюбаланс #madeinusa",
        "puma": "#puma #sneakers #кроссовки #пума #pumafamily",
        "yeezy": "#yeezy #adidas #кроссовки #изи #kanye",
        "asics": "#asics #sneakers #кроссовки #асикс #geltechnology",
        "reebok": "#reebok #sneakers #кроссовки #рибок #classic",
        "vans": "#vans #sneakers #кроссовки #ванс #offthewall",
        "converse": "#converse #sneakers #кроссовки #конверс #allstar",
        "default": "#sneakers #кроссовки #streetwear #обувь #sneakerhead"
    },
    "fashion": {
        "supreme": "#supreme #streetwear #fashion #суприм #hypebeast",
        "offwhite": "#offwhite #fashion #streetwear #virgilabloh",
        "stussy": "#stussy #streetwear #fashion #stussytribe",
        "palace": "#palace #streetwear #fashion #palaceskateboards",
        "default": "#fashion #мода #streetwear #style #стиль #outfit"
    }
}

# Расширенный список источников
SOURCES = [
    {
        "key": "sneakernews", 
        "name": "SneakerNews", 
        "type": "json", 
        "api": "https://sneakernews.com/wp-json/wp/v2/posts?per_page=10&_embed",
        "category": "sneakers"
    },
    {
        "key": "hypebeast", 
        "name": "Hypebeast Footwear", 
        "type": "rss", 
        "api": "https://hypebeast.com/footwear/feed",
        "category": "sneakers"
    },
    {
        "key": "highsnobiety", 
        "name": "Highsnobiety Sneakers", 
        "type": "rss", 
        "api": "https://www.highsnobiety.com/tag/sneakers/feed/",
        "category": "sneakers"
    },
    {
        "key": "hypebeast_fashion", 
        "name": "Hypebeast Fashion", 
        "type": "rss", 
        "api": "https://hypebeast.com/fashion/feed",
        "category": "fashion"
    },
    {
        "key": "highsnobiety_fashion", 
        "name": "Highsnobiety Fashion", 
        "type": "rss", 
        "api": "https://www.highsnobiety.com/tag/fashion/feed/",
        "category": "fashion"
    }
]

# Система тегов и брендов
BRAND_KEYWORDS = {
    "nike": ["nike", "air max", "air force", "dunk", "blazer", "cortez", "vapormax", "pegasus"],
    "adidas": ["adidas", "yeezy", "boost", "ultraboost", "nmd", "gazelle", "samba", "campus"],
    "jordan": ["jordan", "air jordan", "aj1", "aj4", "aj11", "jumpman"],
    "newbalance": ["new balance", "nb", "990", "991", "992", "993", "2002r", "550"],
    "asics": ["asics", "gel", "gel-lyte", "gel-kayano", "gel-1090"],
    "puma": ["puma", "suede", "clyde", "rs-x"],
    "reebok": ["reebok", "classic", "club c", "question"],
    "vans": ["vans", "old skool", "sk8-hi", "authentic", "era"],
    "converse": ["converse", "chuck taylor", "all star", "one star"],
    "salomon": ["salomon", "xt-6", "speedcross"],
    "supreme": ["supreme", "box logo"],
    "offwhite": ["off-white", "off white", "virgil abloh"],
    "stussy": ["stussy", "stüssy"],
    "palace": ["palace", "palace skateboards"]
}

# Модели кроссовок
MODEL_KEYWORDS = {
    "airmax": ["air max", "airmax", "am1", "am90", "am95", "am97"],
    "airforce": ["air force", "af1", "air force 1"],
    "dunk": ["dunk", "dunk low", "dunk high", "sb dunk"],
    "yeezy": ["yeezy", "boost 350", "boost 700", "foam runner"],
    "jordan1": ["jordan 1", "aj1", "air jordan 1"],
    "jordan4": ["jordan 4", "aj4", "air jordan 4"],
    "ultraboost": ["ultraboost", "ultra boost"],
    "990": ["990", "990v", "990v5", "990v6"]
}

# Типы релизов
RELEASE_TYPES = {
    "retro": ["retro", "og", "original", "vintage"],
    "collab": ["collab", "collaboration", "x ", " x ", "partner"],
    "limited": ["limited", "exclusive", "rare", "special edition"],
    "womens": ["women", "wmns", "female"],
    "kids": ["kids", "gs", "gradeschool", "youth"],
    "lifestyle": ["lifestyle", "casual", "street"],
    "performance": ["performance", "running", "basketball", "training"]
}

# --- Проверка конфигурации ---
if not all([TELEGRAM_TOKEN, OPENAI_API_KEY]):
    logging.critical("Не заданы обязательные переменные окружения")
    exit(1)

# Проверяем ADMIN_CHAT_ID
if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "123456789":
    try:
        ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
    except ValueError:
        logging.critical("ADMIN_CHAT_ID должен быть числом")
        exit(1)
else:
    ADMIN_CHAT_ID = None

# Инициализация OpenAI клиента
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def get_user_timezone():
    """Получить временную зону пользователя"""
    return pytz.timezone(state.get("timezone", DEFAULT_TIMEZONE))

def localize_datetime(dt: datetime) -> datetime:
    """Конвертировать UTC время в локальное"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    user_tz = get_user_timezone()
    return dt.astimezone(user_tz)

def format_local_time(dt: datetime) -> str:
    """Форматировать время в локальной временной зоне"""
    local_dt = localize_datetime(dt)
    return local_dt.strftime("%d.%m.%Y %H:%M")

def clean_old_posts(state_dict):
    """Очистка старых постов из очереди"""
    now = datetime.now(timezone.utc)
    removed_count = 0
    
    # Очищаем старые посты
    for uid in list(state_dict["pending"].keys()):
        post = state_dict["pending"][uid]
        try:
            post_date = datetime.fromisoformat(post.get("timestamp", "").replace('Z', '+00:00'))
            age = now - post_date
            
            if age.days > MAX_POST_AGE_DAYS:
                del state_dict["pending"][uid]
                removed_count += 1
        except:
            continue
    
    # Ограничиваем количество постов
    if len(state_dict["pending"]) > MAX_PENDING_POSTS:
        sorted_posts = sorted(
            state_dict["pending"].items(),
            key=lambda x: x[1].get("timestamp", ""),
            reverse=True
        )
        
        state_dict["pending"] = dict(sorted_posts[:MAX_PENDING_POSTS])
        removed_count += len(sorted_posts) - MAX_PENDING_POSTS
    
    if removed_count > 0:
        logging.info(f"Удалено {removed_count} старых постов")
    
    return removed_count

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            # Инициализация полей
            defaults = {
                "sent_links": [],
                "pending": {},
                "moderation_queue": [],
                "preview_mode": {},
                "thoughts_mode": False,
                "scheduled_posts": {},
                "generated_images": {},
                "waiting_for_image": None,
                "current_thought": None,
                "waiting_for_schedule": None,
                "editing_schedule": None,
                "favorites": [],
                "auto_publish": False,
                "publish_interval": 3600,
                "timezone": DEFAULT_TIMEZONE,
                "channel": TELEGRAM_CHANNEL,
                "waiting_for_channel": False
            }
            
            for key, default_value in defaults.items():
                if key not in state:
                    state[key] = default_value
            
            # Валидация pending записей
            valid_pending = {}
            for uid, record in state["pending"].items():
                if isinstance(record, dict) and all(key in record for key in ['id', 'title', 'link']):
                    valid_pending[uid] = record
                else:
                    logging.warning(f"Удаляю некорректную запись из pending: {uid}")
            state["pending"] = valid_pending
            
            # Очистка старых постов
            clean_old_posts(state)
            
            return state
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.info(f"Создаю новый файл состояния: {e}")
        return {
            "sent_links": [], 
            "pending": {}, 
            "moderation_queue": [], 
            "preview_mode": {}, 
            "thoughts_mode": False,
            "scheduled_posts": {},
            "generated_images": {},
            "waiting_for_image": None,
            "current_thought": None,
            "waiting_for_schedule": None,
            "editing_schedule": None,
            "favorites": [],
            "auto_publish": False,
            "publish_interval": 3600,
            "timezone": DEFAULT_TIMEZONE,
            "channel": TELEGRAM_CHANNEL,
            "waiting_for_channel": False
        }

state = load_state()

def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка при сохранении состояния: {e}")

def make_id(source: str, link: str) -> str:
    return hashlib.md5(f"{source}|{link}".encode()).hexdigest()[:12]

def is_valid_image_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    return any(parsed.path.lower().endswith(ext) for ext in valid_extensions)

async def validate_image_url(client: httpx.AsyncClient, url: str) -> bool:
    try:
        response = await client.head(url, timeout=10, follow_redirects=True)
        content_type = response.headers.get('content-type', '')
        return response.status_code == 200 and content_type.startswith('image/')
    except Exception as e:
        logging.debug(f"Ошибка валидации изображения {url}: {e}")
        return False

def extract_tags(title: str, context: str = "") -> Dict[str, List[str]]:
    """Извлечение тегов из заголовка и контекста"""
    tags = {
        "brands": [],
        "models": [],
        "types": [],
        "colors": []
    }
    
    text = f"{title} {context}".lower()
    
    # Извлекаем бренды
    for brand, keywords in BRAND_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                if brand not in tags["brands"]:
                    tags["brands"].append(brand)
                break
    
    # Извлекаем модели
    for model, keywords in MODEL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                if model not in tags["models"]:
                    tags["models"].append(model)
                break
    
    # Извлекаем типы релизов
    for release_type, keywords in RELEASE_TYPES.items():
        for keyword in keywords:
            if keyword in text:
                if release_type not in tags["types"]:
                    tags["types"].append(release_type)
                break
    
    # Извлекаем цвета
    colors = ["black", "white", "red", "blue", "green", "yellow", "purple", "pink", "orange", "grey", "gray", 
              "черный", "белый", "красный", "синий", "зеленый", "желтый", "фиолетовый", "розовый", "оранжевый", "серый"]
    for color in colors:
        if color in text:
            color_en = color if color in ["black", "white", "red", "blue", "green", "yellow", "purple", "pink", "orange", "grey", "gray"] else None
            if color_en and color_en not in tags["colors"]:
                tags["colors"].append(color_en)
    
    return tags

def format_tags_for_display(tags: Dict[str, List[str]]) -> str:
    """Форматирование тегов для отображения"""
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
    """Генерация хэштегов на основе заголовка и категории"""
    title_lower = title.lower()
    
    if category == "sneakers":
        # Проверяем бренды
        for brand, tags in HASHTAGS["sneakers"].items():
            if brand != "default":
                if brand in title_lower or (brand == "jordan" and "air jordan" in title_lower):
                    return tags
        return HASHTAGS["sneakers"]["default"]
    else:
        # Для моды
        for brand, tags in HASHTAGS["fashion"].items():
            if brand != "default":
                if brand in title_lower or (brand == "offwhite" and "off-white" in title_lower):
                    return tags
        return HASHTAGS["fashion"]["default"]

def format_date_for_display(date_str: str) -> str:
    """Форматирование даты для отображения"""
    try:
        if isinstance(date_str, str):
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            date = date_str
        
        # Конвертируем в локальное время
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
    except:
        return "Недавно"

def parse_date_from_rss(item) -> datetime:
    """Парсинг даты из RSS элемента"""
    try:
        date_elem = item.find("pubDate") or item.find("published") or item.find("dc:date")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
    except:
        pass
    return datetime.now(timezone.utc)

def parse_schedule_time(text: str) -> Optional[datetime]:
    """Парсинг времени/даты из текста с учетом временной зоны"""
    try:
        text = text.strip()
        user_tz = get_user_timezone()
        now = datetime.now(user_tz)
        
        # Проверяем разные форматы
        # 1. Только время ЧЧ:ММ
        time_match = re.match(r'^(\d{1,2}):(\d{2})$', text)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                scheduled = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                if scheduled <= now:
                    scheduled += timedelta(days=1)
                # Конвертируем в UTC для хранения
                return scheduled.astimezone(timezone.utc)
        
        # 2. Дата и время ДД.ММ ЧЧ:ММ
        datetime_match = re.match(r'^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})$', text)
        if datetime_match:
            day = int(datetime_match.group(1))
            month = int(datetime_match.group(2))
            hours = int(datetime_match.group(3))
            minutes = int(datetime_match.group(4))
            year = now.year
            
            # Проверяем валидность
            if 1 <= day <= 31 and 1 <= month <= 12 and 0 <= hours <= 23 and 0 <= minutes <= 59:
                scheduled = user_tz.localize(datetime(year, month, day, hours, minutes))
                # Если дата в прошлом, берем следующий год
                if scheduled < now:
                    scheduled = scheduled.replace(year=year + 1)
                return scheduled.astimezone(timezone.utc)
        
        # 3. Относительное время +1h, +30m, +2d
        relative_match = re.match(r'^\+(\d+)([hmd])$', text.lower())
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2)
            
            utc_now = datetime.now(timezone.utc)
            if unit == 'h' and 1 <= amount <= 24:
                return utc_now + timedelta(hours=amount)
            elif unit == 'm' and 1 <= amount <= 1440:
                return utc_now + timedelta(minutes=amount)
            elif unit == 'd' and 1 <= amount <= 30:
                return utc_now + timedelta(days=amount)
        
    except Exception as e:
        logging.error(f"Ошибка парсинга времени: {e}")
    
    return None

async def generate_image(prompt: str, style: str = "photographic") -> Optional[str]:
    """Генерация изображения через DALL-E 3"""
    try:
        logging.info(f"Генерирую изображение: {prompt[:50]}...")
        
        response = await openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        logging.info("Изображение сгенерировано успешно")
        return image_url
        
    except Exception as e:
        logging.error(f"Ошибка при генерации изображения: {e}")
        return None

async def download_image(url: str) -> Optional[bytes]:
    """Скачивание изображения по URL"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logging.error(f"Ошибка при скачивании изображения: {e}")
        return None

async def analyze_image(image_bytes: bytes) -> str:
    """Анализ изображения через GPT-4 Vision"""
    try:
        # Конвертируем в base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        response = await openai_client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Опиши что изображено на этой картинке. Особое внимание удели деталям, цветам, стилю. Если это кроссовки или одежда - опиши модель, бренд, особенности дизайна."
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
        logging.error(f"Ошибка при анализе изображения: {e}")
        return ""

async def extract_all_images_from_page(client: httpx.AsyncClient, url: str) -> List[str]:
    """Извлечение всех изображений со страницы"""
    images = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = await client.get(url, headers=headers, timeout=20, follow_redirects=True)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            
            # Различные селекторы для изображений
            selectors = [
                "div.gallery img",
                "div.post-gallery img", 
                "div.article-gallery img",
                "div.gallery-container img",
                "figure img",
                "div.post-content img",
                "article img",
                "div[class*='gallery'] img",
                "div[class*='slider'] img",
                "div.entry-content img"
            ]
            
            seen_urls = set()
            
            for selector in selectors:
                for img in soup.select(selector):
                    img_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if not img_url:
                        continue
                    
                    # Преобразуем относительные URL в абсолютные
                    if not img_url.startswith("http"):
                        img_url = urljoin(base_url, img_url)
                    
                    # Проверяем валидность и уникальность
                    if is_valid_image_url(img_url) and img_url not in seen_urls:
                        # Пропускаем маленькие изображения (логотипы и т.д.)
                        if "logo" not in img_url.lower() and "icon" not in img_url.lower():
                            images.append(img_url)
                            seen_urls.add(img_url)
                    
                    if len(images) >= MAX_IMAGES_PER_POST:
                        break
                
                if len(images) >= MAX_IMAGES_PER_POST:
                    break
            
            logging.info(f"Найдено {len(images)} изображений на странице {url}")
            
    except Exception as e:
        logging.error(f"Ошибка при извлечении изображений: {e}")
    
    return images[:MAX_IMAGES_PER_POST]

async def parse_full_content(client: httpx.AsyncClient, record: dict) -> dict:
    """Полный парсинг контента для выбранного поста"""
    try:
        # Извлекаем все изображения со страницы
        all_images = await extract_all_images_from_page(client, record["link"])
        
        if all_images:
            # Сохраняем все найденные изображения
            record["images"] = all_images
            record["original_images"] = all_images.copy()
            logging.info(f"Обновлено {len(all_images)} изображений для поста {record['title'][:30]}...")
        
        record["needs_parsing"] = False
        
    except Exception as e:
        logging.error(f"Ошибка при полном парсинге: {e}")
    
    return record

async def fetch_releases(client: httpx.AsyncClient, progress_message=None, bot=None) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    releases = []
    seen_titles = set()
    
    total_sources = len(SOURCES)
    
    for idx, src in enumerate(SOURCES):
        try:
            # Обновляем прогресс
            if progress_message and bot:
                try:
                    await bot.edit_message_text(
                        f"🔄 Проверяю источники... ({idx + 1}/{total_sources})\n"
                        f"📍 Сейчас: {src['name']}",
                        progress_message.chat.id,
                        progress_message.message_id
                    )
                except:
                    pass
            
            logging.info(f"Проверяю источник: {src['name']}")
            resp = await client.get(src["api"], headers=headers, timeout=20)
            resp.raise_for_status()
            
            if src["type"] == "json":
                try:
                    posts = resp.json()
                    if not isinstance(posts, list):
                        logging.warning(f"Неожиданный формат данных от {src['name']}")
                        continue
                    logging.info(f"Найдено {len(posts)} постов от {src['name']}")
                except json.JSONDecodeError:
                    logging.error(f"Ошибка парсинга JSON от {src['name']}")
                    continue
                
                for post in posts[:10]:
                    try:
                        link = post.get("link")
                        title_data = post.get("title", {})
                        title = title_data.get("rendered", "") if isinstance(title_data, dict) else str(title_data)
                        title = BeautifulSoup(title, "html.parser").get_text(strip=True)
                        
                        if not link or not title or len(title) < 10:
                            continue
                        
                        # Проверка на дубликаты по заголовку
                        title_key = title.lower().strip()
                        if title_key in seen_titles:
                            logging.debug(f"Пропускаю дубликат: {title}")
                            continue
                        seen_titles.add(title_key)
                        
                        uid = make_id(src["key"], link)
                        if uid in state["pending"] or link in state["sent_links"]:
                            continue
                        
                        # Получаем дату
                        date_str = post.get("date") or post.get("modified")
                        if date_str:
                            pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                            pub_date = datetime.now(timezone.utc)
                        
                        images = []
                        # Получаем изображение из featuredmedia
                        media = post.get("_embedded", {}).get("wp:featuredmedia", [])
                        if media and isinstance(media, list) and len(media) > 0:
                            featured_url = media[0].get("source_url")
                            if featured_url and is_valid_image_url(featured_url):
                                images.append(featured_url)
                        
                        context = ""
                        
                        releases.append({
                            "id": uid,
                            "title": title[:200],
                            "link": link,
                            "images": images,
                            "original_images": images.copy(),
                            "context": context[:500] if context else "",
                            "source": src["name"],
                            "category": src.get("category", "sneakers"),
                            "timestamp": pub_date.isoformat(),
                            "needs_parsing": True,  # Всегда парсим для получения всех изображений
                            "tags": extract_tags(title, context)  # Добавляем теги
                        })
                        logging.info(f"Добавлен релиз: {title[:50]}... от {src['name']}")
                    except Exception as e:
                        logging.error(f"Ошибка при обработке поста от {src['name']}: {e}")
                        continue
            
            elif src["type"] == "rss":
                try:
                    # Пробуем разные парсеры
                    try:
                        soup = BeautifulSoup(resp.text, "xml")
                        items = soup.find_all("item")
                    except FeatureNotFound:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        items = soup.find_all("item")
                    
                    if not items:
                        items = soup.find_all("entry")
                    
                    logging.info(f"Найдено {len(items)} записей в RSS от {src['name']}")
                    
                    for item in items[:10]:
                        try:
                            # Получаем ссылку
                            link = None
                            link_elem = item.find("link")
                            if link_elem:
                                link = link_elem.get_text(strip=True) if link_elem.string else link_elem.get("href")
                            
                            if not link:
                                guid = item.find("guid")
                                if guid and guid.get_text(strip=True).startswith("http"):
                                    link = guid.get_text(strip=True)
                            
                            # Получаем заголовок
                            title = None
                            title_elem = item.find("title")
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                            
                            if not link or not title or len(title) < 10:
                                continue
                            
                            # Проверка на дубликаты
                            title_key = title.lower().strip()
                            if title_key in seen_titles:
                                logging.debug(f"Пропускаю дубликат: {title}")
                                continue
                            seen_titles.add(title_key)
                            
                            # Проверяем категорию
                            if src.get("category") == "sneakers":
                                title_lower = title.lower()
                                keywords = ['nike', 'adidas', 'jordan', 'yeezy', 'new balance', 'puma', 
                                           'reebok', 'vans', 'converse', 'asics', 'sneaker', 'shoe', 
                                           'footwear', 'release', 'drop', 'collab', 'air max', 'dunk',
                                           'trainer', 'runner', 'retro']
                                if not any(keyword in title_lower for keyword in keywords):
                                    logging.debug(f"Пропускаю не-кроссовочный пост: {title}")
                                    continue
                            
                            uid = make_id(src["key"], link)
                            if uid in state["pending"] or link in state["sent_links"]:
                                continue
                            
                            # Получаем дату
                            pub_date = parse_date_from_rss(item)
                            
                            images = []
                            description = ""
                            
                            # Получаем описание
                            desc_elem = item.find("description")
                            if desc_elem:
                                desc_text = desc_elem.get_text()
                                desc_soup = BeautifulSoup(desc_text, "html.parser")
                                description = desc_soup.get_text(strip=True)[:500]
                                
                                # Ищем первое изображение для превью
                                first_img = desc_soup.find("img", src=True)
                                if first_img:
                                    img_url = first_img.get("src")
                                    if img_url:
                                        if not img_url.startswith("http"):
                                            base_url = f"https://{urlparse(link).netloc}"
                                            img_url = urljoin(base_url, img_url)
                                        if is_valid_image_url(img_url):
                                            images.append(img_url)
                            
                            releases.append({
                                "id": uid,
                                "title": title[:200],
                                "link": link,
                                "images": images,
                                "original_images": images.copy(),
                                "context": description,
                                "source": src["name"],
                                "category": src.get("category", "sneakers"),
                                "timestamp": pub_date.isoformat(),
                                "needs_parsing": True,  # Всегда парсим для получения всех изображений
                                "tags": extract_tags(title, description)  # Добавляем теги
                            })
                            logging.info(f"Добавлен RSS релиз: {title[:50]}... от {src['name']}")
                        except Exception as e:
                            logging.error(f"Ошибка при обработке RSS-элемента от {src['name']}: {e}")
                            continue
                except Exception as e:
                    logging.error(f"Ошибка при парсинге RSS от {src['name']}: {e}")
                    continue
        
        except httpx.TimeoutException:
            logging.error(f"Timeout при запросе к {src['name']}")
        except httpx.RequestError as e:
            logging.error(f"Ошибка HTTP при запросе к {src['name']}: {e}")
        except Exception as e:
            logging.error(f"Неожиданная ошибка при обработке {src['name']}: {e}")
    
    # Сортируем по дате (новые первыми)
    releases.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    logging.info(f"Найдено {len(releases)} новых релизов всего")
    return releases

async def gen_caption(title: str, context: str, category: str = "sneakers", is_thought: bool = False, image_description: str = "") -> str:
    if is_thought:
        # Режим "мыслей" - более человечный и личный стиль
        system_prompt = """Ты ведешь личный блог о кроссовках и уличной моде. Пиши от первого лица, как будто делишься своими мыслями с друзьями. Стиль непринужденный, с эмоциями и личным отношением. 

ПРАВИЛА ИСПОЛЬЗОВАНИЯ ЭМОДЗИ:
- ТОЛЬКО в начале абзаца или всего поста
- НЕ БОЛЕЕ одного эмодзи на абзац
- НЕ используй эмодзи внутри предложений
- Подходящие эмодзи: 😍 🔥 💭 🤔 😎 ✨ 👟

Можешь использовать:
- Личные впечатления ("мне кажется", "по-моему", "честно говоря")
- Эмоции ("обалдел когда увидел", "влюбился с первого взгляда", "не могу налюбоваться")
- Сравнения из жизни
- Немного юмора или иронии где уместно

Максимум 500 символов. Не используй заезженные фразы."""
        
        if image_description:
            user_prompt = f"Напиши пост-размышление на основе изображения и темы.\nТема: {title}\nОписание изображения: {image_description}"
        else:
            user_prompt = f"Напиши пост-размышление о: {title}"
    else:
        # Улучшенный промпт для обычных постов с эмодзи
        system_prompt = """Ты — автор Telegram-канала про кроссовки и уличную моду. Твоя задача — писать короткие, цепляющие и стильные посты о релизах, трендах и коллаборациях. 

ПРАВИЛА ИСПОЛЬЗОВАНИЯ ЭМОДЗИ:
- ТОЛЬКО один эмодзи в начале поста (настроение/тема)
- Можно добавить ОДИН эмодзи в конце (призыв/вопрос)
- НЕ используй эмодзи внутри текста
- НЕ используй эмодзи в каждом абзаце
- Подходящие эмодзи для начала: 🔥 ⚡️ 💫 👟 🚨
- Подходящие для конца: 👀 🤔 💭

Пиши в нейтрально-молодёжном тоне: без пафоса, без канцелярита, без жаргона. Стиль — живой, лёгкий, современный.

Структура поста:
1. Начни с ОДНОГО эмодзи и цепляющей фразы (1-2 предложения)
2. Суть релиза: бренд, модель, дата (если есть) - БЕЗ эмодзи
3. Эстетика: материалы, цвета, что цепляет - БЕЗ эмодзи
4. Завершение: мнение или вопрос (можно добавить ОДИН эмодзи в конце)

Избегай: длинных текстов, технических деталей, рекламных клише.
Максимум 600 символов."""
        
        user_prompt = f"Заголовок: {title}\nДетали: {context[:500] if context else 'Нет информации'}"
    
    models = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    
    for model in models:
        try:
            logging.info(f"Генерирую {'мысли' if is_thought else 'описание'} для: {title[:50]}... с моделью {model}")
            response = await openai_client.chat.completions.create(
                model=model,
                temperature=0.9 if is_thought else 0.8,
                max_tokens=300,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
            )
            generated = response.choices[0].message.content.strip()
            logging.info(f"{'Мысли' if is_thought else 'Описание'} сгенерированы успешно")
            
            # Для мыслей не добавляем заголовок
            if not is_thought and title.lower() not in generated.lower():
                generated = f"<b>{title}</b>\n\n{generated}"
            
            return generated if generated else f"<b>{title}</b>\n\n🔥 Новый релиз. Подробности скоро!"
            
        except Exception as e:
            logging.error(f"Ошибка с моделью {model}: {type(e).__name__}: {str(e)}")
            continue
    
    logging.error("Все модели OpenAI недоступны")
    return f"<b>{title}</b>\n\n👟 Новый релиз. Следите за обновлениями!"

def build_media_group(record: dict, for_channel: bool = False) -> list:
    """Создание медиа-группы с учетом сгенерированных изображений"""
    # Проверяем есть ли сгенерированные изображения
    generated_images = state.get("generated_images", {}).get(record["id"], [])
    
    # Используем сгенерированные изображения если есть, иначе оригинальные
    if generated_images:
        images = generated_images + record.get("original_images", [])
    else:
        images = record.get("images") or []
    
    caption = record.get("description") or record.get("context") or record.get("title") or ""
    
    if for_channel:
        hashtags = get_hashtags(record.get("title", ""), record.get("category", "sneakers"))
        source_text = f"\n\n📍 {record.get('source', 'Unknown')}"
        category_emoji = "👟" if record.get("category") == "sneakers" else "👔"
        
        # Добавляем информацию о планировании если есть
        schedule_info = ""
        if record.get("scheduled_time"):
            schedule_info = f"\n⏰ Запланировано: {record['scheduled_time']}"
        
        if len(caption) + len(record['link']) + len(source_text) + len(hashtags) + len(schedule_info) + 50 < 1024:
            caption += f"{source_text}\n{category_emoji} <a href=\"{record['link']}\">Читать полностью</a>{schedule_info}\n\n{hashtags}"
        elif len(caption) + len(hashtags) + 20 < 1024:
            caption += f"\n\n{hashtags}"
    
    caption = caption[:1020] + "..." if len(caption) > 1024 else caption
    media = []
    
    if images:
        # Ограничиваем количество изображений
        images_to_use = images[:MAX_IMAGES_PER_POST]
        
        media.append(InputMediaPhoto(
            media=images_to_use[0],
            caption=caption,
            parse_mode=ParseMode.HTML
        ))
        for url in images_to_use[1:]:
            media.append(InputMediaPhoto(media=url))
    
    return media

async def send_preview(bot, record: dict, chat_id: int, current_idx: int, total: int, message_id=None):
    """Отправка превью поста с обновленными изображениями и тегами"""
    category_emoji = "👟" if record.get("category") == "sneakers" else "👔"
    date_str = format_date_for_display(record.get("timestamp", ""))
    
    # Проверяем есть ли сгенерированное изображение
    has_generated = record.get("id") in state.get("generated_images", {})
    is_favorite = record.get("id") in state.get("favorites", [])
    
    # Получаем актуальное количество изображений
    generated_count = len(state.get("generated_images", {}).get(record["id"], []))
    original_count = len(record.get("images", []))
    total_images = generated_count + original_count if has_generated else original_count
    
    # Получаем теги
    tags = record.get("tags", {})
    # Если у старого поста нет тегов, генерируем их
    if not tags and "title" in record:
        tags = extract_tags(record.get("title", ""), record.get("context", ""))
        # Сохраняем теги в запись
        if record["id"] in state["pending"]:
            state["pending"][record["id"]]["tags"] = tags
            save_state()
    
    tags_display = format_tags_for_display(tags)
    
    preview_text = (
        f"📅 <b>{date_str}</b>\n"
        f"{category_emoji} <b>{record['title']}</b>\n\n"
    )
    
    if tags_display:
        preview_text += f"{tags_display}\n\n"
    
    preview_text += (
        f"📍 Источник: {record.get('source', 'Unknown')}\n"
        f"🔗 <a href=\"{record['link']}\">Ссылка на статью</a>\n"
        f"🖼 Изображений: {total_images}\n"
    )
    
    if has_generated:
        preview_text += f"🎨 Сгенерировано: {generated_count}\n"
    
    if is_favorite:
        preview_text += "⭐️ В избранном\n"
    
    preview_text += f"\n📊 Пост {current_idx + 1} из {total}"
    
    # Кнопки навигации
    keyboard_buttons = []
    
    nav_buttons = []
    if current_idx > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"preview_prev:{current_idx}"))
    nav_buttons.append(InlineKeyboardButton(f"{current_idx + 1}/{total}", callback_data="noop"))
    if current_idx < total - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"preview_next:{current_idx}"))
    
    keyboard_buttons.append(nav_buttons)
    keyboard_buttons.append([
        InlineKeyboardButton("👁 Полный просмотр", callback_data=f"preview_full:{record['id']}"),
        InlineKeyboardButton("⭐️" if is_favorite else "☆", callback_data=f"toggle_fav:{record['id']}")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton("🎨 Генерировать обложку", callback_data=f"gen_cover:{record['id']}"),
        InlineKeyboardButton("⏰ Запланировать", callback_data=f"schedule:{record['id']}")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton("🏷 Фильтр по тегам", callback_data="filter_tags"),
        InlineKeyboardButton("❌ Закрыть", callback_data="preview_close")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="cmd_back_main")
    ])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    try:
        if message_id:
            return await bot.edit_message_text(
                preview_text,
                chat_id,
                message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            return await bot.send_message(
                chat_id,
                preview_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
    except BadRequest as e:
        if "message is not modified" in str(e):
            # Сообщение не изменилось, игнорируем
            pass
        else:
            logging.error(f"Ошибка при отправке превью: {e}")
    except Exception as e:
        logging.error(f"Ошибка при отправке превью: {e}")
        return None

async def send_full_post(bot, record: dict, chat_id: int):
    """Отправка полного поста с генерацией описания"""
    loading_msg = await bot.send_message(
        chat_id,
        "⏳ Генерирую описание и загружаю полный контент...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Парсим полный контент если нужно
        if record.get("needs_parsing"):
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                record = await parse_full_content(client, record)
                if record["id"] in state["pending"]:
                    state["pending"][record["id"]] = record
                    save_state()
        
        # Генерируем описание
        if not record.get("description") or record.get("description") == record.get("title"):
            description = await gen_caption(
                record["title"], 
                record.get("context", ""), 
                record.get("category", "sneakers")
            )
            record["description"] = description
            # Сохраняем в state
            if record["id"] in state["pending"]:
                state["pending"][record["id"]]["description"] = description
                save_state()
        
        # Удаляем сообщение о загрузке
        await bot.delete_message(chat_id, loading_msg.message_id)
        
        # Отправляем пост на модерацию
        await send_for_moderation(bot, record, show_all=False)
        
    except Exception as e:
        logging.error(f"Ошибка при отправке полного поста: {e}")
        await bot.edit_message_text(
            "❌ Произошла ошибка при загрузке поста",
            chat_id,
            loading_msg.message_id
        )

async def send_for_moderation(bot, record: dict, show_all: bool = False):
    """Отправка поста на модерацию с учетом всех изображений"""
    if not isinstance(record, dict):
        logging.error("Record не является словарем")
        return False
    
    required_fields = ['id', 'title', 'link']
    for field in required_fields:
        if field not in record:
            logging.error(f"Отсутствует обязательное поле: {field}")
            return False
    
    description = record.get("description")
    if not description:
        description = record.get("context") or record["title"]
        record["description"] = description
    
    approve_data = f"approve:{record['id']}"
    reject_data = f"reject:{record['id']}"
    regenerate_data = f"regen:{record['id']}"
    back_data = f"back_preview:{record['id']}"
    gen_cover_data = f"gen_cover_full:{record['id']}"
    revert_img_data = f"revert_img:{record['id']}"
    custom_prompt_data = f"custom_prompt:{record['id']}"
    
    keyboard_buttons = [
        [InlineKeyboardButton("✅ Опубликовать", callback_data=approve_data)],
        [InlineKeyboardButton("🔄 Перегенерировать текст", callback_data=regenerate_data)],
        [
            InlineKeyboardButton("🎨 Генерировать обложку", callback_data=gen_cover_data),
            InlineKeyboardButton("✏️ Свой промпт", callback_data=custom_prompt_data)
        ],
        [
            InlineKeyboardButton("↩️ Вернуть оригинал", callback_data=revert_img_data),
            InlineKeyboardButton("❌ Пропустить", callback_data=reject_data)
        ],
        [
            InlineKeyboardButton("◀️ Вернуться к превью", callback_data=back_data),
            InlineKeyboardButton("🏠 Главное меню", callback_data="cmd_back_main")
        ]
    ]
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    category_emoji = "👟" if record.get("category") == "sneakers" else "👔"
    date_str = format_date_for_display(record.get("timestamp", ""))
    hashtags = get_hashtags(record.get("title", ""), record.get("category", "sneakers"))
    source_info = f"\n📍 Источник: {record.get('source', 'Unknown')}"
    link_info = f"\n🔗 Статья: {record['link']}"
    
    # Информация о изображениях
    img_info = ""
    generated_count = len(state.get("generated_images", {}).get(record["id"], []))
    original_count = len(record.get("images", []))
    
    if generated_count > 0:
        img_info = f"\n🎨 Сгенерировано: {generated_count}, оригинальных: {original_count}"
    else:
        img_info = f"\n🖼 Изображений: {original_count}"
    
    text = (f"📅 {date_str}\n"
           f"{category_emoji} <b>{record['title']}</b>\n\n"
           f"{record['description'][:400]}"
           f"{source_info}{link_info}{img_info}\n\n"
           f"{hashtags}\n\n"
           f"🆔 ID: {record['id']}")
    
    try:
        media = build_media_group(record, for_channel=False)
        if media:
            await bot.send_media_group(ADMIN_CHAT_ID, media)
            await bot.send_message(
                ADMIN_CHAT_ID,
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        else:
            await bot.send_message(
                ADMIN_CHAT_ID,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        return True
    except TelegramError as e:
        logging.error(f"Ошибка Telegram при отправке на модерацию: {e}")
        return False
    except Exception as e:
        logging.error(f"Неожиданная ошибка при отправке на модерацию: {e}")
        return False

async def publish_release(bot, record: dict):
    logging.info(f"Публикую в канал: {record['title'][:50]}...")
    
    # Получаем текущий канал из состояния
    channel = state.get("channel", TELEGRAM_CHANNEL)
    
    try:
        media = build_media_group(record, for_channel=True)
        if media:
            await bot.send_media_group(channel, media)
        else:
            category_emoji = "👟" if record.get("category") == "sneakers" else "👔"
            hashtags = get_hashtags(record.get("title", ""), record.get("category", "sneakers"))
            
            # Добавляем эмодзи для источника
            source_emojis = {
                "SneakerNews": "📰",
                "Hypebeast": "🔥",
                "Highsnobiety": "💎",
                "Hypebeast Footwear": "👟",
                "Hypebeast Fashion": "👔",
                "Highsnobiety Sneakers": "✨",
                "Highsnobiety Fashion": "🎨"
            }
            source_emoji = source_emojis.get(record.get('source', ''), "📍")
            source_text = f"\n\n{source_emoji} {record.get('source', 'Unknown')}"
            
            text = (f"{category_emoji} <b>{record['title']}</b>\n\n"
                   f"{record['description']}{source_text}\n\n"
                   f"🔗 <a href=\"{record['link']}\">Читать полностью</a>\n\n"
                   f"{hashtags}")
            await bot.send_message(
                channel,
                text,
                parse_mode=ParseMode.HTML
            )
        return True
    except TelegramError as e:
        logging.error(f"Ошибка Telegram при публикации: {e}")
        return False
    except Exception as e:
        logging.error(f"Неожиданная ошибка при публикации: {e}")
        return False

async def check_releases_job(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    
    try:
        # Проверяем есть ли админ
        if not ADMIN_CHAT_ID:
            logging.warning("ADMIN_CHAT_ID не установлен, пропускаем проверку")
            return
            
        # Отправляем уведомление о начале проверки
        progress_msg = await bot.send_message(
            ADMIN_CHAT_ID,
            "🔄 Начинаю проверку источников...",
            parse_mode=ParseMode.HTML
        )
        
        # Ищем новые релизы с прогрессом
        logging.info("Ищу новые релизы...")
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            new_releases = await fetch_releases(client, progress_msg, bot)
        
        if not new_releases:
            await bot.edit_message_text(
                "📭 Новых релизов не найдено",
                progress_msg.chat.id,
                progress_msg.message_id
            )
            return
        
        # Добавляем новые релизы в pending
        added_count = 0
        for rel in new_releases:
            try:
                if rel["id"] not in state["pending"]:
                    state["pending"][rel["id"]] = rel
                    added_count += 1
            except Exception as e:
                logging.error(f"Ошибка при добавлении релиза: {e}")
                continue
        
        if added_count > 0:
            save_state()
            logging.info(f"Добавлено {added_count} новых постов в очередь")
            
            # Группируем посты по датам
            posts_by_date = {}
            for post in state["pending"].values():
                date_str = format_date_for_display(post.get("timestamp", ""))
                if date_str not in posts_by_date:
                    posts_by_date[date_str] = []
                posts_by_date[date_str].append(post)
            
            # Формируем сообщение
            summary = f"🆕 Найдено <b>{added_count}</b> новых постов!\n\n"
            
            for date, posts in sorted(posts_by_date.items()):
                summary += f"📅 <b>{date}</b> ({len(posts)} постов)\n"
                # Группируем по источникам
                by_source = {}
                for post in posts:
                    src = post.get("source", "Unknown")
                    if src not in by_source:
                        by_source[src] = 0
                    by_source[src] += 1
                
                for src, count in by_source.items():
                    summary += f"  • {src}: {count}\n"
                summary += "\n"
            
            summary += f"📊 Всего в очереди: {len(state['pending'])}\n\n"
            summary += "Используйте /preview для просмотра"
            
            await bot.edit_message_text(
                summary,
                progress_msg.chat.id,
                progress_msg.message_id,
                parse_mode=ParseMode.HTML
            )
        
        # Проверяем запланированные посты
        await check_scheduled_posts(bot)
        
        # Проверяем авто-публикацию
        if state.get("auto_publish"):
            await auto_publish_next(bot)
                
    except Exception as e:
        logging.error(f"Ошибка в check_releases_job: {e}")

async def check_scheduled_posts(bot):
    """Проверка и публикация запланированных постов"""
    now = datetime.now(timezone.utc)
    published = []
    
    for post_id, schedule_info in list(state.get("scheduled_posts", {}).items()):
        try:
            scheduled_time = datetime.fromisoformat(schedule_info["time"].replace('Z', '+00:00'))
            if now >= scheduled_time:
                # Публикуем пост
                record = schedule_info["record"]
                success = await publish_release(bot, record)
                
                if success:
                    published.append(post_id)
                    logging.info(f"Опубликован запланированный пост: {record['title'][:50]}")
                    
                    # Уведомляем админа
                    if ADMIN_CHAT_ID:
                        await bot.send_message(
                            ADMIN_CHAT_ID,
                            f"✅ Запланированный пост опубликован:\n{record['title'][:50]}...",
                            parse_mode=ParseMode.HTML
                        )
        except Exception as e:
            logging.error(f"Ошибка при публикации запланированного поста {post_id}: {e}")
    
    # Удаляем опубликованные из запланированных
    for post_id in published:
        state["scheduled_posts"].pop(post_id, None)
        # Удаляем из pending
        state["pending"].pop(post_id, None)
        # Добавляем в отправленные
        record = state["scheduled_posts"].get(post_id, {}).get("record", {})
        if record.get("link"):
            state["sent_links"].append(record["link"])
    
    if published:
        save_state()

async def auto_publish_next(bot):
    """Автоматическая публикация следующего поста из избранного"""
    if not state.get("auto_publish"):
        return
    
    # Проверяем когда была последняя публикация
    last_publish = state.get("last_auto_publish")
    if last_publish:
        last_time = datetime.fromisoformat(last_publish.replace('Z', '+00:00'))
        interval = state.get("publish_interval", 3600)
        if (datetime.now(timezone.utc) - last_time).seconds < interval:
            return
    
    # Ищем пост из избранного
    favorites = state.get("favorites", [])
    for fav_id in favorites:
        if fav_id in state["pending"]:
            record = state["pending"][fav_id]
            success = await publish_release(bot, record)
            
            if success:
                # Обновляем состояние
                state["last_auto_publish"] = datetime.now(timezone.utc).isoformat()
                state["favorites"].remove(fav_id)
                state["pending"].pop(fav_id, None)
                state["sent_links"].append(record["link"])
                save_state()
                
                if ADMIN_CHAT_ID:
                    await bot.send_message(
                        ADMIN_CHAT_ID,
                        f"🤖 Автоматически опубликован пост из избранного:\n{record['title'][:50]}...",
                        parse_mode=ParseMode.HTML
                    )
                break

async def thoughts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для создания поста-размышления"""
    try:
        user_id = update.message.from_user.id
        if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ Эта команда доступна только администратору")
            return
        
        # Проверяем аргументы
        if not context.args:
            await update.message.reply_text(
                "💭 Использование команды:\n"
                "/thoughts <краткое описание>\n\n"
                "Пример:\n"
                "/thoughts новые Jordan 4 в черном цвете\n\n"
                "Также можно прикрепить изображение!"
            )
            return
        
        # Получаем тему
        topic = " ".join(context.args)
        
        # Сохраняем в state для ожидания изображения
        state["waiting_for_image"] = {
            "type": "thoughts",
            "topic": topic,
            "message_id": update.message.message_id
        }
        save_state()
        
        # Показываем процесс
        msg = await update.message.reply_text(
            "💭 Отправьте изображение для анализа или нажмите /skip чтобы создать пост без изображения"
        )
        
    except Exception as e:
        logging.error(f"Ошибка в thoughts_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при создании")

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить ожидание изображения"""
    if state.get("waiting_for_image"):
        waiting_data = state["waiting_for_image"]
        state["waiting_for_image"] = None
        save_state()
        
        if waiting_data["type"] == "thoughts":
            # Генерируем мысли без изображения
            msg = await update.message.reply_text("💭 Генерирую мысли...")
            
            thought_text = await gen_caption(
                waiting_data["topic"], 
                "", 
                "sneakers", 
                is_thought=True
            )
            
            hashtags = get_hashtags(waiting_data["topic"], "sneakers")
            final_text = f"{thought_text}\n\n{hashtags}"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Опубликовать", callback_data="publish_thought")],
                [InlineKeyboardButton("🔄 Перегенерировать", callback_data="regen_thought")],
                [InlineKeyboardButton("🎨 Генерировать обложку", callback_data="gen_thought_cover")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_thought")]
            ])
            
            state["current_thought"] = {
                "text": final_text,
                "topic": waiting_data["topic"]
            }
            save_state()
            
            await msg.edit_text(
                f"💭 <b>Пост-размышление:</b>\n\n{final_text}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий"""
    try:
        if not state.get("waiting_for_image"):
            return
        
        user_id = update.message.from_user.id
        if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
            return
        
        waiting_data = state["waiting_for_image"]
        state["waiting_for_image"] = None
        save_state()
        
        # Показываем процесс
        msg = await update.message.reply_text("🔍 Анализирую изображение...")
        
        # Получаем фото
        photo = update.message.photo[-1]  # Берем самое большое
        file = await context.bot.get_file(photo.file_id)
        
        # Скачиваем изображение
        image_bytes = await file.download_as_bytearray()
        
        # Анализируем изображение
        image_description = await analyze_image(bytes(image_bytes))
        
        if waiting_data["type"] == "thoughts":
            # Генерируем мысли на основе изображения
            await msg.edit_text("💭 Генерирую мысли на основе изображения...")
            
            thought_text = await gen_caption(
                waiting_data["topic"], 
                "", 
                "sneakers", 
                is_thought=True,
                image_description=image_description
            )
            
            hashtags = get_hashtags(waiting_data["topic"], "sneakers")
            final_text = f"{thought_text}\n\n{hashtags}"
            
            # Загружаем изображение в Telegram для использования
            uploaded_photo = await update.message.photo[-1].get_file()
            photo_url = uploaded_photo.file_path
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Опубликовать", callback_data="publish_thought")],
                [InlineKeyboardButton("🔄 Перегенерировать", callback_data="regen_thought")],
                [InlineKeyboardButton("🎨 Генерировать обложку", callback_data="gen_thought_cover")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_thought")]
            ])
            
            state["current_thought"] = {
                "text": final_text,
                "topic": waiting_data["topic"],
                "image_description": image_description,
                "image_url": photo.file_id  # Сохраняем file_id для отправки
            }
            save_state()
            
            await msg.edit_text(
                f"💭 <b>Пост-размышление:</b>\n\n{final_text}\n\n"
                f"📸 Изображение прикреплено",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        
    except Exception as e:
        logging.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке изображения")

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data
        
        # Обработка команд из меню
        if data.startswith("cmd_"):
            if data == "cmd_status":
                await show_status_info(query)
                return
            elif data == "cmd_help":
                await show_help_info(query)
                return
            elif data == "cmd_preview":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await start_preview_mode(query, context)
                return
            elif data == "cmd_check":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await query.edit_message_text("🔄 Запускаю проверку новых релизов...")
                asyncio.create_task(check_releases_job(context))
                return
            elif data == "cmd_thoughts":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await show_thoughts_prompt(query)
                return
            elif data == "cmd_scheduled":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await show_scheduled_posts(query)
                return
            elif data == "cmd_stats":
                await show_stats_info(query)
                return
            elif data == "cmd_clean_menu":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await show_clean_menu(query)
                return
            elif data == "cmd_tools_menu":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await show_tools_menu(query)
                return
            elif data == "cmd_back_main":
                await show_main_menu(query)
                return
            elif data == "cmd_auto_menu":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await show_auto_publish_menu(query)
                return
            elif data == "cmd_settings":
                if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                    await query.edit_message_text("❌ Эта команда доступна только администратору")
                    return
                await show_settings_menu(query)
                return
        
        # Обработка настроек
        if data.startswith("settings_"):
            if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                await query.edit_message_text("❌ Недостаточно прав")
                return
                
            if data == "settings_channel":
                state["waiting_for_channel"] = True
                save_state()
                await query.edit_message_text(
                    "📢 <b>Изменение канала публикации</b>\n\n"
                    "Отправьте новый канал в формате:\n"
                    "• <code>@channelname</code> - для публичного канала\n"
                    "• <code>-1001234567890</code> - для приватного канала (ID чата)\n\n"
                    f"Текущий канал: <code>{state.get('channel', TELEGRAM_CHANNEL)}</code>\n\n"
                    "Или /cancel для отмены",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "settings_timezone":
                await show_timezone_menu(query)
                return
        
        # Обработка временных зон
        if data.startswith("tz_"):
            if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                await query.edit_message_text("❌ Недостаточно прав")
                return
                
            timezone_name = data.replace("tz_", "").replace("_", "/")
            state["timezone"] = timezone_name
            save_state()
            
            await query.edit_message_text(
                f"✅ Временная зона изменена на {timezone_name}\n\n"
                f"Текущее время: {datetime.now(pytz.timezone(timezone_name)).strftime('%H:%M')}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Обработка авто-публикации
        if data.startswith("auto_"):
            if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                await query.edit_message_text("❌ Недостаточно прав")
                return
            
            if data == "auto_toggle":
                state["auto_publish"] = not state.get("auto_publish", False)
                save_state()
                await show_auto_publish_menu(query)
                return
            elif data.startswith("auto_interval:"):
                interval = int(data.split(":")[1])
                state["publish_interval"] = interval
                save_state()
                await show_auto_publish_menu(query)
                return
        
        # Обработка избранного
        if data.startswith("toggle_fav:"):
            uid = data.split(":")[1]
            if "favorites" not in state:
                state["favorites"] = []
            
            if uid in state["favorites"]:
                state["favorites"].remove(uid)
            else:
                state["favorites"].append(uid)
            
            save_state()
            
            # Обновляем превью
            preview_list = state.get("preview_mode", {}).get("list", [])
            if uid in preview_list:
                idx = preview_list.index(uid)
                record = state["pending"].get(uid)
                if record:
                    await send_preview(
                        context.bot,
                        record,
                        query.message.chat.id,
                        idx,
                        len(preview_list),
                        query.message.message_id
                    )
            return
        
        # Обработка меню очистки
        if data.startswith("clean_"):
            if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                await query.edit_message_text("❌ Недостаточно прав")
                return
                
            if data == "clean_old":
                before_count = len(state["pending"])
                removed = clean_old_posts(state)
                after_count = len(state["pending"])
                save_state()
                
                await query.edit_message_text(
                    f"🗑 <b>Очистка завершена:</b>\n\n"
                    f"Было постов: {before_count}\n"
                    f"Удалено старых: {removed}\n"
                    f"Осталось: {after_count}\n\n"
                    f"Удаляются посты старше {MAX_POST_AGE_DAYS} дней",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "clean_pending":
                count = len(state["pending"])
                state["pending"].clear()
                state["preview_mode"].clear()
                state["generated_images"].clear()
                save_state()
                
                await query.edit_message_text(f"🗑 Очищено {count} постов из очереди")
                return
            elif data == "clean_sent":
                count = len(state["sent_links"])
                state["sent_links"].clear()
                save_state()
                
                await query.edit_message_text(f"🗑 Очищен список обработанных: {count} записей")
                return
        
        # Обработка меню инструментов
        if data.startswith("tool_"):
            if ADMIN_CHAT_ID and query.from_user.id != ADMIN_CHAT_ID:
                await query.edit_message_text("❌ Недостаточно прав")
                return
                
            if data == "tool_test_sources":
                await query.edit_message_text("🔍 Тестирую источники...")
                await test_sources_inline(query, context)
                return
        
        # Обработка планирования
        if data.startswith("schedule:"):
            uid = data.split(":")[1]
            state["waiting_for_schedule"] = uid
            save_state()
            
            user_tz = get_user_timezone()
            await query.edit_message_text(
                f"⏰ <b>Планирование публикации</b>\n\n"
                f"Ваша временная зона: {state.get('timezone', DEFAULT_TIMEZONE)}\n"
                f"Текущее время: {datetime.now(user_tz).strftime('%H:%M')}\n\n"
                f"Отправьте время в одном из форматов:\n"
                f"• <code>18:30</code> - сегодня в 18:30\n"
                f"• <code>25.12 15:00</code> - конкретная дата\n"
                f"• <code>+2h</code> - через 2 часа\n"
                f"• <code>+30m</code> - через 30 минут\n"
                f"• <code>+1d</code> - через 1 день\n\n"
                f"Или /cancel для отмены",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Обработка редактирования расписания
        if data.startswith("edit_schedule:"):
            post_id = data.split(":")[1]
            state["editing_schedule"] = post_id
            save_state()
            
            schedule_info = state["scheduled_posts"].get(post_id)
            if schedule_info:
                scheduled_time = datetime.fromisoformat(schedule_info["time"].replace('Z', '+00:00'))
                local_time = localize_datetime(scheduled_time)
                user_tz = get_user_timezone()
                
                await query.edit_message_text(
                    f"📝 <b>Изменение времени публикации</b>\n\n"
                    f"Текущее время: {local_time.strftime('%d.%m.%Y %H:%M')} ({state.get('timezone', DEFAULT_TIMEZONE)})\n"
                    f"Сейчас: {datetime.now(user_tz).strftime('%H:%M')}\n\n"
                    f"Отправьте новое время в формате:\n"
                    f"• <code>18:30</code> - сегодня в 18:30\n"
                    f"• <code>25.12 15:00</code> - конкретная дата\n"
                    f"• <code>+2h</code> - через 2 часа\n\n"
                    f"Или /cancel для отмены",
                    parse_mode=ParseMode.HTML
                )
            return
        
        # Обработка удаления из расписания
        if data.startswith("delete_schedule:"):
            post_id = data.split(":")[1]
            if post_id in state.get("scheduled_posts", {}):
                state["scheduled_posts"].pop(post_id)
                save_state()
                await query.edit_message_text("✅ Пост удален из расписания")
            return
        
        # Обработка кастомного промпта
        if data.startswith("custom_prompt:"):
            uid = data.split(":")[1]
            state["waiting_for_prompt"] = uid
            save_state()
            
            await query.edit_message_text(
                "✏️ <b>Создание кастомной обложки</b>\n\n"
                "Отправьте описание для генерации изображения.\n"
                "Пример: <i>Futuristic Nike Air Max sneakers floating in space with neon lights</i>\n\n"
                "Или /cancel для отмены",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Обработка фильтров
        if data == "filter_tags":
            await show_filter_menu(query)
            return
        
        elif data.startswith("filter_brand:"):
            brand = data.split(":")[1]
            await filter_posts_by_tag(query, context, "brand", brand)
            return
        
        elif data.startswith("filter_model:"):
            model = data.split(":")[1]
            await filter_posts_by_tag(query, context, "model", model)
            return
        
        elif data.startswith("filter_type:"):
            release_type = data.split(":")[1]
            await filter_posts_by_tag(query, context, "type", release_type)
            return
        
        elif data == "filter_reset":
            # Сбрасываем фильтры
            preview_list = sorted(
                state["pending"].keys(),
                key=lambda x: state["pending"][x].get("timestamp", ""),
                reverse=True
            )
            state["preview_mode"] = {
                "list": preview_list,
                "current": 0,
                "filter": None
            }
            save_state()
            
            await query.edit_message_text("✅ Фильтры сброшены")
            
            if preview_list:
                first_record = state["pending"].get(preview_list[0])
                if first_record:
                    await send_preview(
                        context.bot,
                        first_record,
                        query.message.chat.id,
                        0,
                        len(preview_list)
                    )
            return
        
        # Обработка превью
        if data.startswith("preview_"):
            if data == "preview_close":
                await query.message.delete()
                return
            
            elif data.startswith("preview_next:") or data.startswith("preview_prev:"):
                current_idx = int(data.split(":")[1])
                preview_list = state.get("preview_mode", {}).get("list", [])
                
                if data.startswith("preview_next:"):
                    new_idx = min(current_idx + 1, len(preview_list) - 1)
                else:
                    new_idx = max(current_idx - 1, 0)
                
                if 0 <= new_idx < len(preview_list):
                    uid = preview_list[new_idx]
                    record = state["pending"].get(uid)
                    if record:
                        await send_preview(
                            context.bot, 
                            record, 
                            query.message.chat.id,
                            new_idx,
                            len(preview_list),
                            query.message.message_id
                        )
                return
            
            elif data.startswith("preview_full:"):
                uid = data.split(":")[1]
                record = state["pending"].get(uid)
                if record:
                    # Удаляем превью и показываем полный пост
                    await query.message.delete()
                    await send_full_post(context.bot, record, query.message.chat.id)
                return
        
        elif data.startswith("gen_cover"):
            # Генерация обложки
            uid = data.split(":")[-1]
            record = state["pending"].get(uid)
            if record:
                await query.message.edit_text("🎨 Генерирую обложку...")
                
                # Определяем стиль
                category = record.get("category", "sneakers")
                style_config = IMAGE_STYLES.get(category, IMAGE_STYLES["sneakers"])
                
                # Генерируем промпт
                prompt = style_config["prompt_template"].format(title=record["title"])
                
                # Генерируем изображение
                image_url = await generate_image(prompt, style_config["style"])
                
                if image_url:
                    # Сохраняем сгенерированное изображение
                    if uid not in state["generated_images"]:
                        state["generated_images"][uid] = []
                    
                    state["generated_images"][uid].append(image_url)
                    
                    # Обновляем запись
                    state["pending"][uid] = record
                    save_state()
                    
                    await query.message.edit_text("✅ Обложка сгенерирована!")
                    
                    # Если это полный просмотр, обновляем пост
                    if "full" in data:
                        await send_for_moderation(context.bot, record)
                else:
                    await query.message.edit_text("❌ Ошибка при генерации обложки")
            return
        
        elif data.startswith("revert_img:"):
            # Возврат к оригинальным изображениям
            uid = data.split(":")[1]
            record = state["pending"].get(uid)
            if record:
                state["generated_images"].pop(uid, None)
                save_state()
                
                await query.message.edit_text("✅ Возвращены оригинальные изображения")
                await send_for_moderation(context.bot, record)
            return
        
        elif data.startswith("back_preview:"):
            # Возврат к превью
            uid = data.split(":")[1]
            await query.message.delete()
            
            preview_list = state.get("preview_mode", {}).get("list", [])
            if uid in preview_list:
                idx = preview_list.index(uid)
                record = state["pending"].get(uid)
                if record:
                    await send_preview(
                        context.bot,
                        record,
                        query.message.chat.id,
                        idx,
                        len(preview_list)
                    )
            return
        
        elif data == "publish_thought":
            # Публикация мысли
            thought_data = state.get("current_thought")
            if thought_data:
                try:
                    channel = state.get("channel", TELEGRAM_CHANNEL)
                    # Проверяем есть ли изображение
                    if thought_data.get("image_url"):
                        await context.bot.send_photo(
                            channel,
                            thought_data["image_url"],
                            caption=thought_data["text"],
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await context.bot.send_message(
                            channel,
                            thought_data["text"],
                            parse_mode=ParseMode.HTML
                        )
                    await query.edit_message_text("✅ Мысли опубликованы!")
                    state.pop("current_thought", None)
                    save_state()
                except Exception as e:
                    await query.edit_message_text(f"❌ Ошибка публикации: {e}")
            return
        
        elif data == "regen_thought":
            # Перегенерация мысли
            thought_data = state.get("current_thought")
            if thought_data:
                await query.edit_message_text("🔄 Генерирую новые мысли...")
                
                new_thought = await gen_caption(
                    thought_data["topic"], 
                    "", 
                    "sneakers", 
                    is_thought=True,
                    image_description=thought_data.get("image_description", "")
                )
                hashtags = get_hashtags(thought_data["topic"], "sneakers")
                final_text = f"{new_thought}\n\n{hashtags}"
                
                state["current_thought"]["text"] = final_text
                save_state()
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Опубликовать", callback_data="publish_thought")],
                    [InlineKeyboardButton("🔄 Перегенерировать", callback_data="regen_thought")],
                    [InlineKeyboardButton("🎨 Генерировать обложку", callback_data="gen_thought_cover")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="cancel_thought")]
                ])
                
                await query.edit_message_text(
                    f"💭 <b>Пост-размышление:</b>\n\n{final_text}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            return
        
        elif data == "gen_thought_cover":
            # Генерация обложки для мысли
            thought_data = state.get("current_thought")
            if thought_data:
                await query.edit_message_text("🎨 Генерирую обложку для мысли...")
                
                style_config = IMAGE_STYLES["thoughts"]
                prompt = style_config["prompt_template"].format(topic=thought_data["topic"])
                
                image_url = await generate_image(prompt, style_config["style"])
                
                if image_url:
                    thought_data["image_url"] = image_url
                    state["current_thought"] = thought_data
                    save_state()
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Опубликовать", callback_data="publish_thought")],
                        [InlineKeyboardButton("🔄 Перегенерировать текст", callback_data="regen_thought")],
                        [InlineKeyboardButton("🎨 Новая обложка", callback_data="gen_thought_cover")],
                        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_thought")]
                    ])
                    
                    await query.edit_message_text(
                        f"💭 <b>Пост-размышление:</b>\n\n{thought_data['text']}\n\n"
                        f"🎨 Обложка сгенерирована!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text("❌ Ошибка при генерации обложки")
            return
        
        elif data == "cancel_thought":
            await query.message.delete()
            state.pop("current_thought", None)
            save_state()
            return
        
        elif data == "noop":
            # Пустое действие
            return
        
        # Обработка модерации
        if ":" not in data:
            await query.edit_message_text("❌ Ошибка: некорректный формат данных")
            return
        
        action, uid = data.split(":", 1)
        
        if action not in ["approve", "reject", "regen"]:
            await query.edit_message_text("❌ Ошибка: неизвестное действие")
            return
        
        record = state["pending"].get(uid)
        if not record:
            await query.edit_message_text("❌ Этот пост уже был обработан")
            return
        
        if action == "approve":
            published = await publish_release(context.bot, record)
            if published:
                await query.edit_message_text(f"✅ Опубликовано: {record['title'][:50]}...")
                if record["link"] not in state["sent_links"]:
                    state["sent_links"].append(record["link"])
                    if len(state["sent_links"]) > 1000:
                        state["sent_links"] = state["sent_links"][-500:]
                state["pending"].pop(uid, None)
                state["generated_images"].pop(uid, None)
                save_state()
            else:
                await query.edit_message_text(f"🚨 Ошибка публикации: {record['title'][:50]}...")
        
        elif action == "reject":
            await query.edit_message_text(f"❌ Пропущено: {record['title'][:50]}...")
            state["pending"].pop(uid, None)
            state["generated_images"].pop(uid, None)
            save_state()
        
        elif action == "regen":
            await query.edit_message_text(f"🔄 Регенерирую описание для: {record['title'][:50]}...")
            
            context_text = record.get("context", "")
            if not context_text and "link" in record:
                context_text = f"Релиз от {record.get('title', '')}"
            
            new_description = await gen_caption(record["title"], context_text, record.get("category", "sneakers"))
            record["description"] = new_description
            state["pending"][uid] = record
            save_state()
            
            await send_for_moderation(context.bot, record, show_all=False)
            
    except Exception as e:
        logging.error(f"Ошибка при обработке callback: {e}")
        try:
            await query.edit_message_text("❌ Произошла ошибка при обработке")
        except:
            await query.answer("❌ Произошла ошибка")

# Обработчики команд
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info(f"Команда /start от пользователя {update.message.from_user.id}")
        is_admin = not ADMIN_CHAT_ID or update.message.from_user.id == ADMIN_CHAT_ID
        
        # Базовые кнопки для всех пользователей
        keyboard_buttons = [
            [InlineKeyboardButton("📊 Статус бота", callback_data="cmd_status")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="cmd_help")]
        ]
        
        if is_admin:
            # Кнопки для администратора
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("👁 Превью постов", callback_data="cmd_preview"),
                    InlineKeyboardButton("🔄 Проверить релизы", callback_data="cmd_check")
                ],
                [
                    InlineKeyboardButton("💭 Создать мысли", callback_data="cmd_thoughts"),
                    InlineKeyboardButton("⏰ Запланированные", callback_data="cmd_scheduled")
                ],
                [
                    InlineKeyboardButton("📈 Статистика", callback_data="cmd_stats"),
                    InlineKeyboardButton("🤖 Авто-публикация", callback_data="cmd_auto_menu")
                ],
                [
                    InlineKeyboardButton("⚙️ Настройки", callback_data="cmd_settings"),
                    InlineKeyboardButton("🧹 Очистка", callback_data="cmd_clean_menu")
                ],
                [
                    InlineKeyboardButton("🔧 Инструменты", callback_data="cmd_tools_menu")
                ]
            ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        welcome_text = (
            "👟 <b>HypeBot</b> - мониторинг релизов кроссовок и уличной моды\n\n"
            "🔥 Актуальные релизы Nike, Adidas, Jordan и других брендов\n"
            "🤖 Автоматическая генерация описаний и обложек\n"
            "⏰ Планировщик публикаций\n"
            "⭐️ Избранное и авто-публикация\n\n"
            "Выберите нужную команду:"
        )
        
        if is_admin:
            welcome_text += f"\n\n🔐 <i>Вы вошли как администратор</i>"
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Ошибка в start_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    try:
        user_id = update.message.from_user.id
        if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
            return
        
        text = update.message.text
        
        # Проверяем разные состояния ожидания
        if state.get("waiting_for_channel"):
            # Ожидаем новый канал
            new_channel = text.strip()
            
            # Валидация канала
            if new_channel.startswith("@") or (new_channel.lstrip("-").isdigit() and len(new_channel) > 5):
                state["channel"] = new_channel
                state["waiting_for_channel"] = False
                save_state()
                
                await update.message.reply_text(
                    f"✅ Канал изменен на: <code>{new_channel}</code>\n\n"
                    f"Все новые публикации будут отправляться в этот канал.",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    "❌ Неверный формат канала\n\n"
                    "Используйте:\n"
                    "• <code>@channelname</code> для публичного канала\n"
                    "• <code>-1001234567890</code> для приватного канала",
                    parse_mode=ParseMode.HTML
                )
        
        elif state.get("waiting_for_schedule"):
            # Ожидаем время для планирования
            scheduled_time = parse_schedule_time(text)
            if scheduled_time:
                post_id = state["waiting_for_schedule"]
                record = state["pending"].get(post_id)
                
                if record:
                    state["scheduled_posts"][post_id] = {
                        "time": scheduled_time.isoformat(),
                        "record": record
                    }
                    
                    state["waiting_for_schedule"] = None
                    save_state()
                    
                    local_time = localize_datetime(scheduled_time)
                    await update.message.reply_text(
                        f"✅ Пост запланирован на {local_time.strftime('%d.%m.%Y %H:%M')} ({state.get('timezone', DEFAULT_TIMEZONE)})\n"
                        f"📝 {record['title'][:50]}..."
                    )
                else:
                    await update.message.reply_text("❌ Пост не найден")
            else:
                await update.message.reply_text(
                    "❌ Неверный формат времени\n\n"
                    "Используйте:\n"
                    "• <code>18:30</code>\n"
                    "• <code>25.12 15:00</code>\n"
                    "• <code>+2h</code>",
                    parse_mode=ParseMode.HTML
                )
        
        elif state.get("editing_schedule"):
            # Редактируем время планирования
            scheduled_time = parse_schedule_time(text)
            if scheduled_time:
                post_id = state["editing_schedule"]
                
                if post_id in state.get("scheduled_posts", {}):
                    state["scheduled_posts"][post_id]["time"] = scheduled_time.isoformat()
                    state["editing_schedule"] = None
                    save_state()
                    
                    local_time = localize_datetime(scheduled_time)
                    await update.message.reply_text(
                        f"✅ Время изменено на {local_time.strftime('%d.%m.%Y %H:%M')} ({state.get('timezone', DEFAULT_TIMEZONE)})"
                    )
                else:
                    await update.message.reply_text("❌ Запланированный пост не найден")
            else:
                await update.message.reply_text("❌ Неверный формат времени")
        
        elif state.get("waiting_for_prompt"):
            # Ожидаем кастомный промпт
            uid = state["waiting_for_prompt"]
            record = state["pending"].get(uid)
            
            if record:
                await update.message.reply_text("🎨 Генерирую изображение с вашим описанием...")
                
                # Генерируем изображение
                image_url = await generate_image(text, "creative")
                
                if image_url:
                    # Сохраняем сгенерированное изображение
                    if uid not in state["generated_images"]:
                        state["generated_images"][uid] = []
                    
                    state["generated_images"][uid].append(image_url)
                    state["waiting_for_prompt"] = None
                    save_state()
                    
                    await update.message.reply_text("✅ Изображение сгенерировано!")
                    await send_for_moderation(context.bot, record)
                else:
                    await update.message.reply_text("❌ Ошибка при генерации изображения")
            else:
                await update.message.reply_text("❌ Пост не найден")
                
        elif state.get("auto_interval_custom"):
            # Ожидаем кастомный интервал
            try:
                minutes = int(text)
                if 10 <= minutes <= 1440:  # От 10 минут до 24 часов
                    state["publish_interval"] = minutes * 60
                    state["auto_interval_custom"] = False
                    save_state()
                    await update.message.reply_text(f"✅ Интервал установлен: {minutes} минут")
                else:
                    await update.message.reply_text("❌ Интервал должен быть от 10 до 1440 минут")
            except ValueError:
                await update.message.reply_text("❌ Введите число минут")
        
    except Exception as e:
        logging.error(f"Ошибка в handle_text_message: {e}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    user_id = update.message.from_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    cancelled = []
    
    if state.get("waiting_for_schedule"):
        state["waiting_for_schedule"] = None
        cancelled.append("планирование поста")
    
    if state.get("editing_schedule"):
        state["editing_schedule"] = None
        cancelled.append("изменение расписания")
    
    if state.get("waiting_for_image"):
        state["waiting_for_image"] = None
        cancelled.append("ожидание изображения")
    
    if state.get("waiting_for_prompt"):
        state["waiting_for_prompt"] = None
        cancelled.append("ожидание промпта")
    
    if state.get("auto_interval_custom"):
        state["auto_interval_custom"] = False
        cancelled.append("установка интервала")
    
    if state.get("waiting_for_channel"):
        state["waiting_for_channel"] = False
        cancelled.append("изменение канала")
    
    save_state()
    
    if cancelled:
        await update.message.reply_text(f"❌ Отменено: {', '.join(cancelled)}")
    else:
        await update.message.reply_text("❌ Нечего отменять")

# Вспомогательные функции для интерактивного меню
async def show_main_menu(query):
    """Показать главное меню"""
    is_admin = not ADMIN_CHAT_ID or query.from_user.id == ADMIN_CHAT_ID
    
    keyboard_buttons = [
        [InlineKeyboardButton("📊 Статус бота", callback_data="cmd_status")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="cmd_help")]
    ]
    
    if is_admin:
        keyboard_buttons.extend([
            [
                InlineKeyboardButton("👁 Превью постов", callback_data="cmd_preview"),
                InlineKeyboardButton("🔄 Проверить релизы", callback_data="cmd_check")
            ],
            [
                InlineKeyboardButton("💭 Создать мысли", callback_data="cmd_thoughts"),
                InlineKeyboardButton("⏰ Запланированные", callback_data="cmd_scheduled")
            ],
            [
                InlineKeyboardButton("📈 Статистика", callback_data="cmd_stats"),
                InlineKeyboardButton("🤖 Авто-публикация", callback_data="cmd_auto_menu")
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data="cmd_settings"),
                InlineKeyboardButton("🧹 Очистка", callback_data="cmd_clean_menu")
            ],
            [
                InlineKeyboardButton("🔧 Инструменты", callback_data="cmd_tools_menu")
            ]
        ])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    welcome_text = (
        "👟 <b>HypeBot</b> - мониторинг релизов кроссовок и уличной моды\n\n"
        "🔥 Актуальные релизы Nike, Adidas, Jordan и других брендов\n"
        "🤖 Автоматическая генерация описаний и обложек\n"
        "⏰ Планировщик публикаций\n"
        "⭐️ Избранное и авто-публикация\n\n"
        "Выберите нужную команду:"
    )
    
    if is_admin:
        welcome_text += f"\n\n🔐 <i>Вы вошли как администратор</i>"
    
    await query.edit_message_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def show_help_info(query):
    """Показать справку"""
    help_text = (
        "ℹ️ <b>Справка по HypeBot</b>\n\n"
        "🔥 <b>Что умеет бот:</b>\n"
        "• Мониторинг релизов кроссовок и моды\n"
        "• Автоматическая генерация описаний\n"
        "• Создание обложек через ИИ\n"
        "• Планирование публикаций\n"
        "• Система тегов и фильтров\n\n"
        "📱 <b>Источники:</b>\n"
        "• SneakerNews\n"
        "• Hypebeast\n"
        "• Highsnobiety\n\n"
        "🤖 <b>ИИ функции:</b>\n"
        "• GPT-4 для генерации текстов\n"
        "• DALL-E 3 для создания обложек\n"
        "• GPT-4 Vision для анализа изображений\n\n"
        "🏷 <b>Система тегов:</b>\n"
        "• Автоматическое определение брендов\n"
        "• Распознавание моделей\n"
        "• Фильтрация по категориям\n\n"
        "💬 Для получения доступа администратора обратитесь к создателю бота"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
    ])
    
    await query.edit_message_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def show_settings_menu(query):
    """Показать меню настроек"""
    current_channel = state.get("channel", TELEGRAM_CHANNEL)
    current_timezone = state.get("timezone", DEFAULT_TIMEZONE)
    
    settings_text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"📢 Канал публикации: <code>{current_channel}</code>\n"
        f"🕐 Временная зона: {current_timezone}\n"
        f"📅 Текущее время: {datetime.now(pytz.timezone(current_timezone)).strftime('%H:%M')}\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Изменить канал", callback_data="settings_channel")],
        [InlineKeyboardButton("🕐 Изменить временную зону", callback_data="settings_timezone")],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
    ])
    
    await query.edit_message_text(
        settings_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def show_timezone_menu(query):
    """Показать меню выбора временной зоны"""
    timezones = [
        ("🇷🇺 Москва", "Europe/Moscow"),
        ("🇷🇺 Санкт-Петербург", "Europe/Moscow"),
        ("🇷🇺 Екатеринбург", "Asia/Yekaterinburg"),
        ("🇷🇺 Новосибирск", "Asia/Novosibirsk"),
        ("🇷🇺 Владивосток", "Asia/Vladivostok"),
        ("🇺🇦 Киев", "Europe/Kiev"),
        ("🇰🇿 Алматы", "Asia/Almaty"),
        ("🇧🇾 Минск", "Europe/Minsk"),
        ("🇺🇸 Нью-Йорк", "America/New_York"),
        ("🇬🇧 Лондон", "Europe/London"),
    ]
    
    keyboard_buttons = []
    for name, tz in timezones:
        callback_data = f"tz_{tz.replace('/', '_')}"
        keyboard_buttons.append([InlineKeyboardButton(name, callback_data=callback_data)])
    
    keyboard_buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="cmd_settings")])
    
    await query.edit_message_text(
        "🕐 <b>Выберите временную зону:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

async def show_stats_info(query):
    """Показать статистику"""
    try:
        pending_count = len(state["pending"])
        sent_count = len(state["sent_links"])
        scheduled_count = len(state.get("scheduled_posts", {}))
        favorites_count = len(state.get("favorites", []))
        
        # Статистика по брендам
        brand_stats = {}
        for post in state["pending"].values():
            brands = post.get("tags", {}).get("brands", [])
            for brand in brands:
                brand_stats[brand] = brand_stats.get(brand, 0) + 1
        
        # Статистика по источникам
        source_stats = {}
        for post in state["pending"].values():
            source = post.get("source", "Unknown")
            source_stats[source] = source_stats.get(source, 0) + 1
        
        stats_text = (
            f"📈 <b>Статистика бота:</b>\n\n"
            f"📝 Постов в ожидании: {pending_count}\n"
            f"⏰ Запланировано: {scheduled_count}\n"
            f"⭐️ В избранном: {favorites_count}\n"
            f"✅ Опубликовано: {sent_count}\n\n"
        )
        
        if brand_stats:
            stats_text += "🏷 <b>По брендам:</b>\n"
            for brand, count in sorted(brand_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                stats_text += f"• {brand.title()}: {count}\n"
            stats_text += "\n"
        
        if source_stats:
            stats_text += "📍 <b>По источникам:</b>\n"
            for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
                stats_text += f"• {source}: {count}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
        
        await query.edit_message_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Ошибка в show_stats_info: {e}")
        await query.edit_message_text("❌ Произошла ошибка")

async def show_tools_menu(query):
    """Показать меню инструментов"""
    tools_text = (
        "🔧 <b>Инструменты</b>\n\n"
        "Дополнительные функции для администратора:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Тест источников", callback_data="tool_test_sources")],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
    ])
    
    await query.edit_message_text(
        tools_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def show_clean_menu(query):
    """Показать меню очистки"""
    clean_text = (
        "🧹 <b>Меню очистки</b>\n\n"
        "Выберите что нужно очистить:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Старые посты", callback_data="clean_old")],
        [InlineKeyboardButton("📝 Очередь постов", callback_data="clean_pending")],
        [InlineKeyboardButton("✅ Обработанные", callback_data="clean_sent")],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
    ])
    
    await query.edit_message_text(
        clean_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def start_preview_mode(query, context):
    """Запустить режим превью"""
    try:
        if not state["pending"]:
            await query.edit_message_text("📭 Нет постов для просмотра")
            return
        
        # Создаем список для превью (сортируем по дате)
        preview_list = sorted(
            state["pending"].keys(),
            key=lambda x: state["pending"][x].get("timestamp", ""),
            reverse=True
        )
        
        state["preview_mode"] = {
            "list": preview_list,
            "current": 0
        }
        save_state()
        
        # Показываем первый пост без удаления сообщения
        first_record = state["pending"].get(preview_list[0])
        if first_record:
            await send_preview(
                context.bot,
                first_record,
                query.message.chat.id,
                0,
                len(preview_list),
                query.message.message_id
            )
        
    except Exception as e:
        logging.error(f"Ошибка в start_preview_mode: {e}")
        try:
            await query.edit_message_text("❌ Произошла ошибка при запуске превью")
        except:
            await query.answer("❌ Произошла ошибка при запуске превью")

async def show_status_info(query):
    """Показать статус бота"""
    try:
        pending_count = len(state["pending"])
        sent_count = len(state["sent_links"])
        scheduled_count = len(state.get("scheduled_posts", {}))
        
        # Следующий запланированный пост
        next_scheduled = None
        if state.get("scheduled_posts"):
            next_post = min(
                state["scheduled_posts"].items(),
                key=lambda x: x[1]["time"]
            )
            next_time = datetime.fromisoformat(next_post[1]["time"].replace('Z', '+00:00'))
            local_time = localize_datetime(next_time)
            next_scheduled = f"⏰ Следующий пост: {local_time.strftime('%d.%m %H:%M')} ({state.get('timezone', DEFAULT_TIMEZONE)})"
        
        # Последние 3 поста
        recent_posts = sorted(
            state["pending"].values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:3]
        
        status_text = (
            f"📊 <b>Статус бота:</b>\n\n"
            f"📝 Постов в ожидании: {pending_count}\n"
            f"⏰ Запланировано: {scheduled_count}\n"
            f"✅ Опубликовано: {sent_count}\n"
            f"📢 Канал: <code>{state.get('channel', TELEGRAM_CHANNEL)}</code>\n"
        )
        
        if next_scheduled:
            status_text += f"\n{next_scheduled}\n"
        
        if recent_posts:
            status_text += "\n🆕 <b>Последние посты:</b>\n"
            for post in recent_posts:
                emoji = "👟" if post.get("category") == "sneakers" else "👔"
                date = format_date_for_display(post.get("timestamp", ""))
                status_text += f"{emoji} {date} - {post['title'][:40]}...\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
        
        await query.edit_message_text(
            status_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Ошибка в show_status_info: {e}")
        await query.edit_message_text("❌ Произошла ошибка")

async def show_scheduled_posts(query):
    """Показать запланированные посты с возможностью редактирования"""
    try:
        scheduled = state.get("scheduled_posts", {})
        
        if not scheduled:
            text = "📭 <b>Нет запланированных постов</b>"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
            ])
        else:
            text = "📅 <b>Запланированные посты:</b>\n\n"
            keyboard_buttons = []
            
            for post_id, info in sorted(scheduled.items(), key=lambda x: x[1]["time"]):
                scheduled_time = datetime.fromisoformat(info["time"].replace('Z', '+00:00'))
                local_time = localize_datetime(scheduled_time)
                record = info["record"]
                
                text += (
                    f"⏰ {local_time.strftime('%d.%m %H:%M')} ({state.get('timezone', DEFAULT_TIMEZONE)})\n"
                    f"📝 {record['title'][:50]}...\n"
                    f"📍 {record.get('source', 'Unknown')}\n\n"
                )
                
                # Кнопки для каждого поста
                keyboard_buttons.append([
                    InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_schedule:{post_id}"),
                    InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_schedule:{post_id}")
                ])
            
            keyboard_buttons.append([InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")])
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logging.error(f"Ошибка в show_scheduled_posts: {e}")
        await query.edit_message_text("❌ Произошла ошибка")

async def show_auto_publish_menu(query):
    """Меню авто-публикации"""
    is_enabled = state.get("auto_publish", False)
    interval = state.get("publish_interval", 3600) // 60  # В минутах
    favorites_count = len(state.get("favorites", []))
    
    text = (
        f"🤖 <b>Автоматическая публикация</b>\n\n"
        f"Статус: {'✅ Включена' if is_enabled else '❌ Выключена'}\n"
        f"Интервал: {interval} минут\n"
        f"Постов в избранном: {favorites_count}\n\n"
        f"Бот будет автоматически публиковать посты из избранного с заданным интервалом"
    )
    
    keyboard_buttons = [
        [InlineKeyboardButton(
            "🔴 Выключить" if is_enabled else "🟢 Включить",
            callback_data="auto_toggle"
        )],
        [
            InlineKeyboardButton("30 мин", callback_data="auto_interval:1800"),
            InlineKeyboardButton("1 час", callback_data="auto_interval:3600"),
            InlineKeyboardButton("2 часа", callback_data="auto_interval:7200")
        ],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
    ]
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def show_thoughts_prompt(query):
    """Показать инструкцию для создания мыслей"""
    thoughts_text = (
        "💭 <b>Создание поста-размышления</b>\n\n"
        "Для создания личного поста используйте команду:\n"
        "<code>/thoughts описание темы</code>\n\n"
        "📝 <b>Пример:</b>\n"
        "<code>/thoughts новые Jordan 4 в черном цвете</code>\n\n"
        "📸 После команды можно прикрепить изображение для анализа\n\n"
        "💡 Бот создаст пост в личном стиле с эмоциями и впечатлениями"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
    ])
    
    await query.edit_message_text(
        thoughts_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def show_filter_menu(query):
    """Показать меню фильтров"""
    # Собираем все уникальные теги
    all_brands = set()
    all_models = set()
    all_types = set()
    
    for post in state["pending"].values():
        tags = post.get("tags", {})
        all_brands.update(tags.get("brands", []))
        all_models.update(tags.get("models", []))
        all_types.update(tags.get("types", []))
    
    keyboard_buttons = []
    
    # Кнопки брендов
    if all_brands:
        brand_buttons = []
        for brand in sorted(all_brands)[:3]:  # Показываем первые 3
            brand_buttons.append(
                InlineKeyboardButton(
                    brand.title(), 
                    callback_data=f"filter_brand:{brand}"
                )
            )
        keyboard_buttons.append(brand_buttons)
    
    # Кнопки моделей
    if all_models:
        model_buttons = []
        for model in sorted(all_models)[:3]:
            model_buttons.append(
                InlineKeyboardButton(
                    model.upper(), 
                    callback_data=f"filter_model:{model}"
                )
            )
        keyboard_buttons.append(model_buttons)
    
    # Кнопки типов
    if all_types:
        type_buttons = []
        for rtype in sorted(all_types)[:3]:
            type_buttons.append(
                InlineKeyboardButton(
                    rtype.title(), 
                    callback_data=f"filter_type:{rtype}"
                )
            )
        keyboard_buttons.append(type_buttons)
    
    keyboard_buttons.extend([
        [InlineKeyboardButton("🔄 Сбросить фильтры", callback_data="filter_reset")],
        [InlineKeyboardButton("◀️ Назад", callback_data="preview_close")]
    ])
    
    await query.edit_message_text(
        "🏷 <b>Фильтр по тегам</b>\n\n"
        "Выберите тег для фильтрации:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

async def filter_posts_by_tag(query, context, tag_type: str, tag_value: str):
    """Фильтрация постов по тегу"""
    filtered_posts = []
    
    for uid, post in state["pending"].items():
        tags = post.get("tags", {})
        if tag_type == "brand" and tag_value in tags.get("brands", []):
            filtered_posts.append(uid)
        elif tag_type == "model" and tag_value in tags.get("models", []):
            filtered_posts.append(uid)
        elif tag_type == "type" and tag_value in tags.get("types", []):
            filtered_posts.append(uid)
    
    if not filtered_posts:
        await query.edit_message_text(f"📭 Нет постов с тегом {tag_value}")
        return
    
    # Сортируем по дате
    filtered_posts.sort(
        key=lambda x: state["pending"][x].get("timestamp", ""),
        reverse=True
    )
    
    state["preview_mode"] = {
        "list": filtered_posts,
        "current": 0,
        "filter": {tag_type: tag_value}
    }
    save_state()
    
    await query.edit_message_text(
        f"✅ Найдено {len(filtered_posts)} постов с тегом {tag_value}"
    )
    
    # Показываем первый пост
    first_record = state["pending"].get(filtered_posts[0])
    if first_record:
        await send_preview(
            context.bot,
            first_record,
            query.message.chat.id,
            0,
            len(filtered_posts)
        )

async def test_sources_inline(query, context):
    """Тестирование источников через inline кнопки"""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            results = []
            
            for idx, src in enumerate(SOURCES):
                try:
                    await query.edit_message_text(f"🔍 Тестирую источники... ({idx + 1}/{len(SOURCES)})\n📍 {src['name']}")
                    
                    resp = await client.get(src["api"], headers=headers, timeout=20)
                    resp.raise_for_status()
                    
                    if src["type"] == "rss":
                        try:
                            soup = BeautifulSoup(resp.text, "xml")
                            items = soup.find_all("item")
                        except:
                            soup = BeautifulSoup(resp.text, "html.parser")
                            items = soup.find_all("item")
                        
                        if not items:
                            items = soup.find_all("entry")
                        
                        count = len(items)
                        first_title = items[0].find("title").get_text(strip=True) if items else "Нет"
                        
                        results.append(f"✅ {src['name']} ({src.get('category', 'unknown')}):\n"
                                     f"   Записей: {count}\n"
                                     f"   Первая: {first_title[:40]}...")
                    else:
                        posts = resp.json()
                        count = len(posts) if isinstance(posts, list) else 0
                        
                        results.append(f"✅ {src['name']} ({src.get('category', 'unknown')}):\n"
                                     f"   Постов: {count}")
                    
                except Exception as e:
                    results.append(f"❌ {src['name']}: {type(e).__name__}")
            
            # Формируем итоговое сообщение
            final_text = "📊 <b>Результаты тестирования:</b>\n\n" + "\n\n".join(results)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
            ])
            
            await query.edit_message_text(
                final_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        
    except Exception as e:
        logging.error(f"Ошибка в test_sources_inline: {e}")
        await query.edit_message_text("❌ Произошла ошибка")

async def reset_state_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для сброса состояния (только для админа)"""
    try:
        user_id = update.message.from_user.id
        if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ Эта команда доступна только администратору")
            return
        
        # Создаем новое чистое состояние
        global state
        state = {
            "sent_links": [], 
            "pending": {}, 
            "moderation_queue": [], 
            "preview_mode": {}, 
            "thoughts_mode": False,
            "scheduled_posts": {},
            "generated_images": {},
            "waiting_for_image": None,
            "current_thought": None,
            "waiting_for_schedule": None,
            "editing_schedule": None,
            "favorites": [],
            "auto_publish": False,
            "publish_interval": 3600,
            "timezone": DEFAULT_TIMEZONE,
            "channel": TELEGRAM_CHANNEL,
            "waiting_for_channel": False
        }
        save_state()
        
        await update.message.reply_text(
            "✅ Состояние бота сброшено!\n\n"
            "Все посты очищены. Запустите /check для поиска новых релизов."
        )
        
    except Exception as e:
        logging.error(f"Ошибка в reset_state_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при сбросе состояния")

def main() -> None:
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).connect_timeout(30).read_timeout(30).build()
        
        # Добавляем обработчики команд
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("cancel", cancel_command))
        app.add_handler(CommandHandler("thoughts", thoughts_command))
        app.add_handler(CommandHandler("skip", skip_command))
        app.add_handler(CommandHandler("reset_state", reset_state_command))
        
        # Обработчики для фото и текста
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Обработчик callback
        app.add_handler(CallbackQueryHandler(on_callback))
        
        # Запускаем периодическую проверку
        app.job_queue.run_repeating(
            check_releases_job,
            interval=CHECK_INTERVAL_SECONDS,
            first=30
        )
        
        logging.info("=== HypeBot запущен ===")
        logging.info(f"Admin ID: {ADMIN_CHAT_ID if ADMIN_CHAT_ID else 'Не установлен'}")
        logging.info(f"Channel: {state.get('channel', TELEGRAM_CHANNEL)}")
        logging.info(f"Timezone: {state.get('timezone', DEFAULT_TIMEZONE)}")
        logging.info(f"Источников: {len(SOURCES)}")
        logging.info("Новые функции: настройки канала, временные зоны, улучшенные промпты")
        
        try:
            app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        except Conflict:
            logging.critical("Бот уже запущен в другом процессе.")
            return
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()