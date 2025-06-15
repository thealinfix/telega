#!/usr/bin/env python3
"""
Утилиты для работы со временем и датами
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import re
import logging

try:
    import pytz
except ImportError:
    logging.warning("pytz не установлен. Установите: pip install pytz")
    pytz = None

# Константы
DEFAULT_TIMEZONE = "Europe/Moscow"
UTC_OFFSET_PATTERN = r'+00:00'
DEFAULT_DATE_STRING = "Недавно"


def get_user_timezone(state: dict):
    """Получить временную зону пользователя"""
    timezone_str = state.get("timezone", DEFAULT_TIMEZONE)
    try:
        return pytz.timezone(timezone_str) if pytz else timezone.utc
    except Exception as e:
        logging.error(f"Ошибка получения временной зоны {timezone_str}: {e}")
        return pytz.timezone(DEFAULT_TIMEZONE) if pytz else timezone.utc


def localize_datetime(dt: datetime, state: dict) -> datetime:
    """Конвертировать UTC время в локальное"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    user_tz = get_user_timezone(state)
    return dt.astimezone(user_tz)


def format_local_time(dt: datetime, state: dict) -> str:
    """Форматировать время в локальной временной зоне"""
    local_dt = localize_datetime(dt, state)
    return local_dt.strftime("%d.%m.%Y %H:%M")


def parse_date_from_string(date_str: str) -> Optional[datetime]:
    """Парсинг даты из строки ISO формата"""
    try:
        # Заменяем паттерн +00:00 для совместимости
        if 'Z' in date_str:
            date_str = date_str.replace('Z', UTC_OFFSET_PATTERN)
        return datetime.fromisoformat(date_str)
    except ValueError as e:
        logging.error(f"Ошибка парсинга даты {date_str}: {e}")
        return None


def parse_schedule_time(text: str, state: dict) -> Optional[datetime]:
    """Парсинг времени/даты из текста с учетом временной зоны"""
    try:
        text = text.strip()
        user_tz = get_user_timezone(state)
        
        if pytz:
            now = datetime.now(user_tz)
        else:
            now = datetime.now(timezone.utc)
        
        # Обработка разных форматов времени
        parsed_time = _parse_time_format(text, now, user_tz)
        if parsed_time:
            return parsed_time
        
        parsed_datetime = _parse_datetime_format(text, now, user_tz)
        if parsed_datetime:
            return parsed_datetime
        
        parsed_relative = _parse_relative_time(text)
        if parsed_relative:
            return parsed_relative
        
    except Exception as e:
        logging.error(f"Ошибка парсинга времени '{text}': {e}")
    
    return None


def _parse_time_format(text: str, now: datetime, user_tz) -> Optional[datetime]:
    """Парсинг формата ЧЧ:ММ"""
    time_match = re.match(r'^(\d{1,2}):(\d{2})', text)


def format_date_for_display(date_input: any, state: dict) -> str:
    """Форматирование даты для отображения"""
    try:
        if isinstance(date_input, str):
            date = parse_date_from_string(date_input)
            if not date:
                return DEFAULT_DATE_STRING
        elif isinstance(date_input, datetime):
            date = date_input
        else:
            return DEFAULT_DATE_STRING
        
        # Конвертируем в локальное время
        local_date = localize_datetime(date, state)
        now = localize_datetime(datetime.now(timezone.utc), state)
        diff = now - local_date
        
        if diff.days == 0:
            return "Сегодня"
        elif diff.days == 1:
            return "Вчера"
        elif diff.days < 7:
            return f"{diff.days} дней назад"
        else:
            return local_date.strftime("%d.%m.%Y")
    except Exception as e:
        logging.error(f"Ошибка форматирования даты: {e}")
        return DEFAULT_DATE_STRING


def parse_date_from_rss(item) -> datetime:
    """Парсинг даты из RSS элемента"""
    try:
        # Ищем элементы с датой
        date_elem = item.find("pubDate") or item.find("published") or item.find("dc:date")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
            # Пытаемся распарсить через email.utils
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
    except ImportError:
        logging.warning("email.utils недоступен")
    except Exception as e:
        logging.error(f"Ошибка парсинга RSS даты: {e}")
    
    if not time_match:
        return None
    
    hours = int(time_match.group(1))
    minutes = int(time_match.group(2))
    
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    
    scheduled = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    if scheduled <= now:
        scheduled += timedelta(days=1)
    
    return scheduled.astimezone(timezone.utc)


def _parse_datetime_format(text: str, now: datetime, user_tz) -> Optional[datetime]:
    """Парсинг формата ДД.ММ ЧЧ:ММ"""
    datetime_match = re.match(r'^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})', text)


def format_date_for_display(date_input: any, state: dict) -> str:
    """Форматирование даты для отображения"""
    try:
        if isinstance(date_input, str):
            date = parse_date_from_string(date_input)
            if not date:
                return "Недавно"
        elif isinstance(date_input, datetime):
            date = date_input
        else:
            return "Недавно"
        
        # Конвертируем в локальное время
        local_date = localize_datetime(date, state)
        now = localize_datetime(datetime.now(timezone.utc), state)
        diff = now - local_date
        
        if diff.days == 0:
            return "Сегодня"
        elif diff.days == 1:
            return "Вчера"
        elif diff.days < 7:
            return f"{diff.days} дней назад"
        else:
            return local_date.strftime("%d.%m.%Y")
    except Exception as e:
        logging.error(f"Ошибка форматирования даты: {e}")
        return "Недавно"


def parse_date_from_rss(item) -> datetime:
    """Парсинг даты из RSS элемента"""
    try:
        # Ищем элементы с датой
        date_elem = item.find("pubDate") or item.find("published") or item.find("dc:date")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
            # Пытаемся распарсить через email.utils
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
    except ImportError:
        logging.warning("email.utils недоступен")
    except Exception as e:
        logging.error(f"Ошибка парсинга RSS даты: {e}")
    
    if not datetime_match:
        return None
    
    day = int(datetime_match.group(1))
    month = int(datetime_match.group(2))
    hours = int(datetime_match.group(3))
    minutes = int(datetime_match.group(4))
    year = now.year
    
    if not (1 <= day <= 31 and 1 <= month <= 12 and 0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    
    if pytz and hasattr(user_tz, 'localize'):
        scheduled = user_tz.localize(datetime(year, month, day, hours, minutes))
    else:
        scheduled = datetime(year, month, day, hours, minutes, tzinfo=timezone.utc)
    
    if scheduled < now:
        scheduled = scheduled.replace(year=year + 1)
    
    return scheduled.astimezone(timezone.utc)


def _parse_relative_time(text: str) -> Optional[datetime]:
    """Парсинг относительного времени (+1h, +30m, +2d)"""
    relative_match = re.match(r'^\+(\d+)([hmd])', text.lower())


def format_date_for_display(date_input: any, state: dict) -> str:
    """Форматирование даты для отображения"""
    try:
        if isinstance(date_input, str):
            date = parse_date_from_string(date_input)
            if not date:
                return "Недавно"
        elif isinstance(date_input, datetime):
            date = date_input
        else:
            return "Недавно"
        
        # Конвертируем в локальное время
        local_date = localize_datetime(date, state)
        now = localize_datetime(datetime.now(timezone.utc), state)
        diff = now - local_date
        
        if diff.days == 0:
            return "Сегодня"
        elif diff.days == 1:
            return "Вчера"
        elif diff.days < 7:
            return f"{diff.days} дней назад"
        else:
            return local_date.strftime("%d.%m.%Y")
    except Exception as e:
        logging.error(f"Ошибка форматирования даты: {e}")
        return "Недавно"


def parse_date_from_rss(item) -> datetime:
    """Парсинг даты из RSS элемента"""
    try:
        # Ищем элементы с датой
        date_elem = item.find("pubDate") or item.find("published") or item.find("dc:date")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
            # Пытаемся распарсить через email.utils
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
    except ImportError:
        logging.warning("email.utils недоступен")
    except Exception as e:
        logging.error(f"Ошибка парсинга RSS даты: {e}")
    
    if not relative_match:
        return None
    
    amount = int(relative_match.group(1))
    unit = relative_match.group(2)
    
    utc_now = datetime.now(timezone.utc)
    
    if unit == 'h' and 1 <= amount <= 24:
        return utc_now + timedelta(hours=amount)
    elif unit == 'm' and 1 <= amount <= 1440:
        return utc_now + timedelta(minutes=amount)
    elif unit == 'd' and 1 <= amount <= 30:
        return utc_now + timedelta(days=amount)
    
    return None


def format_date_for_display(date_input: any, state: dict) -> str:
    """Форматирование даты для отображения"""
    try:
        if isinstance(date_input, str):
            date = parse_date_from_string(date_input)
            if not date:
                return "Недавно"
        elif isinstance(date_input, datetime):
            date = date_input
        else:
            return "Недавно"
        
        # Конвертируем в локальное время
        local_date = localize_datetime(date, state)
        now = localize_datetime(datetime.now(timezone.utc), state)
        diff = now - local_date
        
        if diff.days == 0:
            return "Сегодня"
        elif diff.days == 1:
            return "Вчера"
        elif diff.days < 7:
            return f"{diff.days} дней назад"
        else:
            return local_date.strftime("%d.%m.%Y")
    except Exception as e:
        logging.error(f"Ошибка форматирования даты: {e}")
        return "Недавно"


def parse_date_from_rss(item) -> datetime:
    """Парсинг даты из RSS элемента"""
    try:
        # Ищем элементы с датой
        date_elem = item.find("pubDate") or item.find("published") or item.find("dc:date")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
            # Пытаемся распарсить через email.utils
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
    except ImportError:
        logging.warning("email.utils недоступен")
    except Exception as e:
        logging.error(f"Ошибка парсинга RSS даты: {e}")
    
    return datetime.now(timezone.utc)