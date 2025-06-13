import logging
import asyncio
from datetime import datetime, timezone, timedelta
import httpx
import re
import pytz
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from . import config, state, utils
from .openai_utils import generate_image, analyze_image
from .messaging import (
    gen_caption,
    build_media_group,
    send_preview,
    send_full_post,
    send_for_moderation,
    publish_release,
)
from .tasks import check_releases_job


async def thoughts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для создания поста-размышления"""
    try:
        user_id = update.message.from_user.id
        if config.ADMIN_CHAT_ID and user_id != config.ADMIN_CHAT_ID:
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
        state.save_state()
        
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
        state.save_state()
        
        if waiting_data["type"] == "thoughts":
            # Генерируем мысли без изображения
            msg = await update.message.reply_text("💭 Генерирую мысли...")
            
            thought_text = await gen_caption(
                waiting_data["topic"], 
                "", 
                "sneakers", 
                is_thought=True
            )
            
            hashtags = utils.get_hashtags(waiting_data["topic"], "sneakers")
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
            state.save_state()
            
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
        if config.ADMIN_CHAT_ID and user_id != config.ADMIN_CHAT_ID:
            return
        
        waiting_data = state["waiting_for_image"]
        state["waiting_for_image"] = None
        state.save_state()
        
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
            
            hashtags = utils.get_hashtags(waiting_data["topic"], "sneakers")
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
            state.save_state()
            
            await msg.edit_text(
                f"💭 <b>Пост-размышление:</b>\n\n{final_text}\n\n"
                f"📸 Изображение прикреплено",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        
    except Exception as e:
        logging.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке изображения")

# Обработчики команд
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info(f"Команда /start от пользователя {update.message.from_user.id}")
        is_admin = not config.ADMIN_CHAT_ID or update.message.from_user.id == config.ADMIN_CHAT_ID
        
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
        if config.ADMIN_CHAT_ID and user_id != config.ADMIN_CHAT_ID:
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
                state.save_state()
                
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
            scheduled_time = utils.parse_schedule_time(text)
            if scheduled_time:
                post_id = state["waiting_for_schedule"]
                record = state["pending"].get(post_id)
                
                if record:
                    state["scheduled_posts"][post_id] = {
                        "time": scheduled_time.isoformat(),
                        "record": record
                    }
                    
                    state["waiting_for_schedule"] = None
                    state.save_state()
                    
                    local_time = state.localize_datetime(scheduled_time)
                    await update.message.reply_text(
                        f"✅ Пост запланирован на {local_time.strftime('%d.%m.%Y %H:%M')} ({state.get('timezone', config.DEFAULT_TIMEZONE)})\n"
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
            scheduled_time = utils.parse_schedule_time(text)
            if scheduled_time:
                post_id = state["editing_schedule"]
                
                if post_id in state.get("scheduled_posts", {}):
                    state["scheduled_posts"][post_id]["time"] = scheduled_time.isoformat()
                    state["editing_schedule"] = None
                    state.save_state()
                    
                    local_time = state.localize_datetime(scheduled_time)
                    await update.message.reply_text(
                        f"✅ Время изменено на {local_time.strftime('%d.%m.%Y %H:%M')} ({state.get('timezone', config.DEFAULT_TIMEZONE)})"
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
                    state.save_state()
                    
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
                    state.save_state()
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
    if config.ADMIN_CHAT_ID and user_id != config.ADMIN_CHAT_ID:
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

    state.save_state()

    if cancelled:
        await update.message.reply_text(f"❌ Отменено: {', '.join(cancelled)}")
    else:
        await update.message.reply_text("❌ Нечего отменять")

async def reset_state_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для сброса состояния (только для админа)"""
    try:
        user_id = update.message.from_user.id
        if config.ADMIN_CHAT_ID and user_id != config.ADMIN_CHAT_ID:
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
            "timezone": config.DEFAULT_TIMEZONE,
            "channel": config.TELEGRAM_CHANNEL,
            "waiting_for_channel": False
        }
        state.save_state()
        
        await update.message.reply_text(
            "✅ Состояние бота сброшено!\n\n"
            "Все посты очищены. Запустите /check для поиска новых релизов."
        )
        
    except Exception as e:
        logging.error(f"Ошибка в reset_state_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при сбросе состояния")

