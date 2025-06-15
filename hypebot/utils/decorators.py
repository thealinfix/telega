"""
Decorator utilities for handlers
"""
import functools
import logging
import time
from typing import Callable, Optional, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction


def admin_only(admin_id: Optional[int]):
    """Decorator to restrict command to admin only"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            # For callback queries
            if hasattr(update, 'callback_query') and update.callback_query:
                user_id = update.callback_query.from_user.id
                if admin_id and user_id != admin_id:
                    await update.callback_query.answer("❌ Недостаточно прав", show_alert=True)
                    return
            # For messages
            elif hasattr(update, 'message') and update.message:
                user_id = update.message.from_user.id
                if admin_id and user_id != admin_id:
                    await update.message.reply_text("❌ Эта команда доступна только администратору")
                    return
            
            return await func(self, update, context)
        return wrapper
    return decorator


async def _notify_user_of_error(update: Update):
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("❌ Произошла ошибка", show_alert=True)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text("❌ Произошла ошибка при выполнении команды")
    except Exception:
        pass

def log_errors(func: Callable) -> Callable:
    """Decorator to log errors in handlers"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}", exc_info=True)
            update = next((arg for arg in args if isinstance(arg, Update)), None)
            if update:
                await _notify_user_of_error(update)
    return wrapper


def with_typing_action(func: Callable) -> Callable:
    """Decorator to show typing action while processing"""
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await context.bot.send_chat_action(
                chat_id=update.message.chat_id,
                action=ChatAction.TYPING
            )
        return await func(self, update, context)
    return wrapper


def answer_callback_query(func: Callable) -> Callable:
    """Decorator to automatically answer callback queries"""
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            await update.callback_query.answer()
        return await func(self, update, context)
    return wrapper


def require_args(min_args: int = 1, usage_text: str = None):
    """Decorator to require minimum number of arguments for command"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not context.args or len(context.args) < min_args:
                help_text = usage_text or f"Использование: /{func.__name__} <аргументы>"
                await update.message.reply_text(help_text)
                return
            return await func(self, update, context)
        return wrapper
    return decorator


def _get_user_id(update: Update) -> Optional[int]:
    """Helper to extract user_id from update"""
    if hasattr(update, 'message') and update.message:
        return update.message.from_user.id
    elif hasattr(update, 'callback_query') and update.callback_query:
        return update.callback_query.from_user.id
    return None

def rate_limit(seconds: int = 1):
    """Simple rate limiting decorator"""
    def decorator(func: Callable) -> Callable:
        last_called = {}

        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = _get_user_id(update)

            if user_id:
                now = time.time()
                last = last_called.get(user_id, 0)

                if now - last < seconds:
                    if hasattr(update, 'callback_query') and update.callback_query:
                        await update.callback_query.answer("⏱ Слишком быстро! Подождите немного.", show_alert=True)
                    return

                last_called[user_id] = now

            return await func(self, update, context)
        return wrapper
    return decorator