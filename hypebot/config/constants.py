"""
Constants and static data for HypeBot
"""
from typing import Dict, List


# Hashtags for posts
HASHTAGS: Dict[str, Dict[str, str]] = {
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

# Brand detection keywords
BRAND_KEYWORDS: Dict[str, List[str]] = {
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

# Sneaker model keywords
MODEL_KEYWORDS: Dict[str, List[str]] = {
    "airmax": ["air max", "airmax", "am1", "am90", "am95", "am97"],
    "airforce": ["air force", "af1", "air force 1"],
    "dunk": ["dunk", "dunk low", "dunk high", "sb dunk"],
    "yeezy": ["yeezy", "boost 350", "boost 700", "foam runner"],
    "jordan1": ["jordan 1", "aj1", "air jordan 1"],
    "jordan4": ["jordan 4", "aj4", "air jordan 4"],
    "ultraboost": ["ultraboost", "ultra boost"],
    "990": ["990", "990v", "990v5", "990v6"]
}

# Release type keywords
RELEASE_TYPES: Dict[str, List[str]] = {
    "retro": ["retro", "og", "original", "vintage"],
    "collab": ["collab", "collaboration", "x ", " x ", "partner"],
    "limited": ["limited", "exclusive", "rare", "special edition"],
    "womens": ["women", "wmns", "female"],
    "kids": ["kids", "gs", "gradeschool", "youth"],
    "lifestyle": ["lifestyle", "casual", "street"],
    "performance": ["performance", "running", "basketball", "training"]
}

# Source emojis
SOURCE_EMOJIS: Dict[str, str] = {
    "SneakerNews": "📰",
    "Hypebeast": "🔥",
    "Highsnobiety": "💎",
    "Hypebeast Footwear": "👟",
    "Hypebeast Fashion": "👔",
    "Highsnobiety Sneakers": "✨",
    "Highsnobiety Fashion": "🎨"
}

# Timezones for settings
AVAILABLE_TIMEZONES = [
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

# Color keywords for tag extraction
COLOR_KEYWORDS = [
    "black", "white", "red", "blue", "green", "yellow", "purple", "pink", 
    "orange", "grey", "gray", "черный", "белый", "красный", "синий", 
    "зеленый", "желтый", "фиолетовый", "розовый", "оранжевый", "серый"
]

# Validation patterns
VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

# API Models fallback order
OPENAI_MODELS = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]

# System prompts
CAPTION_SYSTEM_PROMPT = """Ты — автор Telegram-канала про кроссовки и уличную моду. Твоя задача — писать короткие, цепляющие и стильные посты о релизах, трендах и коллаборациях. 

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

THOUGHTS_SYSTEM_PROMPT = """Ты ведешь личный блог о кроссовках и уличной моде. Пиши от первого лица, как будто делишься своими мыслями с друзьями. Стиль непринужденный, с эмоциями и личным отношением. 

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