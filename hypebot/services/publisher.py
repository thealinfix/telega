"""
Publishing service
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from telegram import Bot, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.error import TelegramError

from ..models.post import Post, ThoughtPost
from ..models.schedule import ScheduledPost
from ..services.state_manager import StateManager
from ..services.image_service import ImageService


class PublisherService:
    """Service for publishing posts"""
    
    def __init__(
        self,
        bot: Bot,
        state_manager: StateManager,
        image_service: ImageService
    ):
        self.bot = bot
        self.state_manager = state_manager
        self.image_service = image_service
    
    async def publish_post(self, post: Post, channel: Optional[str] = None) -> bool:
        """Publish post to channel"""
        if not channel:
            channel = self.state_manager.state.channel
        
        logging.info(f"Publishing to channel: {post.title[:50]}...")
        
        try:
            # Get generated images if any
            generated_images = self.state_manager.state.generated_images.get(post.id, [])
            
            # Build media group
            media = self.image_service.build_media_group(
                post,
                generated_images,
                for_channel=True
            )
            
            if media:
                await self.bot.send_media_group(channel, media)
            else:
                # Text-only post
                text = post.format_for_channel()
                await self.bot.send_message(
                    channel,
                    text,
                    parse_mode=ParseMode.HTML
                )
            
            # Mark as sent
            self.state_manager.mark_post_as_sent(post)
            
            logging.info(f"Successfully published: {post.title[:50]}")
            return True
            
        except TelegramError as e:
            logging.error(f"Telegram error publishing: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error publishing: {e}")
            return False
    
    async def publish_thought(self, thought: ThoughtPost, channel: Optional[str] = None) -> bool:
        """Publish thought post"""
        if not channel:
            channel = self.state_manager.state.channel
        
        try:
            if thought.image_url:
                await self.bot.send_photo(
                    channel,
                    thought.image_url,
                    caption=thought.text,
                    parse_mode=ParseMode.HTML
                )
            else:
                await self.bot.send_message(
                    channel,
                    thought.text,
                    parse_mode=ParseMode.HTML
                )
            
            return True
            
        except Exception as e:
            logging.error(f"Error publishing thought: {e}")
            return False
    
    async def check_and_publish_scheduled(self) -> List[str]:
        """Check and publish scheduled posts"""
        published_ids = []
        
        for post_id, scheduled in list(self.state_manager.state.scheduled_posts.items()):
            if scheduled.is_ready():
                success = await self.publish_post(scheduled.record)
                
                if success:
                    published_ids.append(post_id)
                    self.state_manager.unschedule_post(post_id)
                    
                    logging.info(f"Published scheduled post: {scheduled.record.title[:50]}")
                    
                    # Notify admin
                    if self.state_manager.config.admin_chat_id:
                        await self.bot.send_message(
                            self.state_manager.config.admin_chat_id,
                            f"✅ Запланированный пост опубликован:\n{scheduled.record.title[:50]}...",
                            parse_mode=ParseMode.HTML
                        )
        
        return published_ids
    
    async def auto_publish_next_favorite(self) -> Optional[str]:
        """Auto-publish next post from favorites"""
        if not self.state_manager.state.auto_publish:
            return None
        
        # Check interval
        last_publish = self.state_manager.state.last_auto_publish
        if last_publish:
            last_time = datetime.fromisoformat(last_publish.replace('Z', '+00:00'))
            interval = self.state_manager.state.publish_interval
            if (datetime.now(timezone.utc) - last_time).seconds < interval:
                return None
        
        # Find post from favorites
        for fav_id in self.state_manager.state.favorites:
            post = self.state_manager.get_post(fav_id)
            if post:
                success = await self.publish_post(post)
                
                if success:
                    # Update state
                    self.state_manager.state.last_auto_publish = datetime.now(timezone.utc).isoformat()
                    self.state_manager.state.favorites.remove(fav_id)
                    self.state_manager.save_state()
                    
                    # Notify admin
                    if self.state_manager.config.admin_chat_id:
                        await self.bot.send_message(
                            self.state_manager.config.admin_chat_id,
                            f"🤖 Автоматически опубликован пост из избранного:\n{post.title[:50]}...",
                            parse_mode=ParseMode.HTML
                        )
                    
                    return fav_id
        
        return None
    
    async def send_for_moderation(
        self,
        post: Post,
        admin_chat_id: int
    ) -> bool:
        """Send post to admin for moderation"""
        if not isinstance(post, Post):
            logging.error("Invalid post object for moderation")
            return False
        
        try:
            from ..handlers.menu import create_moderation_keyboard
            from ..utils.formatters import format_moderation_text
            from ..utils.time_utils import format_date_for_display
            
            # Prepare text
            date_str = format_date_for_display(
                post.timestamp,
                self.state_manager.state.timezone
            )
            
            generated_count = len(self.state_manager.state.generated_images.get(post.id, []))
            original_count = len(post.images)
            
            text = format_moderation_text(
                post,
                date_str,
                generated_count,
                original_count,
                self.state_manager.state.timezone
            )
            
            # Send media if available
            generated_images = self.state_manager.state.generated_images.get(post.id, [])
            media = self.image_service.build_media_group(
                post,
                generated_images,
                for_channel=False
            )
            
            if media:
                await self.bot.send_media_group(admin_chat_id, media)
            
            # Send moderation message
            keyboard = create_moderation_keyboard(post.id)
            await self.bot.send_message(
                admin_chat_id,
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            return True
            
        except TelegramError as e:
            logging.error(f"Telegram error sending for moderation: {e}")
            return False
        except Exception as e:
            logging.error(f"Error sending for moderation: {e}")
            return False