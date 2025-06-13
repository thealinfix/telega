import logging
from telegram import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest
import httpx
from . import config, utils, fetcher
from .state import state, save_state
from .openai_utils import openai_client

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
        hashtags = utils.get_hashtags(record.get("title", ""), record.get("category", "sneakers"))
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
        images_to_use = images[:config.MAX_IMAGES_PER_POST]
        
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
    date_str = utils.format_date_for_display(record.get("timestamp", ""))
    
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
        tags = utils.extract_tags(record.get("title", ""), record.get("context", ""))
        # Сохраняем теги в запись
        if record["id"] in state["pending"]:
            state["pending"][record["id"]]["tags"] = tags
            save_state()
    
    tags_display = utils.format_tags_for_display(tags)
    
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
                record = await fetcher.parse_full_content(client, record)
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
    date_str = utils.format_date_for_display(record.get("timestamp", ""))
    hashtags = utils.get_hashtags(record.get("title", ""), record.get("category", "sneakers"))
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
            await bot.send_media_group(config.ADMIN_CHAT_ID, media)
            await bot.send_message(
                config.ADMIN_CHAT_ID,
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        else:
            await bot.send_message(
                config.ADMIN_CHAT_ID,
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
    channel = state.get("channel", config.TELEGRAM_CHANNEL)
    
    try:
        media = build_media_group(record, for_channel=True)
        if media:
            await bot.send_media_group(channel, media)
        else:
            category_emoji = "👟" if record.get("category") == "sneakers" else "👔"
            hashtags = utils.get_hashtags(record.get("title", ""), record.get("category", "sneakers"))
            
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

