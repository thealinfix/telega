"""
Menu handlers
"""
import logging
from datetime import datetime
from typing import Optional

# Common button text constants
BACK_TO_MENU_TEXT = "◀️ Назад в меню"

import pytz
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .base import BaseHandler
from ..config.constants import AVAILABLE_TIMEZONES
from ..utils.validators import is_admin
from ..utils.formatters import format_stats_text, format_scheduled_post_info
from ..utils.time_utils import format_local_time, localize_datetime
from ..utils.decorators import log_errors, answer_callback_query


class MenuHandler(BaseHandler):
    
    @log_errors
    @answer_callback_query
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
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
            [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status"""
        stats = self.state_manager.get_stats()
        
        # Next scheduled post
        next_scheduled = None
        if self.state.scheduled_posts:
            next_post = min(
                self.state.scheduled_posts.items(),
                key=lambda x: x[1].time
            )
            next_time = datetime.fromisoformat(next_post[1].time.replace('Z', '+00:00'))
            local_time = localize_datetime(next_time, self.state.timezone)
            next_scheduled = f"⏰ Следующий пост: {local_time.strftime('%d.%m %H:%M')} ({self.state.timezone})"
        
        # Recent posts
        recent_posts = sorted(
            self.state.pending.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )[:3]
        
        status_text = (
            f"📊 <b>Статус бота:</b>\n\n"
            f"📝 Постов в ожидании: {stats['pending_count']}\n"
            f"⏰ Запланировано: {stats['scheduled_count']}\n"
            f"✅ Опубликовано: {stats['sent_count']}\n"
            f"📢 Канал: <code>{self.state.channel}</code>\n"
        )
        
        if next_scheduled:
            status_text += f"\n{next_scheduled}\n"
        
        if recent_posts:
            status_text += "\n🆕 <b>Последние посты:</b>\n"
            for post in recent_posts:
                from ..utils.time_utils import format_date_for_display
                emoji = "👟" if post.category == "sneakers" else "👔"
                date = format_date_for_display(post.timestamp, self.state.timezone)
                status_text += f"{emoji} {date} - {post.title[:40]}...\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            status_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show statistics"""
        stats = self.state_manager.get_stats()
        
        stats_text = format_stats_text(
            stats['pending_count'],
            stats['sent_count'],
            stats['scheduled_count'],
            stats['favorites_count'],
            stats['brand_stats'],
            stats['source_stats']
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_scheduled_posts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show scheduled posts"""
        scheduled = self.state.scheduled_posts
        
        if not scheduled:
            text = "📭 <b>Нет запланированных постов</b>"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
            ])
        else:
            text = "📅 <b>Запланированные посты:</b>\n\n"
            keyboard_buttons = []
            
            for post_id, sched_post in sorted(scheduled.items(), key=lambda x: x[1].time):
                scheduled_time = sched_post.get_datetime()
                local_time = localize_datetime(scheduled_time, self.state.timezone)
                
                text += format_scheduled_post_info(
                    local_time.strftime('%d.%m %H:%M'),
                    sched_post.record.title,
                    sched_post.record.source
                )
                
                # Buttons for each post
                keyboard_buttons.append([
                    InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_schedule:{post_id}"),
            keyboard_buttons.append([InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")])
                ])
            
            keyboard_buttons.append([InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")])
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        current_channel = self.state.channel
        current_timezone = self.state.timezone
        
        settings_text = (
            "⚙️ <b>Настройки бота</b>\n\n"
            f"📢 Канал публикации: <code>{current_channel}</code>\n"
            f"🕐 Временная зона: {current_timezone}\n"
            f"📅 Текущее время: {datetime.now(pytz.timezone(current_timezone)).strftime('%H:%M')}\n"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Изменить канал", callback_data="settings_channel")],
            [InlineKeyboardButton("🕐 Изменить временную зону", callback_data="settings_timezone")],
            [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_timezone_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show timezone selection menu"""
        keyboard_buttons = []
        for name, tz in AVAILABLE_TIMEZONES:
            callback_data = f"tz_{tz.replace('/', '_')}"
            keyboard_buttons.append([InlineKeyboardButton(name, callback_data=callback_data)])
        
        keyboard_buttons.append([InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_settings")])
        
        await update.callback_query.edit_message_text(
            "🕐 <b>Выберите временную зону:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
    
    @log_errors
    @answer_callback_query
    async def show_auto_publish_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show auto-publish menu"""
        is_enabled = self.state.auto_publish
        interval = self.state.publish_interval // 60  # In minutes
        favorites_count = len(self.state.favorites)
        
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
            [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
        ]
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_clean_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show clean menu"""
        clean_text = (
            "🧹 <b>Меню очистки</b>\n\n"
            "Выберите что нужно очистить:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Старые посты", callback_data="clean_old")],
            [InlineKeyboardButton("📝 Очередь постов", callback_data="clean_pending")],
            [InlineKeyboardButton("✅ Обработанные", callback_data="clean_sent")],
            [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            clean_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_tools_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show tools menu"""
        tools_text = (
            "🔧 <b>Инструменты</b>\n\n"
            "Дополнительные функции для администратора:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Тест источников", callback_data="tool_test_sources")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            tools_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @log_errors
    @answer_callback_query
    async def show_thoughts_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show thoughts creation prompt"""
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
            [InlineKeyboardButton(BACK_TO_MENU_TEXT, callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            thoughts_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )


def create_moderation_keyboard(post_id: str) -> InlineKeyboardMarkup:
    """Create moderation keyboard for post"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve:{post_id}")],
        [InlineKeyboardButton("🔄 Перегенерировать текст", callback_data=f"regen:{post_id}")],
        [
            InlineKeyboardButton("🎨 Генерировать обложку", callback_data=f"gen_cover_full:{post_id}"),
            InlineKeyboardButton("✏️ Свой промпт", callback_data=f"custom_prompt:{post_id}")
        ],
        [
            InlineKeyboardButton("↩️ Вернуть оригинал", callback_data=f"revert_img:{post_id}"),
            InlineKeyboardButton("❌ Пропустить", callback_data=f"reject:{post_id}")
        ],
        [
            InlineKeyboardButton("◀️ Вернуться к превью", callback_data=f"back_preview:{post_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="cmd_back_main")
        ]
    ])

class MenuHandler(BaseHandler):
    # ... (other methods remain unchanged)

    @log_errors
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        # Determine if message or callback
        if update.message:
            user_id = update.message.from_user.id
            reply_func = update.message.reply_text
        else:
            user_id = update.callback_query.from_user.id
            reply_func = update.callback_query.edit_message_text

        is_admin_user = is_admin(user_id, self.admin_id)

        # Base buttons for all users
        keyboard_buttons = [
            [InlineKeyboardButton("📊 Статус бота", callback_data="cmd_status")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="cmd_help")]
        ]

        if is_admin_user:
            # Admin buttons
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

        if is_admin_user:
            welcome_text += "\n\n🔐 <i>Вы вошли как администратор</i>"

        await reply_func(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )