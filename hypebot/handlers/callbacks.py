"""
Callback query handlers
"""
import logging
import asyncio
from datetime import datetime

import pytz
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from .base import BaseHandler
from .menu import MenuHandler, create_moderation_keyboard
from ..models.post import ThoughtPost
from ..utils.decorators import log_errors, answer_callback_query, admin_only
from ..utils.formatters import get_hashtags_for_post
from ..utils.time_utils import localize_datetime


class CallbackHandler(BaseHandler):
    """Handles callback queries"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.menu_handler = MenuHandler(*args, **kwargs)
    
    @log_errors
    @answer_callback_query
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main callback handler"""
        query = update.callback_query
        data = query.data
        
        # Route to appropriate handler
        if data.startswith("cmd_"):
            await self._handle_command_callbacks(update, context, data)
        elif data.startswith("settings_"):
            await self._handle_settings_callbacks(update, context, data)
        elif data.startswith("tz_"):
            await self._handle_timezone_callbacks(update, context, data)
        elif data.startswith("auto_"):
            await self._handle_auto_publish_callbacks(update, context, data)
        elif data.startswith("clean_"):
            await self._handle_clean_callbacks(update, context, data)
        elif data.startswith("tool_"):
            await self._handle_tools_callbacks(update, context, data)
        elif data.startswith("schedule:") or data.startswith("edit_schedule:") or data.startswith("delete_schedule:"):
            await self._handle_schedule_callbacks(update, context, data)
        elif data.startswith("toggle_fav:"):
            await self._handle_favorite_callbacks(update, context, data)
        elif data.startswith("filter_"):
            await self._handle_filter_callbacks(update, context, data)
        elif data.startswith("preview_"):
            await self._handle_preview_callbacks(update, context, data)
        elif data.startswith("gen_"):
            await self._handle_generation_callbacks(update, context, data)
        elif data in ["publish_thought", "regen_thought", "cancel_thought"]:
            await self._handle_thought_callbacks(update, context, data)
        elif data == "noop":
            # No operation
            return
        else:
            # Moderation actions
            await self._handle_moderation_callbacks(update, context, data)
    
    @admin_only(None)
    async def _handle_command_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle command menu callbacks"""
        if data == "cmd_status":
            await self.menu_handler.show_status(update, context)
        elif data == "cmd_help":
            await self.menu_handler.show_help(update, context)
        elif data == "cmd_preview":
            from .preview import PreviewHandler
            preview_handler = PreviewHandler(
                self.config,
                self.state_manager,
                self.ai_service,
                self.image_service,
                self.publisher_service,
                self.content_fetcher
            )
            await preview_handler.start_preview_mode(update, context)
        elif data == "cmd_check":
            await update.callback_query.edit_message_text("🔄 Запускаю проверку новых релизов...")
            from ..bot import check_releases_job
            asyncio.create_task(check_releases_job(context, None))  # Will need to pass bot instance
        elif data == "cmd_thoughts":
            await self.menu_handler.show_thoughts_prompt(update, context)
        elif data == "cmd_scheduled":
            await self.menu_handler.show_scheduled_posts(update, context)
        elif data == "cmd_stats":
            await self.menu_handler.show_stats(update, context)
        elif data == "cmd_auto_menu":
            await self.menu_handler.show_auto_publish_menu(update, context)
        elif data == "cmd_settings":
            await self.menu_handler.show_settings_menu(update, context)
        elif data == "cmd_clean_menu":
            await self.menu_handler.show_clean_menu(update, context)
        elif data == "cmd_tools_menu":
            await self.menu_handler.show_tools_menu(update, context)
        elif data == "cmd_back_main":
            await self.menu_handler.show_main_menu(update, context)
    
    @admin_only(None)
    async def _handle_settings_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle settings callbacks"""
        if data == "settings_channel":
            self.state.waiting.waiting_for_channel = True
            self.save_state()
            
            await update.callback_query.edit_message_text(
                "📢 <b>Изменение канала публикации</b>\n\n"
                "Отправьте новый канал в формате:\n"
                "• <code>@channelname</code> - для публичного канала\n"
                "• <code>-1001234567890</code> - для приватного канала (ID чата)\n\n"
                f"Текущий канал: <code>{self.state.channel}</code>\n\n"
                "Или /cancel для отмены",
                parse_mode=ParseMode.HTML
            )
        elif data == "settings_timezone":
            await self.menu_handler.show_timezone_menu(update, context)
    
    @admin_only(None)
    async def _handle_timezone_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle timezone selection"""
        timezone_name = data.replace("tz_", "").replace("_", "/")
        self.state_manager.update_settings(timezone=timezone_name)
        
        await update.callback_query.edit_message_text(
            f"✅ Временная зона изменена на {timezone_name}\n\n"
            f"Текущее время: {datetime.now(pytz.timezone(timezone_name)).strftime('%H:%M')}",
            parse_mode=ParseMode.HTML
        )
    
    @admin_only(None)
    async def _handle_auto_publish_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle auto-publish callbacks"""
        if data == "auto_toggle":
            new_state = not self.state.auto_publish
            self.state_manager.update_settings(auto_publish=new_state)
            await self.menu_handler.show_auto_publish_menu(update, context)
        
        elif data.startswith("auto_interval:"):
            interval = int(data.split(":")[1])
            self.state_manager.update_settings(publish_interval=interval)
            await self.menu_handler.show_auto_publish_menu(update, context)
    
    @admin_only(None)
    async def _handle_clean_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle clean menu callbacks"""
        if data == "clean_old":
            before_count = len(self.state.pending)
            old_removed, limit_removed = self.state_manager.clean_old_data()
            after_count = len(self.state.pending)
            
            await update.callback_query.edit_message_text(
                f"🗑 <b>Очистка завершена:</b>\n\n"
                f"Было постов: {before_count}\n"
                f"Удалено старых: {old_removed}\n"
                f"Удалено по лимиту: {limit_removed}\n"
                f"Осталось: {after_count}\n\n"
                f"Удаляются посты старше {self.config.max_post_age_days} дней",
                parse_mode=ParseMode.HTML
            )
        
        elif data == "clean_pending":
            count = len(self.state.pending)
            self.state.pending.clear()
            self.state.preview_mode = None
            self.state.generated_images.clear()
            self.save_state()
            
            await update.callback_query.edit_message_text(f"🗑 Очищено {count} постов из очереди")
        
        elif data == "clean_sent":
            count = len(self.state.sent_links)
            self.state.sent_links.clear()
            self.save_state()
            
            await update.callback_query.edit_message_text(f"🗑 Очищен список обработанных: {count} записей")
    
    @admin_only(None)
    async def _handle_tools_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle tools callbacks"""
        if data == "tool_test_sources":
            await update.callback_query.edit_message_text("🔍 Тестирую источники...")
            await self._test_sources_inline(update, context)
    
    async def _test_sources_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test all sources"""
        from ..config.sources import SOURCES
        
        results = []
        
        for idx, source in enumerate(SOURCES):
            try:
                await update.callback_query.edit_message_text(
                    f"🔍 Тестирую источники... ({idx + 1}/{len(SOURCES)})\n📍 {source['name']}"
                )
                
                # Simple connectivity test
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(source["api"], timeout=10)
                    status = "✅" if resp.status_code == 200 else f"❌ {resp.status_code}"
                    results.append(f"{status} {source['name']} ({source['category']})")
            
            except Exception as e:
                results.append(f"❌ {source['name']}: {type(e).__name__}")
        
        # Final results
        final_text = "📊 <b>Результаты тестирования:</b>\n\n" + "\n".join(results)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
        
        await update.callback_query.edit_message_text(
            final_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    @admin_only(None)
    async def _handle_schedule_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle scheduling callbacks"""
        if data.startswith("schedule:"):
            uid = data.split(":")[1]
            self.state.waiting.waiting_for_schedule = uid
            self.save_state()
            
            user_tz = pytz.timezone(self.state.timezone)
            await update.callback_query.edit_message_text(
                f"⏰ <b>Планирование публикации</b>\n\n"
                f"Ваша временная зона: {self.state.timezone}\n"
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
        
        elif data.startswith("edit_schedule:"):
            post_id = data.split(":")[1]
            self.state.waiting.editing_schedule = post_id
            self.save_state()
            
            schedule_info = self.state.scheduled_posts.get(post_id)
            if schedule_info:
                scheduled_time = schedule_info.get_datetime()
                local_time = localize_datetime(scheduled_time, self.state.timezone)
                user_tz = pytz.timezone(self.state.timezone)
                
                await update.callback_query.edit_message_text(
                    f"📝 <b>Изменение времени публикации</b>\n\n"
                    f"Текущее время: {local_time.strftime('%d.%m.%Y %H:%M')} ({self.state.timezone})\n"
                    f"Сейчас: {datetime.now(user_tz).strftime('%H:%M')}\n\n"
                    f"Отправьте новое время в формате:\n"
                    f"• <code>18:30</code> - сегодня в 18:30\n"
                    f"• <code>25.12 15:00</code> - конкретная дата\n"
                    f"• <code>+2h</code> - через 2 часа\n\n"
                    f"Или /cancel для отмены",
                    parse_mode=ParseMode.HTML
                )
        
        elif data.startswith("delete_schedule:"):
            post_id = data.split(":")[1]
            self.state_manager.unschedule_post(post_id)
            await update.callback_query.edit_message_text("✅ Пост удален из расписания")
    
    async def _handle_favorite_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle favorite toggles"""
        uid = data.split(":")[1]
        is_favorite = self.state_manager.toggle_favorite(uid)
        
        # Update preview if active
        if self.state.preview_mode and uid in self.state.preview_mode.list:
            from .preview import PreviewHandler
            preview_handler = PreviewHandler(
                self.config,
                self.state_manager,
                self.ai_service,
                self.image_service,
                self.publisher_service,
                self.content_fetcher
            )
            
            idx = self.state.preview_mode.list.index(uid)
            post = self.state_manager.get_post(uid)
            
            if post:
                await preview_handler.send_preview(
                    context.bot,
                    post,
                    update.callback_query.message.chat.id,
                    idx,
                    len(self.state.preview_mode.list),
                    update.callback_query.message.message_id
                )
    
    async def _handle_filter_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle filter callbacks"""
        if data == "filter_tags":
            await self._show_filter_menu(update, context)
        
        elif data.startswith("filter_brand:") or data.startswith("filter_model:") or data.startswith("filter_type:"):
            parts = data.split(":")
            filter_type = parts[0].replace("filter_", "")
            filter_value = parts[1]
            
            await self._filter_posts_by_tag(update, context, filter_type, filter_value)
        
        elif data == "filter_reset":
            # Reset filters
            preview_list = sorted(
                self.state.pending.keys(),
                key=lambda x: self.state.pending[x].timestamp,
                reverse=True
            )
            
            from ..models.state import PreviewMode
            self.state.preview_mode = PreviewMode(
                list=preview_list,
                current=0,
                filter=None
            )
            self.save_state()
            
            await update.callback_query.edit_message_text("✅ Фильтры сброшены")
            
            if preview_list:
                from .preview import PreviewHandler
                preview_handler = PreviewHandler(
                    self.config,
                    self.state_manager,
                    self.ai_service,
                    self.image_service,
                    self.publisher_service,
                    self.content_fetcher
                )
                
                first_post = self.state_manager.get_post(preview_list[0])
                if first_post:
                    await preview_handler.send_preview(
                        context.bot,
                        first_post,
                        update.callback_query.message.chat.id,
                        0,
                        len(preview_list)
                    )
    
    async def _show_filter_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show filter menu"""
        all_tags = self.tag_extractor.get_all_unique_tags(self.state.pending)
        
        keyboard_buttons = []
        
        # Brand buttons
        if all_tags["brands"]:
            brand_buttons = []
            for brand in all_tags["brands"][:3]:
                brand_buttons.append(
                    InlineKeyboardButton(
                        brand.title(),
                        callback_data=f"filter_brand:{brand}"
                    )
                )
            keyboard_buttons.append(brand_buttons)
        
        # Model buttons
        if all_tags["models"]:
            model_buttons = []
            for model in all_tags["models"][:3]:
                model_buttons.append(
                    InlineKeyboardButton(
                        model.upper(),
                        callback_data=f"filter_model:{model}"
                    )
                )
            keyboard_buttons.append(model_buttons)
        
        # Type buttons
        if all_tags["types"]:
            type_buttons = []
            for rtype in all_tags["types"][:3]:
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
        
        await update.callback_query.edit_message_text(
            "🏷 <b>Фильтр по тегам</b>\n\n"
            "Выберите тег для фильтрации:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
    
    async def _filter_posts_by_tag(self, update: Update, context: ContextTypes.DEFAULT_TYPE, tag_type: str, tag_value: str):
        """Filter posts by tag"""
        filtered_posts = []
        
        for uid, post in self.state.pending.items():
            if post.tags and self.tag_extractor.matches_filter(post.tags, tag_type, tag_value):
                filtered_posts.append(uid)
        
        if not filtered_posts:
            await update.callback_query.edit_message_text(f"📭 Нет постов с тегом {tag_value}")
            return
        
        # Sort by date
        filtered_posts.sort(
            key=lambda x: self.state.pending[x].timestamp,
            reverse=True
        )
        
        from ..models.state import PreviewMode
        self.state.preview_mode = PreviewMode(
            list=filtered_posts,
            current=0,
            filter={tag_type: tag_value}
        )
        self.save_state()
        
        await update.callback_query.edit_message_text(
            f"✅ Найдено {len(filtered_posts)} постов с тегом {tag_value}"
        )
        
        # Show first post
        from .preview import PreviewHandler
        preview_handler = PreviewHandler(
            self.config,
            self.state_manager,
            self.ai_service,
            self.image_service,
            self.publisher_service,
            self.content_fetcher
        )
        
        first_post = self.state_manager.get_post(filtered_posts[0])
        if first_post:
            await preview_handler.send_preview(
                context.bot,
                first_post,
                update.callback_query.message.chat.id,
                0,
                len(filtered_posts)
            )
    
    async def _handle_preview_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle preview navigation callbacks"""
        from .preview import PreviewHandler
        preview_handler = PreviewHandler(
            self.config,
            self.state_manager,
            self.ai_service,
            self.image_service,
            self.publisher_service,
            self.content_fetcher
        )
        
        if data == "preview_close":
            await update.callback_query.message.delete()
            return
        
        elif data.startswith("preview_next:") or data.startswith("preview_prev:"):
            current_idx = int(data.split(":")[1])
            preview_list = self.state.preview_mode.list if self.state.preview_mode else []
            
            if data.startswith("preview_next:"):
                new_idx = min(current_idx + 1, len(preview_list) - 1)
            else:
                new_idx = max(current_idx - 1, 0)
            
            if 0 <= new_idx < len(preview_list):
                uid = preview_list[new_idx]
                post = self.state_manager.get_post(uid)
                if post:
                    await preview_handler.send_preview(
                        context.bot,
                        post,
                        update.callback_query.message.chat.id,
                        new_idx,
                        len(preview_list),
                        update.callback_query.message.message_id
                    )
        
        elif data.startswith("preview_full:"):
            uid = data.split(":")[1]
            post = self.state_manager.get_post(uid)
            if post:
                # Delete preview and show full post
                await update.callback_query.message.delete()
                await preview_handler.send_full_post(context.bot, post, update.callback_query.message.chat.id)
        
        elif data.startswith("back_preview:"):
            # Return to preview from moderation
            uid = data.split(":")[1]
            await update.callback_query.message.delete()
            
            preview_list = self.state.preview_mode.list if self.state.preview_mode else []
            if uid in preview_list:
                idx = preview_list.index(uid)
                post = self.state_manager.get_post(uid)
                if post:
                    await preview_handler.send_preview(
                        context.bot,
                        post,
                        update.callback_query.message.chat.id,
                        idx,
                        len(preview_list)
                    )
    
    @admin_only(None)
    async def _handle_generation_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle image/text generation callbacks"""
        if data.startswith("gen_cover") or data.startswith("custom_prompt:"):
            uid = data.split(":")[-1]
            post = self.state_manager.get_post(uid)
            
            if not post:
                await update.callback_query.edit_message_text("❌ Пост не найден")
                return
            
            if data.startswith("custom_prompt:"):
                # Wait for custom prompt
                self.state.waiting.waiting_for_prompt = uid
                self.save_state()
                
                await update.callback_query.edit_message_text(
                    "✏️ <b>Создание кастомной обложки</b>\n\n"
                    "Отправьте описание для генерации изображения.\n"
                    "Пример: <i>Futuristic Nike Air Max sneakers floating in space with neon lights</i>\n\n"
                    "Или /cancel для отмены",
                    parse_mode=ParseMode.HTML
                )
            else:
                # Generate with default prompt
                await update.callback_query.message.edit_text("🎨 Генерирую обложку...")
                
                # Determine style
                category = post.category
                style_key = category if category in ["sneakers", "fashion"] else "sneakers"
                
                # Generate prompt
                prompt = self.ai_service.get_image_prompt(post.title, style_key)
                
                # Generate image
                image_url = await self.ai_service.generate_image(prompt)
                
                if image_url:
                    self.state_manager.add_generated_image(uid, image_url)
                    await update.callback_query.message.edit_text("✅ Обложка сгенерирована!")
                    
                    # If this is full view, update post
                    if "full" in data:
                        await self.publisher_service.send_for_moderation(
                            post,
                            update.callback_query.message.chat.id
                        )
                else:
                    await update.callback_query.message.edit_text("❌ Ошибка при генерации обложки")
        
        elif data.startswith("revert_img:"):
            # Revert to original images
            uid = data.split(":")[1]
            post = self.state_manager.get_post(uid)
            
            if post:
                self.state_manager.clear_generated_images(uid)
                await update.callback_query.message.edit_text("✅ Возвращены оригинальные изображения")
                await self.publisher_service.send_for_moderation(
                    post,
                    update.callback_query.message.chat.id
                )
        
        elif data == "gen_thought_cover":
            # Generate cover for thought
            thought_data = self.state.current_thought
            if thought_data:
                await update.callback_query.edit_message_text("🎨 Генерирую обложку для мысли...")
                
                prompt = self.ai_service.get_image_prompt(thought_data.topic, "thoughts")
                image_url = await self.ai_service.generate_image(prompt)
                
                if image_url:
                    thought_data.image_url = image_url
                    self.state.current_thought = thought_data
                    self.save_state()
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Опубликовать", callback_data="publish_thought")],
                        [InlineKeyboardButton("🔄 Перегенерировать текст", callback_data="regen_thought")],
                        [InlineKeyboardButton("🎨 Новая обложка", callback_data="gen_thought_cover")],
                        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_thought")]
                    ])
                    
                    await update.callback_query.edit_message_text(
                        f"💭 <b>Пост-размышление:</b>\n\n{thought_data.text}\n\n"
                        f"🎨 Обложка сгенерирована!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
                    )
                else:
                    await update.callback_query.edit_message_text("❌ Ошибка при генерации обложки")
    
    async def _handle_thought_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle thought post callbacks"""
        thought_data = self.state.current_thought
        
        if not thought_data:
            await update.callback_query.edit_message_text("❌ Данные поста не найдены")
            return
        
        if data == "publish_thought":
            # Publish thought
            success = await self.publisher_service.publish_thought(thought_data)
            
            if success:
                await update.callback_query.edit_message_text("✅ Мысли опубликованы!")
                self.state.current_thought = None
                self.save_state()
            else:
                await update.callback_query.edit_message_text("❌ Ошибка публикации")
        
        elif data == "regen_thought":
            # Regenerate thought text
            await update.callback_query.edit_message_text("🔄 Генерирую новые мысли...")
            
            new_thought = await self.ai_service.generate_caption(
                thought_data.topic,
                "",
                "sneakers",
                is_thought=True,
                image_description=thought_data.image_description or ""
            )
            
            hashtags = get_hashtags_for_post(thought_data.topic, "sneakers")
            final_text = f"{new_thought}\n\n{hashtags}"
            
            thought_data.text = final_text
            self.state.current_thought = thought_data
            self.save_state()
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Опубликовать", callback_data="publish_thought")],
                [InlineKeyboardButton("🔄 Перегенерировать", callback_data="regen_thought")],
                [InlineKeyboardButton("🎨 Генерировать обложку", callback_data="gen_thought_cover")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_thought")]
            ])
            
            await update.callback_query.edit_message_text(
                f"💭 <b>Пост-размышление:</b>\n\n{final_text}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        
        elif data == "cancel_thought":
            await update.callback_query.message.delete()
            self.state.current_thought = None
            self.save_state()
    
    @admin_only(None)
    async def _handle_moderation_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle post moderation callbacks"""
        if ":" not in data:
            await update.callback_query.edit_message_text("❌ Ошибка: некорректный формат данных")
            return
        
        action, uid = data.split(":", 1)
        
        if action not in ["approve", "reject", "regen"]:
            return
        
        post = self.state_manager.get_post(uid)
        if not post:
            await update.callback_query.edit_message_text("❌ Этот пост уже был обработан")
            return
        
        if action == "approve":
            # Publish post
            published = await self.publisher_service.publish_post(post)
            
            if published:
                await update.callback_query.edit_message_text(f"✅ Опубликовано: {post.title[:50]}...")
            else:
                await update.callback_query.edit_message_text(f"🚨 Ошибка публикации: {post.title[:50]}...")
        
        elif action == "reject":
            await update.callback_query.edit_message_text(f"❌ Пропущено: {post.title[:50]}...")
            self.state_manager.remove_post(uid)
        
        elif action == "regen":
            await update.callback_query.edit_message_text(f"🔄 Регенерирую описание для: {post.title[:50]}...")
            
            # Regenerate caption
            new_description = await self.ai_service.generate_caption(
                post.title,
                post.context,
                post.category
            )
            
            post.description = new_description
            self.save_state()
            
            # Send back for moderation
            await self.publisher_service.send_for_moderation(
                post,
                update.callback_query.message.chat.id
            )