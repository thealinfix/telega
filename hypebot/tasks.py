import logging
from datetime import datetime, timezone
import httpx
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from . import config, utils, fetcher
from .state import state, save_state
from .messaging import publish_release


async def check_releases_job(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    
    try:
        # Проверяем есть ли админ
        if not config.ADMIN_CHAT_ID:
            logging.warning("config.ADMIN_CHAT_ID не установлен, пропускаем проверку")
            return
            
        # Отправляем уведомление о начале проверки
        progress_msg = await bot.send_message(
            config.ADMIN_CHAT_ID,
            "🔄 Начинаю проверку источников...",
            parse_mode=ParseMode.HTML
        )
        
        # Ищем новые релизы с прогрессом
        logging.info("Ищу новые релизы...")
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            new_releases = await fetcher.fetch_releases(client, progress_msg, bot)
        
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
                date_str = utils.format_date_for_display(post.get("timestamp", ""))
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
                    if config.ADMIN_CHAT_ID:
                        await bot.send_message(
                            config.ADMIN_CHAT_ID,
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
                
                if config.ADMIN_CHAT_ID:
                    await bot.send_message(
                        config.ADMIN_CHAT_ID,
                        f"🤖 Автоматически опубликован пост из избранного:\n{record['title'][:50]}...",
                        parse_mode=ParseMode.HTML
                    )
                break

