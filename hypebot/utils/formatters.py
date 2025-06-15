"""
Text formatting utilities
"""
from typing import Dict, List, Optional, TYPE_CHECKING
from telegram.constants import ParseMode

from ..config.constants import HASHTAGS, SOURCE_EMOJIS

if TYPE_CHECKING:
    from ..models.post import Post, PostTags


def format_tags_for_display(tags: 'PostTags') -> str:
    """Format tags for display in message"""
    result = []
    
    if tags.brands:
        result.append(f"🏷 Бренд: {', '.join(tags.brands)}")
    if tags.models:
        result.append(f"👟 Модель: {', '.join(tags.models)}")
    if tags.types:
        result.append(f"📌 Тип: {', '.join(tags.types)}")
    if tags.colors:
        result.append(f"🎨 Цвет: {', '.join(tags.colors)}")
    
    return "\n".join(result) if result else ""


def get_hashtags_for_post(title: str, category: str) -> str:
    """Generate hashtags based on post title and category"""
    title_lower = title.lower()
    
    hashtag_dict = HASHTAGS.get(category, HASHTAGS.get("sneakers", {}))
    
    # Check for brand-specific hashtags
    for brand, tags in hashtag_dict.items():
        if brand == "default":
            continue
            
        # Special cases
        if brand == "jordan" and "air jordan" in title_lower:
            return tags
        elif brand == "offwhite" and "off-white" in title_lower:
            return tags
        elif brand in title_lower:
            return tags
    
    # Return default hashtags
    return hashtag_dict.get("default", "")


def format_post_for_channel(post: 'Post') -> str:
    """Format post for channel publication"""
    category_emoji = "👟" if post.category == "sneakers" else "👔"
    hashtags = post.get_hashtags()
    
    # Get source emoji
    source_emoji = SOURCE_EMOJIS.get(post.source, "📍")
    source_text = f"\n\n{source_emoji} {post.source}"
    
    text = (
        f"{category_emoji} <b>{post.title}</b>\n\n"
        f"{post.description}{source_text}\n\n"
        f"🔗 <a href=\"{post.link}\">Читать полностью</a>\n\n"
        f"{hashtags}"
    )
    
    return text


def format_preview_text(
    post: 'Post',
    current_idx: int,
    total: int,
    has_generated: bool,
    is_favorite: bool,
    generated_count: int,
    date_str: str,
    timezone_str: str
) -> str:
    """Format post preview text"""
    category_emoji = "👟" if post.category == "sneakers" else "👔"
    tags_display = format_tags_for_display(post.tags) if post.tags else ""
    
    total_images = generated_count + len(post.images) if has_generated else len(post.images)
    
    preview_text = (
        f"📅 <b>{date_str}</b>\n"
        f"{category_emoji} <b>{post.title}</b>\n\n"
    )
    
    if tags_display:
        preview_text += f"{tags_display}\n\n"
    
    preview_text += (
        f"📍 Источник: {post.source}\n"
        f"🔗 <a href=\"{post.link}\">Ссылка на статью</a>\n"
        f"🖼 Изображений: {total_images}\n"
    )
    
    if has_generated:
        preview_text += f"🎨 Сгенерировано: {generated_count}\n"
    
    if is_favorite:
        preview_text += "⭐️ В избранном\n"
    
    preview_text += f"\n📊 Пост {current_idx + 1} из {total}"
    
    return preview_text


def format_moderation_text(
    post: 'Post',
    date_str: str,
    generated_count: int,
    original_count: int,
    timezone_str: str
) -> str:
    """Format post for moderation"""
    category_emoji = "👟" if post.category == "sneakers" else "👔"
    hashtags = post.get_hashtags()
    source_info = f"\n📍 Источник: {post.source}"
    link_info = f"\n🔗 Статья: {post.link}"
    
    # Image info
    img_info = ""
    if generated_count > 0:
        img_info = f"\n🎨 Сгенерировано: {generated_count}, оригинальных: {original_count}"
    else:
        img_info = f"\n🖼 Изображений: {original_count}"
    
    text = (
        f"📅 {date_str}\n"
        f"{category_emoji} <b>{post.title}</b>\n\n"
        f"{post.description[:400]}"
        f"{source_info}{link_info}{img_info}\n\n"
        f"{hashtags}\n\n"
        f"🆔 ID: {post.id}"
    )
    
    return text


def truncate_text(text: str, max_length: int = 1024, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    replacements = {
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def format_stats_text(
    pending_count: int,
    sent_count: int,
    scheduled_count: int,
    favorites_count: int,
    brand_stats: Dict[str, int],
    source_stats: Dict[str, int]
) -> str:
    """Format statistics text"""
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
    
    return stats_text


def format_scheduled_post_info(
    scheduled_time_str: str,
    post_title: str,
    post_source: str,
    timezone_str: str
) -> str:
    """Format scheduled post information"""
    return (
        f"⏰ {scheduled_time_str} ({timezone_str})\n"
        f"📝 {post_title[:50]}...\n"
        f"📍 {post_source}\n\n"
    )