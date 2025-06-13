import json
import logging
from datetime import datetime, timezone
from typing import Dict, List
import pytz
from . import config

state = {}


def get_user_timezone():
    return pytz.timezone(state.get("timezone", config.DEFAULT_TIMEZONE))


def localize_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    user_tz = get_user_timezone()
    return dt.astimezone(user_tz)


def format_local_time(dt: datetime) -> str:
    local_dt = localize_datetime(dt)
    return local_dt.strftime("%d.%m.%Y %H:%M")


def clean_old_posts(state_dict):
    now = datetime.now(timezone.utc)
    removed_count = 0
    for uid in list(state_dict["pending"].keys()):
        post = state_dict["pending"][uid]
        try:
            post_date = datetime.fromisoformat(post.get("timestamp", "").replace('Z', '+00:00'))
            age = now - post_date
            if age.days > config.MAX_POST_AGE_DAYS:
                del state_dict["pending"][uid]
                removed_count += 1
        except Exception:
            continue

    if len(state_dict["pending"]) > config.MAX_PENDING_POSTS:
        sorted_posts = sorted(
            state_dict["pending"].items(),
            key=lambda x: x[1].get("timestamp", ""),
            reverse=True,
        )
        state_dict["pending"] = dict(sorted_posts[: config.MAX_PENDING_POSTS])
        removed_count += len(sorted_posts) - config.MAX_PENDING_POSTS

    if removed_count > 0:
        logging.info(f"Удалено {removed_count} старых постов")

    return removed_count


def load_state():
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
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
                "timezone": config.DEFAULT_TIMEZONE,
                "channel": config.TELEGRAM_CHANNEL,
                "waiting_for_channel": False,
            }
            for key, default in defaults.items():
                if key not in loaded:
                    loaded[key] = default

            valid_pending = {}
            for uid, record in loaded["pending"].items():
                if isinstance(record, dict) and all(k in record for k in ["id", "title", "link"]):
                    valid_pending[uid] = record
                else:
                    logging.warning(f"Удаляю некорректную запись из pending: {uid}")
            loaded["pending"] = valid_pending
            clean_old_posts(loaded)
            return loaded
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
            "timezone": config.DEFAULT_TIMEZONE,
            "channel": config.TELEGRAM_CHANNEL,
            "waiting_for_channel": False,
        }


state = load_state()


def save_state():
    try:
        with open(config.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка при сохранении состояния: {e}")
