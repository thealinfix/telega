#!/usr/bin/env python3
"""
Сервис управления состоянием приложения
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

from models.post import Post
from models.schedule import ScheduledPost
from config.settings import settings


class StateManager:
    """Управление состоянием приложения"""
    
    def __init__(self, state_file: str = "state.json"):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Загрузка состояния из файла"""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                
                # Инициализация полей по умолчанию
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
                    "timezone": settings.default_timezone,
                    "channel": settings.telegram_channel,
                    "waiting_for_channel": False,
                    "waiting_for_prompt": None,
                    "auto_interval_custom": False
                }
                
                # Обновляем только отсутствующие ключи
                for key, default_value in defaults.items():
                    if key not in state:
                        state[key] = default_value
                
                # Валидация и миграция данных
                self._validate_state(state)
                
                # Очистка старых постов
                self.clean_old_posts(state)
                
                return state
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.info(f"Создаю новый файл состояния: {e}")
            return self._create_default_state()
    
    def _create_default_state(self) -> Dict[str, Any]:
        """Создание состояния по умолчанию"""
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
            "timezone": settings.default_timezone,
            "channel": settings.telegram_channel,
            "waiting_for_channel": False,
            "waiting_for_prompt": None,
            "auto_interval_custom": False
        }
    
    def _validate_state(self, state: Dict[str, Any]) -> None:
        """Валидация состояния"""
        # Валидация pending записей
        valid_pending = {}
        for uid, record in state.get("pending", {}).items():
            if isinstance(record, dict) and all(key in record for key in ['id', 'title', 'link']):
                valid_pending[uid] = record
            else:
                logging.warning(f"Удаляю некорректную запись из pending: {uid}")
        state["pending"] = valid_pending
    
    def save_state(self) -> None:
        """Сохранение состояния в файл"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logging.error(f"Ошибка при сохранении состояния: {e}")
    
    def clean_old_posts(self, state: Optional[Dict[str, Any]] = None) -> int:
        """Очистка старых постов из очереди"""
        if state is None:
            state = self.state
        
        now = datetime.now(timezone.utc)
        removed_count = 0
        
        # Очищаем старые посты
        for uid in list(state["pending"].keys()):
            post = state["pending"][uid]
            try:
                post_date = datetime.fromisoformat(
                    post.get("timestamp", "").replace('Z', '+00:00')
                )
                age = now - post_date
                
                if age.days > settings.max_post_age_days:
                    del state["pending"][uid]
                    removed_count += 1
            except Exception:
                continue
        
        # Ограничиваем количество постов
        if len(state["pending"]) > settings.max_pending_posts:
            sorted_posts = sorted(
                state["pending"].items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True
            )
            
            state["pending"] = dict(sorted_posts[:settings.max_pending_posts])
            removed_count += len(sorted_posts) - settings.max_pending_posts
        
        if removed_count > 0:
            logging.info(f"Удалено {removed_count} старых постов")
        
        return removed_count
    
    # Методы доступа к состоянию
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение из состояния"""
        return self.state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Установить значение в состоянии"""
        self.state[key] = value
        self.save_state()
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Обновить несколько значений"""
        self.state.update(updates)
        self.save_state()
    
    # Специализированные методы
    def add_pending_post(self, post: Post) -> None:
        """Добавить пост в очередь"""
        self.state["pending"][post.id] = post.to_dict()
        self.save_state()
    
    def get_pending_post(self, post_id: str) -> Optional[Post]:
        """Получить пост из очереди"""
        post_data = self.state["pending"].get(post_id)
        if post_data:
            return Post.from_dict(post_data)
        return None
    
    def remove_pending_post(self, post_id: str) -> None:
        """Удалить пост из очереди"""
        if post_id in self.state["pending"]:
            del self.state["pending"][post_id]
            self.save_state()
    
    def add_sent_link(self, link: str) -> None:
        """Добавить ссылку в отправленные"""
        if link not in self.state["sent_links"]:
            self.state["sent_links"].append(link)
            # Ограничиваем размер списка
            if len(self.state["sent_links"]) > 1000:
                self.state["sent_links"] = self.state["sent_links"][-500:]
            self.save_state()
    
    def is_link_sent(self, link: str) -> bool:
        """Проверить, была ли ссылка отправлена"""
        return link in self.state["sent_links"]
    
    def add_scheduled_post(self, post_id: str, scheduled_post: ScheduledPost) -> None:
        """Добавить запланированный пост"""
        self.state["scheduled_posts"][post_id] = scheduled_post.to_dict()
        self.save_state()
    
    def get_scheduled_posts(self) -> Dict[str, ScheduledPost]:
        """Получить все запланированные посты"""
        result = {}
        for post_id, data in self.state["scheduled_posts"].items():
            try:
                result[post_id] = ScheduledPost.from_dict(data)
            except Exception as e:
                logging.error(f"Ошибка при загрузке запланированного поста {post_id}: {e}")
        return result
    
    def remove_scheduled_post(self, post_id: str) -> None:
        """Удалить запланированный пост"""
        if post_id in self.state["scheduled_posts"]:
            del self.state["scheduled_posts"][post_id]
            self.save_state()
    
    def toggle_favorite(self, post_id: str) -> bool:
        """Переключить избранное"""
        if post_id in self.state["favorites"]:
            self.state["favorites"].remove(post_id)
            is_favorite = False
        else:
            self.state["favorites"].append(post_id)
            is_favorite = True
        
        self.save_state()
        return is_favorite
    
    def is_favorite(self, post_id: str) -> bool:
        """Проверить, в избранном ли пост"""
        return post_id in self.state.get("favorites", [])