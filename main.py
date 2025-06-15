import asyncio
import random
import openai
from telethon import TelegramClient
from telethon.tl.functions.messages import SendReactionRequest, ReadHistoryRequest, SetTypingRequest
from telethon.tl.functions.channels import ReadMessageContentsRequest
from telethon.tl.types import ReactionEmoji, SendMessageTypingAction, SendMessageCancelAction
from telethon.tl.functions.account import UpdateStatusRequest
from datetime import datetime, timedelta
import json
import os
import time
import re
import sys
from smart_bot_coordinator import SmartBotCoordinator, should_comment_smart
from typing import Dict, List, Tuple
bot_coordinator = SmartBotCoordinator()
def load_bots_config():
    """Загружает конфигурацию ботов"""
    try:
        with open('bots_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Файл bots_config.json не найден!")
        return None

def select_bot():
    """Позволяет выбрать бота для запуска"""
    config = load_bots_config()
    if not config:
        return None
    
    bots = config['bots']
    
    print("\n🤖 ВЫБОР БОТА ДЛЯ ЗАПУСКА")
    print("=" * 40)
    
    for i, bot in enumerate(bots, 1):
        status_emoji = "🟢" if bot['status'] == "active" else "⚫"
        proxy_info = f"{bot['proxy'][1]}:{bot['proxy'][2]}" if bot.get('proxy') else "Без прокси"
        print(f"{i}. {bot['name']} ({bot['phone']})")
        print(f"   Статус: {status_emoji} {bot['status']}")
        print(f"   Прокси: {proxy_info}")
        print(f"   Роль: {bot['role']}")
        print()
    
    try:
        choice = int(input("Выберите номер бота (0 для стандартного): "))
        
        if choice == 0:
            print("✅ Используются стандартные настройки")
            return None
        elif 1 <= choice <= len(bots):
            selected_bot = bots[choice - 1]
            print(f"\n✅ Выбран бот: {selected_bot['name']}")
            return selected_bot
        else:
            print("❌ Неверный выбор")
            return None
    except ValueError:
        print("❌ Введите число")
        return None

# Модифицируйте точку входа программы:
if __name__ == "__main__":
    # Предлагаем выбрать бота
    selected_bot = select_bot()
    
    if selected_bot:
        # Переопределяем глобальные переменные из выбранного бота
        api_id = selected_bot['api_id']
        api_hash = selected_bot['api_hash']
        session_file = selected_bot['session_file']
        
        # Прокси - преобразуем из списка в кортеж
        if selected_bot.get('proxy'):
            proxy = tuple(selected_bot['proxy'])
        else:
            proxy = None
        
        print(f"\n📱 Запуск с настройками:")
        print(f"   Сессия: {session_file}")
        print(f"   API ID: {api_id}")
        if proxy:
            print(f"   Прокси: {proxy[1]}:{proxy[2]}")
    else:
        print("\n📱 Запуск со стандартными настройками")
        # Используются настройки из начала файла
    
    # Запускаем основную функцию
    asyncio.run(enhanced_main())
if "--stats" in sys.argv:
    asyncio.run(show_coordination_stats())
else:
    asyncio.run(enhanced_main())
class ContentAnalyzer:
    """Продвинутый анализатор контента постов"""
    
    def __init__(self):
        # Расширенные категории брендов
        self.brands = {
            "nike": ["nike", "air max", "air force", "dunk", "blazer", "jordan", "aj1", "aj4"],
            "adidas": ["adidas", "yeezy", "boost", "ultraboost", "nmd", "gazelle"],
            "new_balance": ["new balance", "nb", "990", "991", "992", "2002r"],
            "puma": ["puma", "suede", "clyde"],
            "vans": ["vans", "old skool", "sk8-hi"],
            "converse": ["converse", "chuck taylor", "all star"]
        }
        
        # Модели и типы обуви
        self.shoe_models = {
            "retro": ["retro", "og", "vintage", "classic"],
            "running": ["running", "runner", "marathon", "sport"],
            "lifestyle": ["lifestyle", "casual", "street"],
            "collab": ["collab", "collaboration", "x ", " x "],
            "limited": ["limited", "exclusive", "rare", "drop"]
        }
        
        # Цвета на разных языках
        self.colors = {
            "black": ["black", "черный", "чёрный", "noir", "черн"],
            "white": ["white", "белый", "blanc", "бел"],
            "red": ["red", "красный", "rouge", "красн"],
            "blue": ["blue", "синий", "голубой", "bleu", "син", "сапфир"],
            "green": ["green", "зеленый", "зелёный", "vert", "зелен"],
            "grey": ["grey", "gray", "серый", "gris", "сер"],
            "yellow": ["yellow", "желтый", "жёлтый", "желт", "кибер-желт"],
            "purple": ["purple", "фиолетовый", "пурпурный", "фиолет"],
            "orange": ["orange", "оранжевый", "оранж"],
            "pink": ["pink", "розовый", "роз"],
            "brown": ["brown", "коричневый", "коричн"],
            "multicolor": ["multicolor", "разноцветный", "мульти", "радуга"]
        }
        
        # Материалы
        self.materials = {
            "leather": ["leather", "кожа", "замша", "suede", "нубук", "nubuck"],
            "mesh": ["mesh", "сетка", "текстиль", "fabric"],
            "canvas": ["canvas", "холст", "ткань"],
            "synthetic": ["synthetic", "синтетика", "искусственный"]
        }
        
        # Ценовые категории
        self.price_indicators = {
            "expensive": ["дорого", "expensive", "овerprice", "дороговато"],
            "cheap": ["дешево", "cheap", "бюджет", "недорого"],
            "sale": ["sale", "скидка", "распродажа", "discount", "%"]
        }

    def analyze_post(self, text: str, has_image: bool = False) -> Dict:
        """Полный анализ поста"""
        text_lower = text.lower() if text else ""
        
        analysis = {
            "brands": self._extract_brands(text_lower),
            "models": self._extract_models(text_lower),
            "colors": self._extract_colors(text_lower),
            "materials": self._extract_materials(text_lower),
            "price_context": self._extract_price_context(text_lower),
            "sentiment": self._analyze_sentiment(text_lower),
            "has_question": "?" in text if text else False,
            "has_price": self._has_price(text_lower),
            "release_type": self._get_release_type(text_lower),
            "is_news": self._is_news(text_lower),
            "has_image": has_image,
            "text_length": len(text) if text else 0,
            "main_topic": self._get_main_topic(text_lower),
            "is_album": False  # Устанавливается позже если grouped_id
        }
        
        return analysis

    def _extract_brands(self, text: str) -> List[str]:
        """Извлекает упомянутые бренды"""
        found_brands = []
        for brand, keywords in self.brands.items():
            if any(keyword in text for keyword in keywords):
                found_brands.append(brand)
        return found_brands

    def _extract_models(self, text: str) -> List[str]:
        """Извлекает модели обуви"""
        found_models = []
        for model_type, keywords in self.shoe_models.items():
            if any(keyword in text for keyword in keywords):
                found_models.append(model_type)
        return found_models

    def _extract_colors(self, text: str) -> List[str]:
        """Извлекает цвета (улучшенная версия)"""
        found_colors = []
        
        # Разбиваем текст на слова и проверяем каждое
        words = text.lower().split()
        
        for color, keywords in self.colors.items():
            for keyword in keywords:
                # Проверяем точное совпадение слова
                if keyword in words:
                    if color not in found_colors:
                        found_colors.append(color)
                    break
                # Проверяем вхождение в составные слова (например, "сапфирово-черные")
                for word in words:
                    if keyword in word and len(keyword) > 3:  # Не ищем слишком короткие
                        if color not in found_colors:
                            found_colors.append(color)
                        break
        
        return found_colors

    def _extract_materials(self, text: str) -> List[str]:
        """Извлекает материалы"""
        found_materials = []
        for material, keywords in self.materials.items():
            if any(keyword in text for keyword in keywords):
                found_materials.append(material)
        return found_materials

    def _extract_price_context(self, text: str) -> str:
        """Определяет ценовой контекст"""
        for category, keywords in self.price_indicators.items():
            if any(keyword in text for keyword in keywords):
                return category
        return "unknown"

    def _has_price(self, text: str) -> bool:
        """Проверяет наличие цены"""
        price_patterns = [
            r'\d+\s*(?:руб|rub|₽|\$|usd|eur|€)',
            r'(?:руб|rub|₽|\$|usd|eur|€)\s*\d+',
            r'\d{3,}\s*(?:р|r)',
            r'\d+k\s*(?:руб|rub)?'
        ]
        return any(re.search(pattern, text) for pattern in price_patterns)

    def _get_release_type(self, text: str) -> str:
        """Определяет тип релиза"""
        if any(word in text for word in ["collab", "collaboration", "x ", " x "]):
            return "collaboration"
        elif any(word in text for word in ["limited", "exclusive", "rare"]):
            return "limited"
        elif any(word in text for word in ["retro", "og", "vintage"]):
            return "retro"
        else:
            return "general"

    def _is_news(self, text: str) -> bool:
        """Определяет, является ли пост новостью"""
        news_indicators = ["drop", "release", "выход", "релиз", "появится", "скоро", "soon", "coming", "new"]
        return any(indicator in text for indicator in news_indicators)

    def _get_main_topic(self, text: str) -> str:
        """Определяет основную тему поста"""
        if self._extract_price_context(text) == "sale":
            return "sale"
        elif any(word in text for word in ["collab", "collaboration", "x ", " x "]):
            return "collaboration"
        elif self._is_news(text):
            return "news"
        elif self._has_price(text):
            return "price"
        else:
            return "general"

    def _analyze_sentiment(self, text: str) -> str:
        """Анализирует настроение текста"""
        positive_words = ["крутой", "классный", "отличный", "лучший", "топ", "fire", "amazing", "great", "best", "perfect", "🔥", "❤️", "😍"]
        negative_words = ["плохой", "ужасный", "дорого", "овerprice", "не стоит", "bad", "terrible", "expensive", "waste"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
# Список популярных каналов для имитации просмотра
POPULAR_CHANNELS = [
    "durov",           # Павел Дуров (правильное имя)
    "tginfo",          # Telegram Info
    "telegram",        # Telegram News
    "breakingmash",    # Mash
    "meduzalive",      # Медуза
    "rian_ru",         # РИА Новости
    "rt_russian",      # RT на русском
    "tass_agency",     # ТАСС
    "rbc_news"         # РБК
]

# 2. Добавьте метод _analyze_sentiment в класс ContentAnalyzer:
# (Удалено дублирующее определение класса ContentAnalyzer)
def analyze_post(self, text: str, has_image: bool = False) -> Dict:
    """Полный анализ поста"""
    text_lower = text.lower() if text else ""
    
    analysis = {
        "brands": self._extract_brands(text_lower),
        "models": self._extract_models(text_lower),
        "colors": self._extract_colors(text_lower),
        "materials": self._extract_materials(text_lower),
        "price_context": self._extract_price_context(text_lower),
        "sentiment": self._analyze_sentiment(text_lower),
        "has_question": "?" in text,
        "has_price": self._has_price(text_lower),
        "release_type": self._get_release_type(text_lower),
        "is_news": self._is_news(text_lower),
        "has_image": has_image,
        "text_length": len(text),
        "main_topic": self._get_main_topic(text_lower)
    }
    
    return analysis

    def _extract_brands(self, text: str) -> List[str]:
        """Извлекает упомянутые бренды"""
        found_brands = []
        for brand, keywords in self.brands.items():
            if any(keyword in text for keyword in keywords):
                found_brands.append(brand)
        return found_brands

    def _extract_models(self, text: str) -> List[str]:
        """Извлекает модели обуви"""
        found_models = []
        for model_type, keywords in self.shoe_models.items():
            if any(keyword in text for keyword in keywords):
                found_models.append(model_type)
        return found_models

    def _extract_colors(self, text: str) -> List[str]:
        """Извлекает цвета (улучшенная версия)"""
        found_colors = []

        # Разбиваем текст на слова и проверяем каждое
        words = text.lower().split()

        for color, keywords in self.colors.items():
            for keyword in keywords:
                # Проверяем точное совпадение слова
                if keyword in words:
                    if color not in found_colors:
                        found_colors.append(color)
                    break
                # Проверяем вхождение в составные слова (например, "сапфирово-черные")
                for word in words:
                    if keyword in word and len(keyword) > 3:  # Не ищем слишком короткие
                        if color not in found_colors:
                            found_colors.append(color)
                        break

        return found_colors

    def _extract_materials(self, text: str) -> List[str]:
        """Извлекает материалы"""
        found_materials = []
        for material, keywords in self.materials.items():
            if any(keyword in text for keyword in keywords):
                found_materials.append(material)
        return found_materials

    def _extract_price_context(self, text: str) -> str:
        """Определяет ценовой контекст"""
        for category, keywords in self.price_indicators.items():
            if any(keyword in text for keyword in keywords):
                return category
        return "unknown"

    def _has_price(self, text: str) -> bool:
        """Проверяет наличие цены"""
        price_patterns = [
            r'\d+\s*(?:руб|rub|₽|\$|usd|eur|€)',
            r'(?:руб|rub|₽|\$|usd|eur|€)\s*\d+',
            r'\d{3,}\s*(?:р|r)',
            r'\d+k\s*(?:руб|rub)?'
        ]
        return any(re.search(pattern, text) for pattern in price_patterns)

    def _get_release_type(self, text: str) -> str:
        """Определяет тип релиза"""
        if any(word in text for word in ["new", "новый", "новая", "новые", "анонс"]):
            return "new_release"
        elif any(word in text for word in ["restock", "рестоке", "вернулись"]):
            return "restock"
        elif any(word in text for word in ["soon", "скоро", "coming", "грядет"]):
            return "upcoming"
        elif any(word in text for word in ["drop", "дроп", "релиз"]):
            return "drop"
        return "general"

    def _is_news(self, text: str) -> bool:
        """Определяет, является ли пост новостью"""
        news_indicators = [
            "announced", "анонсировали", "представили", "показали",
            "leaked", "слили", "утечка", "первый взгляд",
            "official", "официально", "подтвердили"
        ]
        return any(indicator in text for indicator in news_indicators)

    def _get_main_topic(self, text: str) -> str:
        """Определяет основную тему поста"""
        if any(word in text for word in ["collab", "collaboration", "коллаборация", " x "]):
            return "collaboration"
        elif any(word in text for word in ["retro", "og", "возвращение", "классика"]):
            return "retro"
        elif any(word in text for word in ["sale", "скидка", "распродажа"]):
            return "sale"
        elif any(word in text for word in ["review", "обзор", "отзыв"]):
            return "review"
        elif self._is_news(text):
            return "news"
        else:
            return "general"

    def _analyze_sentiment(self, text: str) -> str:
        """Анализирует тональность текста (метод-заглушка, используйте analyze_sentiment вне класса)"""
        return analyze_sentiment(text)

# 1. НОВАЯ функция для мониторинга ответов на комментарии (замена monitor_my_comments_replies)
async def check_replies_to_my_comments(client, discussion_chat, reactions_history, private_chat_history):
    """Проверяет ответы на мои комментарии и правильно обрабатывает ответы от каналов"""
    print("\n🔍 Проверяю ответы на мои комментарии...")
    
    try:
        # Получаем наши сообщения
        my_messages = reactions_history.get("my_messages", [])
        if not my_messages:
            print("📭 Нет моих комментариев для проверки")
            return
            
        messages = await client.get_messages(discussion_chat, limit=100)
        found_replies = False
        
        for msg in messages:
            # Проверяем, это ответ на наше сообщение?
            if msg.reply_to_msg_id and str(msg.reply_to_msg_id) in my_messages:
                # Проверяем, не обработали ли уже
                if str(msg.id) in reactions_history.get("processed_replies", []):
                    continue
                
                # Определяем отправителя
                sender_name = "Неизвестный"
                is_channel = False
                sender_id = None
                
                # Проверяем разные варианты отправителя
                if msg.from_id:
                    if hasattr(msg.from_id, 'channel_id'):
                        # Это канал
                        is_channel = True
                        sender_name = "Канал"
                        try:
                            channel_entity = await client.get_entity(msg.from_id)
                            if hasattr(channel_entity, 'title'):
                                sender_name = channel_entity.title
                        except:
                            pass
                    elif hasattr(msg.from_id, 'user_id'):
                        # Это пользователь
                        sender_id = msg.from_id.user_id
                        try:
                            user_entity = await client.get_entity(msg.from_id)
                            sender_name = get_display_name(user_entity)
                        except:
                            pass
                elif msg.sender:
                    # Старый способ
                    sender_name = get_display_name(msg.sender)
                    if hasattr(msg.sender, 'broadcast') and msg.sender.broadcast:
                        is_channel = True
                    elif hasattr(msg.sender, 'id'):
                        sender_id = msg.sender.id
                
                print(f"💬 Найден ответ на мой комментарий от {sender_name}")
                
                if msg.text:
                    print(f"   Текст: {msg.text[:100]}...")
                
                found_replies = True
                
                # Решаем, что делать с ответом
                if is_channel:
                    # Это ответ от канала - отвечаем в чате
                    if random.random() < 0.6:  # 60% шанс ответить каналу
                        await handle_channel_reply_in_chat(client, discussion_chat, msg, reactions_history)
                else:
                    # Это ответ от пользователя
                    if random.random() < 0.4:  # 40% шанс ответить пользователю
                        await handle_user_reply_in_chat(client, discussion_chat, msg, reactions_history)
                    
                    # Можем также поставить реакцию
                    if random.random() < 0.7:  # 70% шанс реакции
                        emoji = random.choice(["👍", "❤️", "🔥", "😊", "👀"])
                        await asyncio.sleep(random.randint(5, 15))
                        try:
                            await client(SendReactionRequest(
                                peer=discussion_chat,
                                msg_id=msg.id,
                                reaction=[ReactionEmoji(emoticon=emoji)]
                            ))
                            print(f"   ✅ Поставил реакцию {emoji}")
                        except:
                            pass
                
                # Помечаем как обработанный
                if "processed_replies" not in reactions_history:
                    reactions_history["processed_replies"] = []
                reactions_history["processed_replies"].append(str(msg.id))
                save_reactions_history(reactions_history)
        
        if not found_replies:
            print("📭 Новых ответов на мои комментарии не найдено")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке ответов: {e}")

# 2. Функция для ответа каналу в чате
async def handle_channel_reply_in_chat(client, discussion_chat, msg, reactions_history):
    """Обрабатывает ответ от канала - отвечает в чате"""
    print(f"📢 Готовлю ответ каналу...")
    
    # Анализируем текст для выбора стиля
    style = "neutral"
    if msg.text and "?" in msg.text:
        style = "answer"
    elif msg.text and any(word in msg.text.lower() for word in ["спасибо", "thanks", "круто", "супер"]):
        style = "positive"
    
    # Генерируем ответ
    reply = await generate_channel_appropriate_reply(msg.text, style)
    
    # Задержка
    delay = random.randint(30, 120)
    print(f"⏳ Отвечу через {delay} секунд...")
    await asyncio.sleep(delay)
    
    try:
        # Имитируем набор текста
        await simulate_typing(client, discussion_chat)
        
        # Отправляем ответ
        sent = await client.send_message(
            discussion_chat,
            reply,
            reply_to=msg.id
        )
        
        print(f"✅ Ответил каналу: {reply}")
        
        # Добавляем в историю
        reactions_history["my_messages"].append(str(sent.id))
        save_reactions_history(reactions_history)
        
    except Exception as e:
        print(f"❌ Ошибка при ответе каналу: {e}")

# 3. Функция для ответа пользователю в чате
async def handle_user_reply_in_chat(client, discussion_chat, msg, reactions_history):
    """Обрабатывает ответ от пользователя - отвечает в чате"""
    print(f"👤 Готовлю ответ пользователю...")
    
    # Выбираем стиль на основе текста
    style = analyze_reply_style(msg.text)
    
    # Генерируем ответ
    reply = await gpt_comment_with_context("", style, {"all_comments": []}, replied_comment=msg.text)
    
    # Задержка
    delay = random.randint(45, 150)
    print(f"⏳ Отвечу через {delay} секунд...")
    await asyncio.sleep(delay)
    
    try:
        await simulate_typing(client, discussion_chat)
        
        sent = await client.send_message(
            discussion_chat,
            reply,
            reply_to=msg.id
        )
        
        print(f"✅ Ответил пользователю: {reply}")
        
        reactions_history["my_messages"].append(str(sent.id))
        save_reactions_history(reactions_history)
        
    except Exception as e:
        print(f"❌ Ошибка при ответе пользователю: {e}")

# 4. Генератор ответов для каналов
async def generate_channel_appropriate_reply(channel_text, style):
    """Генерирует подходящий ответ для канала"""
    
    # Специальные ответы для каналов
    channel_replies = {
        "answer": {
            "price": ["норм цена", "дороговато", "за такую цену возьму", "подожду скидок"],
            "where": ["на poizon", "в оффлайне", "везде будут", "в телеге видел"],
            "when": ["летом вроде", "скоро должны", "уже есть", "в июне писали"],
            "default": ["ок", "понял", "спасибо", "ясно"]
        },
        "positive": ["топ инфа", "спасибо за пост", "класс", "огонь новость", "ждал этого"],
        "neutral": ["интересно", "посмотрим", "норм", "ок", "понятно"]
    }
    
    # Если вопрос о цене
    if channel_text and any(word in channel_text.lower() for word in ["цена", "сколько", "почем", "price"]):
        return random.choice(channel_replies["answer"]["price"])
    
    # Если вопрос где купить
    if channel_text and any(word in channel_text.lower() for word in ["где", "откуда", "where"]):
        return random.choice(channel_replies["answer"]["where"])
    
    # Если вопрос когда
    if channel_text and any(word in channel_text.lower() for word in ["когда", "when", "дата"]):
        return random.choice(channel_replies["answer"]["when"])
    
    # Выбираем по стилю
    if style == "answer":
        return random.choice(channel_replies["answer"]["default"])
    elif style == "positive":
        return random.choice(channel_replies["positive"])
    else:
        return random.choice(channel_replies["neutral"])

# 5. Анализатор стиля для ответов
def analyze_reply_style(text):
    """Анализирует текст ответа для выбора стиля"""
    if not text:
        return "neutral"
    
    text_lower = text.lower()
    
    # Вопрос
    if "?" in text:
        return "answer"
    
    # Позитив
    positive_words = ["спасибо", "thanks", "круто", "класс", "топ", "согласен"]
    if any(word in text_lower for word in positive_words):
        return "agree"
    
    # Негатив
    negative_words = ["не согласен", "фигня", "плохо", "дорого", "не нравится"]
    if any(word in text_lower for word in negative_words):
        return "neutral"  # Не спорим
    
    return "short_reaction"

async def handle_reply_to_my_comment(client, message, reactions_history):
    """Обрабатывает ответ на наш комментарий"""
    
    # Проверяем, не слишком ли много ответов
    today = datetime.now().strftime("%Y-%m-%d")
    replies_today = reactions_history.get("replies_today", {}).get(today, 0)
    
    if replies_today >= 10:  # Максимум 10 ответов в день
        print("⚠️ Достигнут лимит ответов на ответы за день")
        return
    
    # Анализируем текст
    text_lower = message.text.lower()
    
    # Проверяем, это вопрос к нам?
    is_question_to_me = False
    clarification_needed = False
    
    # Явные обращения
    if any(marker in text_lower for marker in ["@", "тебе", "тебя", "ты ", " ты", "вам", "вас"]):
        is_question_to_me = True
    
    # Неявные вопросы - нужно уточнение
    elif "?" in message.text and len(text_lower.split()) < 10:
        # Короткий вопрос без явного адресата
        clarification_needed = True
    
    # Решаем, отвечать ли
    reply_chance = 0.9 if is_question_to_me else 0.3
    
    if clarification_needed:
        reply_chance = 0.7  # Высокий шанс уточнить
    
    if random.random() < reply_chance:
        # Задержка перед ответом
        delay = random.randint(30, 120)
        print(f"⏳ Отвечу через {delay} секунд...")
        await asyncio.sleep(delay)
        
        # Имитируем набор текста
        await simulate_typing(client, discussion_chat)
        
        # Генерируем ответ
        if clarification_needed:
            reply = await generate_clarification_reply(message.text)
        else:
            reply = await generate_reply_to_reply(message.text, is_question_to_me)
        
        try:
            sent_reply = await client.send_message(
                entity=discussion_chat,
                message=reply,
                reply_to=message.id
            )
            
            # Добавляем в историю
            if "replied_to_replies" not in reactions_history:
                reactions_history["replied_to_replies"] = []
            reactions_history["replied_to_replies"].append(str(message.id))
            
            if "my_messages" not in reactions_history:
                reactions_history["my_messages"] = []
            reactions_history["my_messages"].append(str(sent_reply.id))
            
            # Обновляем счетчик
            if "replies_today" not in reactions_history:
                reactions_history["replies_today"] = {}
            reactions_history["replies_today"][today] = replies_today + 1
            
            save_reactions_history(reactions_history)
            print(f"✅ Ответил: {reply}")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке ответа: {e}")

async def generate_clarification_reply(original_text):
    """Генерирует уточняющий ответ"""
    clarifications = [
        "это мне?",
        "мне вопрос?",
        "ты мне?",
        "это ко мне?",
        "мне отвечаешь?",
        "сорри это мне или нет?",
        "не понял это мне",
        "чё мне?",
        "а это кому вопрос?"
    ]
    
    # 70% шанс использовать готовую фразу
    if random.random() < 0.7:
        return random.choice(clarifications)
    
    # Иначе GPT
    prompt = f"""Ты видишь вопрос в чате, но не понимаешь, тебе ли он адресован.
Напиши ОЧЕНЬ короткое уточнение (2-5 слов), спроси адресован ли вопрос тебе.
Пиши как в мессенджере, можешь без знаков препинания.

Вопрос который ты видишь: {original_text}

Твое короткое уточнение:"""

    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=15,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip().lower()
    except Exception:
        return random.choice(clarifications)

async def generate_reply_to_reply(text, is_direct_question):
    """Генерирует ответ на ответ"""
    
    if is_direct_question:
        # Прямой вопрос к нам - отвечаем по существу
        prompt = f"""Тебе задали прямой вопрос в чате. Ответь коротко и по делу.
Пиши как обычный человек в мессенджере, максимум 10 слов.

Вопрос: {text}

Твой ответ:"""
    else:
        # Просто реакция на наш комментарий
        prompt = f"""Кто-то ответил на твой комментарий. Отреагируй коротко.
Можешь согласиться, пошутить или просто подтвердить.
Максимум 5 слов, пиши как в чате.

Ответ на твой комментарий: {text}

Твоя реакция:"""

    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.8,
        )
        reply = response.choices[0].message.content.strip()
        
        # 60% шанс сделать все маленькими буквами
        if random.random() < 0.6:
            reply = reply.lower()
            
        return reply
    except Exception:
        # Запасные варианты
        if is_direct_question:
            return random.choice(["хз", "не знаю", "может быть", "да", "неа", "норм"])
        else:
            return random.choice(["ага", "++", "точно", "да", "пон", "))"])

async def continuous_monitoring_mode(client, channel_username, discussion_chat, history, reactions_history, private_chat_history):
    """Режим постоянного мониторинга с правильной обработкой ответов"""
    print("\n🔄 Запускаю режим постоянного мониторинга...")
    print("📱 Статус: онлайн 🟢")
    
    while True:
        try:
            # Проверяем ответы на наши комментарии (включая от каналов)
            await check_replies_to_my_comments(client, discussion_chat, reactions_history, private_chat_history)
            
            # Проверяем личные сообщения
            await handle_private_messages(client, private_chat_history)
            
            # Случайный интервал
            interval = random.randint(300, 600)  # 5-10 минут
            print(f"\n⏰ Следующая проверка через {interval//60} минут...")
            
            await asyncio.sleep(interval)
            
        except Exception as e:
            print(f"❌ Ошибка в режиме мониторинга: {e}")
            await asyncio.sleep(60)
    


async def generate_contextual_comment(analysis: Dict, style: str) -> str:
    """Генерирует комментарий на основе анализа контента"""
    
    # Специфичные комментарии для разных контекстов
    contextual_templates = {
        "collaboration": {
            "positive": ["огонь коллаб", "жду эту коллабу", "топ колаборация", "patta x nike всегда огонь", "патта не подводит"],
            "question": ["когда дроп?", "будет в россии?", "сколько будут стоить?", "где можно будет взять?"],
            "love": ["мечта", "нужны обе", "shut up and take my money", "беру не глядя"],
            "cool": ["стильная коллаба", "патта как всегда", "дизайн топ", "найс коллаб"]
        },
        "retro": {
            "positive": ["классика", "легенда вернулась", "наконец-то", "ждал этого"],
            "love": ["детство", "ностальгия", "помню первые", "легендарные"],
            "neutral": ["были у меня такие", "норм что вернули", "посмотрим что будет"]
        },
        "sale": {
            "positive": ["надо брать", "пора затариваться", "наконец-то скидки"],
            "question": ["сколько процентов?", "где скидки?", "это везде или где?"],
            "short_reaction": ["бегу", "лечу", "уже еду"]
        },
        "new_release": {
            "positive": ["свежак", "новинка огонь", "ждал", "топ релиз"],
            "question": ["когда релиз?", "где купить?", "будет онлайн?"],
            "love": ["хочу", "нужны", "беру не глядя"]
        },
        "drop": {
            "positive": ["жду дроп", "готов к дропу", "топ релиз", "будет жарко"],
            "question": ["во сколько дроп?", "где дропается?", "какая цена?"],
            "love": ["нужны обязательно", "мастхэв", "готовлю деньги"]
        },
        "album": {
            "positive": ["топ подборка", "все фото огонь", "красивые фотки", "шикарно", "залип"],
            "question": ["все цвета есть?", "сколько всего расцветок?", "это все варианты?"],
            "love": ["все хочу", "каждая пара огонь", "выбрать не могу", "все в коллекцию"],
            "cool": ["стильная подборка", "красиво сфоткано", "качество топ", "четкие фото"],
            "short_reaction": ["🔥🔥🔥", "все топ", "+++", "вау"]
        }
    }
    
    # Комментарии для конкретных брендов
    brand_specific = {
        "nike": {
            "positive": ["найк как всегда", "swoosh на месте", "найк не подводит", "air max топчик"],
            "love": ["обожаю найк", "nike boy", "team nike", "air max forever"],
            "question": ["в снкрс будут?", "на найк ру появятся?", "сколько ретейл?"]
        },
        "adidas": {
            "positive": ["три полоски топ", "адидас красавцы", "адик огонь"],
            "love": ["adidas всегда в сердце", "three stripes life"]
        },
        "new_balance": {
            "positive": ["нб в деле", "new balance топ", "качество нб"],
            "love": ["nb lifestyle", "обожаю нью бэланс"]
        }
    }
    
    # Приоритет выбора шаблона:
    # 1. Сначала проверяем основную тему (collaboration, drop и т.д.)
    # 2. Потом проверяем тип релиза
    # 3. Затем бренды
    # 4. В конце - дефолтные
    
    templates = None
    
    # Проверяем основную тему
    main_topic = analysis.get("main_topic", "general")
    if main_topic in contextual_templates and style in contextual_templates[main_topic]:
        templates = contextual_templates[main_topic][style]
    
    # Если не нашли, проверяем тип релиза
    if not templates:
        release_type = analysis.get("release_type", "general")
        if release_type in contextual_templates and style in contextual_templates[release_type]:
            templates = contextual_templates[release_type][style]
    
    # Если альбом, добавляем специфичные комментарии
    if analysis.get("is_album") and not templates:
        if style in contextual_templates["album"]:
            templates = contextual_templates["album"][style]
    
    # Проверяем бренды
    if not templates and analysis.get("brands"):
        brand = analysis["brands"][0]
        if brand in brand_specific and style in brand_specific[brand]:
            templates = brand_specific[brand][style]
    
    # Дефолтные шаблоны
    if not templates:
        templates = {
            "positive": ["топ", "огонь", "класс", "норм", "круто", "найс"],
            "negative": ["не мое", "спорно", "хз", "ну такое"],
            "question": ["сколько?", "где?", "когда?", "почем?"],
            "love": ["хочу", "нужны", "мечта", "кайф"],
            "cool": ["стильно", "свежо", "четко", "найс"],
            "short_reaction": ["++", "вау", "ого", "топ"]
        }.get(style, ["норм"])
    
    # Выбираем случайный шаблон
    comment = random.choice(templates)
    
    # Заменяем плейсхолдеры если есть
    if "{brand1}" in comment and len(analysis.get("brands", [])) >= 1:
        comment = comment.replace("{brand1}", analysis["brands"][0])
    if "{brand2}" in comment and len(analysis.get("brands", [])) >= 2:
        comment = comment.replace("{brand2}", analysis["brands"][1])
    
    return comment


async def generate_smart_comment(post_text: str, analysis: Dict, history) -> str:
    """Генерирует умный комментарий на основе анализа"""
    
    # Специальная обработка для альбомов
    if analysis.get("is_album"):
        # Если это коллаборация с альбомом
        if analysis.get("main_topic") == "collaboration":
            style = random.choice(["positive", "love", "question", "cool"])
        else:
            # Обычные альбомы
            album_styles = ["positive", "love", "question", "cool"]
            style = random.choice(album_styles)
    elif analysis.get("main_topic") == "collaboration":
        # Коллаборации - всегда интересно
        style = random.choice(["positive", "love", "question", "cool"])
    elif analysis.get("release_type") == "drop":
        # Дропы - ажиотаж
        style = random.choice(["positive", "question", "love"])
    elif analysis["has_question"]:
        style = "answer"
    elif analysis["main_topic"] == "sale":
        style = random.choice(["positive", "short_reaction", "question"])
    elif analysis["brands"] and "nike" in analysis["brands"]:
        style = random.choice(["positive", "love", "cool", "question"])
    elif analysis["release_type"] == "new_release":
        style = random.choice(["positive", "question", "love"])
    elif analysis["sentiment"] == "positive":
        style = random.choice(["positive", "cool"])
    elif analysis["sentiment"] == "negative":
        style = random.choice(["neutral", "question"])
    else:
        style = get_comment_style(history)
    
    # Для постов без текста (только фото)
    if not post_text or post_text == "Пост без текста (только фото/медиа)":
        return await generate_photo_comment(analysis, style)
    
    # Генерируем контекстный комментарий
    comment = await generate_contextual_comment(analysis, style)
    
    # Для отладки
    print(f"  💭 Выбран стиль: {style}")
    print(f"  💬 Сгенерирован комментарий: {comment}")
    
    return comment

async def process_new_posts(client, channel_username, discussion_chat, 
                          history_file="comment_history.json",
                          reactions_file="reactions_history.json"):
    """Модифицированная функция для работы с разными файлами истории"""
    
    # Загружаем историю для конкретного бота
    history = load_history(history_file)
    reactions_history = load_reactions_history(reactions_file)
    
    # Получаем информацию о текущем боте
    me = await client.get_me()
    bot_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    print(f"🤖 Работает бот: {bot_name}")
    
    # Проверяем последний пост в канале
    last_channel_post = await get_last_channel_post(client, channel_username, reactions_history)
    
    if not last_channel_post:
        found_new = False
        messages = await client.get_messages(channel_username, limit=20)
        
        for msg in messages:
            msg_key = f"{channel_username}_{msg.id}"
            if msg_key not in reactions_history.get("processed_messages", []):
                if msg.message and (not msg.grouped_id or msg.text or not msg.grouped_id):
                    last_channel_post = msg
                    found_new = True
                    print(f"✅ Найден необработанный пост: {msg.id}")
                    break
        
        if not found_new:
            print("❌ Все последние посты уже обработаны")
            return
    
    post_text = print_post_info(last_channel_post)
    
    # Обработка альбомов
    if last_channel_post.grouped_id:
        print(f"\n📸 Обнаружен альбом (grouped_id: {last_channel_post.grouped_id})")
        album_messages = await client.get_messages(
            channel_username, 
            limit=10,
            min_id=last_channel_post.id - 10,
            max_id=last_channel_post.id + 10
        )
        
        media_count = sum(1 for msg in album_messages if msg.grouped_id == last_channel_post.grouped_id)
        print(f"📸 Фотографий в альбоме: {media_count}")
    
    if not post_text:
        post_text = "Пост без текста (только фото/медиа)"
    
    # Пауза перед реакцией
    await asyncio.sleep(random.uniform(3, 10))
    
    # Ставим реакцию на пост
    await process_channel_post_reaction(client, last_channel_post, reactions_history)
    
    # Обработка комментариев с учетом бота
    await handle_discussion_and_comments_multi_bot(
        client, last_channel_post, post_text, history, reactions_history, bot_name
    )
    
    # Сохраняем историю
    save_history(history, history_file)
    save_reactions_history(reactions_history, reactions_file)

async def handle_discussion_and_comments_multi_bot(client, last_channel_post, post_text, 
                                                  history, reactions_history, bot_name):
    """Версия обработки комментариев с поддержкой множества ботов"""
    
    # Для дополнительных фото из альбома не комментируем
    if last_channel_post.grouped_id and not last_channel_post.text:
        print("⏭️ Пропускаю комментирование дополнительного фото из альбома")
        return
    
    # Анализируем контент
    analyzer = ContentAnalyzer()
    has_image = bool(last_channel_post.media or last_channel_post.grouped_id)
    post_analysis = analyzer.analyze_post(post_text, has_image)
    
    # Находим обсуждение
    discussion_msg_id = await find_discussion_msg_id(client, last_channel_post, discussion_chat)
    my_comment_id = None
    
    if not discussion_msg_id:
        print("❌ Не найдено обсуждение для поста.")
        return
    
    # Проверяем, можем ли комментировать
    if can_comment(last_channel_post.id, history):
        style = get_comment_style(history)
        wait_time = random.randint(10, 30)
        print(f"\n⏳ Жду {wait_time} секунд перед комментарием к посту...")
        await asyncio.sleep(wait_time)
        
        # Генерируем комментарий с учетом имени бота
        comment = await generate_bot_specific_comment(post_text, style, history, bot_name)
        sent_msg = await send_comment_and_get_id(
            client, discussion_chat, discussion_msg_id, comment, last_channel_post.id, history
        )
        
        if sent_msg:
            my_comment_id = sent_msg.id
    
    # Обрабатываем реакции и ответы
    await asyncio.sleep(random.randint(20, 60))
    await process_comment_reactions_and_replies_multi_bot(
        client, discussion_chat, post_text, reactions_history, history, my_comment_id, bot_name
    )

async def generate_bot_specific_comment(post_text, style, history, bot_name):
    """Генерирует комментарий с учетом личности конкретного бота"""
    
    # Разные "личности" для разных ботов
    bot_personalities = {
        "default": {
            "traits": "обычный парень, любит кроссовки",
            "vocabulary": ["топ", "норм", "класс", "хочу"],
            "emoji_chance": 0.1
        },
        "enthusiast": {
            "traits": "энтузиаст, всегда в восторге от новинок",
            "vocabulary": ["огонь", "имба", "мечта", "обязательно возьму"],
            "emoji_chance": 0.3
        },
        "skeptic": {
            "traits": "скептик, критично относится к ценам",
            "vocabulary": ["дорого", "переплата", "подожду скидок", "не стоит"],
            "emoji_chance": 0.05
        },
        "collector": {
            "traits": "коллекционер, знает историю моделей",
            "vocabulary": ["классика", "must have", "в коллекцию", "легенда"],
            "emoji_chance": 0.2
        }
    }
    
    # Выбираем личность на основе имени бота или случайно
    personality = bot_personalities.get(bot_name.lower(), random.choice(list(bot_personalities.values())))
    
    # Модифицированный промпт с учетом личности
    prompt = f"""Ты {personality['traits']}. 
Пиши ОЧЕНЬ КОРОТКО (1-5 слов).
Стиль: {style}
Используй слова: {', '.join(personality['vocabulary'])}
Контекст: {post_text[:100]}

Напиши короткий комментарий:"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=1.0,
        )
        comment = response.choices[0].message.content.strip().lower()
        
        # Добавляем эмодзи с учетом личности
        if random.random() < personality['emoji_chance']:
            emoji = random.choice(["🔥", "👟", "💰", "🤔", "😍"])
            comment += f" {emoji}"
        
        return comment
        
    except:
        return random.choice(personality['vocabulary'])

async def process_comment_reactions_and_replies_multi_bot(client, discussion_chat, post_text, 
                                                         reactions_history, history, 
                                                         my_comment_id, bot_name):
    """Обработка комментариев с учетом других ботов"""
    print("\n🔍 Проверяю комментарии для реакций и ответов...")
    
    if my_comment_id:
        reactions_history["my_messages"].append(str(my_comment_id))
        save_reactions_history(reactions_history)
    
    messages = await client.get_messages(discussion_chat, limit=30)
    
    # Получаем список известных ботов из конфига
    known_bots = load_known_bots()  # Функция для загрузки списка ботов
    
    reactions_given = 0
    replies_given = 0
    
    for msg in messages:
        if not msg.text or not msg.sender:
            continue
            
        # Пропускаем свои сообщения
        if str(msg.id) in reactions_history["my_messages"]:
            continue
        
        # Проверяем, это другой бот?
        sender_name = f"{msg.sender.first_name or ''} {msg.sender.last_name or ''}".strip()
        is_bot = sender_name in known_bots
        
        # Увеличиваем шанс взаимодействия с другими ботами
        if is_bot:
            interaction_chance = 0.5  # 50% шанс взаимодействия с ботом
        else:
            interaction_chance = 0.2  # 20% с обычными пользователями
        
        # Реакции
        if random.random() < interaction_chance and reactions_given < 3:
            emoji = choose_reaction(analyze_sentiment(msg.text))
            delay = random.randint(10, 30)
            print(f"⏳ Реакция {emoji} на {'бота' if is_bot else 'пользователя'} {sender_name}")
            
            await asyncio.sleep(delay)
            if await send_reaction(client, discussion_chat, msg.id, emoji, reactions_history):
                reactions_given += 1
                
                # Записываем взаимодействие с ботом
                if is_bot:
                    record_bot_interaction(bot_name, sender_name, "reaction", emoji)
        
        # Ответы (только один за сессию)
        if replies_given < 1 and should_reply_to_comment(msg.text, post_text, history, False):
            # Особая логика для ответов ботам
            if is_bot and random.random() < 0.7:  # 70% шанс ответить боту
                reply = await generate_bot_to_bot_reply(msg.text, sender_name)
            else:
                reply = await gpt_comment_with_context(post_text, "neutral", history, msg.text)
            
            delay = random.randint(30, 90)
            await asyncio.sleep(delay)
            
            try:
                await simulate_typing(client, discussion_chat)
                sent = await client.send_message(discussion_chat, reply, reply_to=msg.id)
                
                reactions_history["my_messages"].append(str(sent.id))
                save_reactions_history(reactions_history)
                
                print(f"✅ Ответил {'боту' if is_bot else 'пользователю'}: {reply}")
                replies_given += 1
                
                if is_bot:
                    record_bot_interaction(bot_name, sender_name, "reply", reply)
                    
            except Exception as e:
                print(f"❌ Ошибка ответа: {e}")

def load_known_bots():
    """Загружает список известных ботов"""
    try:
        with open("bots_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
            return [bot.get("name", "") for bot in config.get("bots", [])]
    except:
        return []

def record_bot_interaction(bot1, bot2, interaction_type, content):
    """Записывает взаимодействие между ботами"""
    interactions_file = "bot_interactions.json"
    
    try:
        with open(interactions_file, 'r', encoding='utf-8') as f:
            interactions = json.load(f)
    except:
        interactions = []
    
    interactions.append({
        "timestamp": datetime.now().isoformat(),
        "bot1": bot1,
        "bot2": bot2,
        "type": interaction_type,
        "content": content
    })
    
    # Сохраняем только последние 100 взаимодействий
    interactions = interactions[-100:]
    
    with open(interactions_file, 'w', encoding='utf-8') as f:
        json.dump(interactions, f, indent=2, ensure_ascii=False)

async def generate_bot_to_bot_reply(original_text, other_bot_name):
    """Генерирует ответ для другого бота"""
    replies = [
        "согласен", "точно", "+1", "тоже так думаю",
        "интересная мысль", "не знал", "спасибо",
        "хорошая идея", "поддерживаю", "факт",
        "может быть", "возможно", "надо подумать"
    ]
    
    # Если вопрос - отвечаем
    if "?" in original_text:
        return random.choice(["да", "нет", "возможно", "думаю да", "не уверен"])
    
    return random.choice(replies)

# Функции для сохранения с кастомными именами файлов
def save_history(history, filename="comment_history.json"):
    """Сохраняет историю в указанный файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def load_history(filename="comment_history.json"):
    """Загружает историю из указанного файла"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "posts_commented": {},
        "all_comments": [],
        "daily_count": {},
        "session_count": 0
    }

def save_reactions_history(reactions_history, filename="reactions_history.json"):
    """Сохраняет историю реакций в указанный файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(reactions_history, f, indent=2, ensure_ascii=False)

def load_reactions_history(filename="reactions_history.json"):
    """Загружает историю реакций из указанного файла"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "reacted_to": [],
        "all_reactions": [],
        "my_messages": [],
        "processed_messages": [],
        "hourly_count": {},
        "session_reactions_count": 0
    }

# Обновленная функция для использования с анализатором
async def process_post_with_analysis(post_text: str, has_image: bool = False) -> Tuple[str, Dict]:
    """Обрабатывает пост с полным анализом"""
    analyzer = ContentAnalyzer()
    analysis = analyzer.analyze_post(post_text, has_image)
    
    # Выбираем стиль на основе анализа
    if analysis["has_question"]:
        style = "answer"
    elif analysis["main_topic"] == "sale":
        style = random.choice(["positive", "short_reaction", "question"])
    elif analysis["main_topic"] == "collaboration":
        style = random.choice(["positive", "love", "question"])
    elif analysis["sentiment"] == "positive":
        style = random.choice(["positive", "love", "cool"])
    else:
        style = random.choice(["neutral", "question", "short_reaction"])
    
    # Генерируем контекстный комментарий
    comment = await generate_contextual_comment(analysis, style)
    
    return comment, analysis
# ==== КОНФИГ ====
api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'
session_file = 'sessions/573181612574.session'  
proxy = ('socks5', '217.29.62.212', 12049, True, 'ZcqNj3', 'KNqLM6')

openai_client = openai.OpenAI(
    api_key="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"
)

channel_username = 'chinapack'
discussion_chat = 'chipack_chat'

SKIP_POSTS_WITHOUT_TEXT = True

# Файлы для хранения истории
HISTORY_FILE = "comment_history.json"
REACTIONS_HISTORY_FILE = "reactions_history.json"
PRIVATE_CHAT_HISTORY_FILE = "private_chat_history.json"

# Настройки антидетекта
ANTIDETECT_CONFIG = {
    # Личные сообщения
    "private_message_reply_chance": 1,      # 30% шанс ответить на личное сообщение
    "max_private_replies_per_day": 5,         # Максимум ответов в личке за день
    "private_reply_delay": (5, 30),         # Задержка перед ответом в личке (1-5 минут)
    "ignore_spam_keywords": ["заработок", "инвестиции", "крипта", "биржа", "ставки"],
    
    # Имитация активности
    "random_channel_view_chance": 0.7,        # 70% шанс просмотреть случайные каналы
    "channels_to_view": 3,                    # Количество каналов для просмотра
    "read_messages_delay": (2, 10),           # Задержка при чтении сообщений
    
    # Статус онлайн
    "update_online_status": True,             # Обновлять статус онлайн
    "online_duration": (300, 900),            # Время онлайн (5-15 минут)
    "offline_duration": (1800, 7200),         # Время офлайн (30 мин - 2 часа)
    
    # Имитация набора текста
    "typing_duration": (3, 8),                # Время "набора" сообщения
    "typing_chance": 0.8,                     # 80% шанс показать набор текста
    
    # Паузы между действиями
    "action_cooldown": (5, 20),               # Пауза между любыми действиями
    "session_duration": (1800, 3600),         # Длительность сессии (30-60 минут)
    
    # Дневные лимиты
    "max_actions_per_day": 50,                # Максимум действий в день
    "max_messages_per_hour": 10,              # Максимум сообщений в час
    
    # Время активности (московское время)
    "active_hours": (9, 23),                  # Активен с 9 до 23
    "weekend_activity_reduction": 0.5,        # 50% снижение активности в выходные
}

# Список популярных каналов для имитации просмотра
POPULAR_CHANNELS = [
    "durov_russia",           # Павел Дуров (правильное имя)
    "tginfo",          # Telegram Info
    "telegram",        # Telegram News
    "breakingmash",    # Mash
    "meduzalive",      # Медуза
    "rian_ru",         # РИА Новости
    "rt_russian",      # RT на русском
    "tass_agency",     # ТАСС
    "rbc_news"         # РБК
]

# Настройки реакций
REACTIONS_CONFIG = {
    "channel_post_reaction_chance": 1.0,      # 100% шанс поставить реакцию на пост в канале
    "comment_reaction_chance": 0.3,           # 30% шанс поставить реакцию на чужой комментарий
    "max_reactions_per_hour": 20,             # Максимум реакций в час
    "min_time_between_reactions": 20,         # Минимум 20 секунд между реакциями
    "react_to_replies_chance": 0.9,           # 90% шанс отреагировать если тебе ответили
    "reaction_delay": (5, 45),                # Задержка перед реакцией (секунды)
    "max_reactions_per_session": 5,           # Максимум реакций за одну сессию
    "max_replies_to_replies_per_day": 10,  # Максимум ответов на ответы в день
    "reply_to_reply_delay": (30, 120),     # Задержка перед ответом на ответ
}

# Настройки ответов на комментарии
REPLY_CONFIG = {
    "reply_to_interesting_comment": 0.15,     # 15% базовый шанс ответить на интересный коммент
    "reply_if_mentioned_brand": 0.4,          # 40% если упомянут бренд из поста
    "reply_if_question": 0.6,                 # 60% если это вопрос
    "reply_if_strong_emotion": 0.3,           # 30% если сильные эмоции
    "max_replies_per_post": 2,                # Максимум ответов под одним постом
    "min_time_between_replies": 180,          # Минимум 3 минуты между ответами
    "reply_delay": (30, 120)                  # Задержка перед ответом
}

# Эмодзи реакции по категориям (расширенный список)
REACTIONS_BY_SENTIMENT = {
    "positive": ["👍", "❤️", "🔥", "👏", "💯", "😍", "✨", "💪"],  # Убрали 🤩, ⚡️
    "negative": ["👎", "😢", "🤮", "💩", "🤡", "😒", "😤"],  # Убрали 🙄, 😑
    "neutral": ["👀", "🤔", "😐", "🤷", "💭"],  # Убрали 🫤, 😶
    "funny": ["😂", "🤣", "😁", "😆", "💀", "😄"],  # Убрали 🤪
    "question": ["❓", "🤷"],  # Убрали 🤨, 🧐, ❔, 🤷‍♂️, 🤷‍♀️
    "wow": ["😱", "🤯", "😮", "🔥", "💥", "😲"],  # Убрали 🤩
    "love": ["❤️", "😍", "💕", "💖", "💘"],  # Убрали ❤️‍🔥
    "cool": ["😎", "🤙", "💎", "🔥"]  # Убрали 🆒
}

# Расширенные ключевые слова для определения тональности
SENTIMENT_KEYWORDS = {
    "positive": ["круто", "топ", "имба", "огонь", "класс", "супер", "лучш", "хочу", "надо брать", "шикарн", "красив", "стильн", "четк", "качеств"],
    "negative": ["кринж", "фу", "ужас", "говн", "отстой", "хрень", "не нрав", "плох", "дорог", "разочаров", "бред", "днище"],
    "funny": ["ахах", "хаха", "ору", "рофл", "лол", "смешн", "ржу", "угар", "хех", "ахахах", "лмао"],
    "question": ["?", "как", "где", "сколько", "когда", "почему", "зачем", "что это", "кто", "какой", "какие"],
    "wow": ["вау", "ого", "офигеть", "ничего себе", "охренеть", "жесть", "капец", "пздц", "блин"],
    "love": ["люблю", "обожаю", "кайф", "влюбился", "мечта", "хочу", "надо"],
    "cool": ["стиль", "свег", "фреш", "найс", "чил", "вайб"]
}

# Фразы, указывающие на интересный комментарий
INTERESTING_PATTERNS = {
    "personal_experience": ["у меня", "я купил", "я брал", "ношу", "были такие"],
    "recommendation": ["советую", "рекомендую", "берите", "не берите", "стоит", "не стоит"],
    "strong_opinion": ["имхо", "по мне", "считаю", "уверен", "точно"],
    "detailed_analysis": ["потому что", "так как", "дело в том", "причина"],
    "comparison": ["лучше чем", "хуже чем", "в отличие от", "по сравнению"]
}

# Настройки защиты от спама
SPAM_PROTECTION = {
    "min_time_between_comments": 300,
    "max_comments_per_hour": 5,
    "max_comments_per_post": 1,
    "max_comments_per_day": 20,
    "avoid_duplicate_style": True,
    "min_unique_words": 3
}

COMMENTS = [
    "ну такое",
    "хочу себе такие",
    "кринж какой то",
    "ору",
    "топчик",
    "имба просто",
    "ну норм чо",
    "жиза",
    "база",
    "да ладно прикольно же",
    "блин круто",
    "хз мне не оч",
    "вот это да",
    "ахахах топ",
    "бля хочу",
    "ну хз хз",
    "прикольно выглядит",
    "++++",
    "мне нрав",
    "дайте две",
    "это жестко",
    "сколько стоят",
    "где купить можно"
]

GPT_MODEL = "gpt-4o"

# Создаем папку sessions если её нет
os.makedirs('sessions', exist_ok=True)

def load_history():
    """Загружает историю комментариев"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return create_empty_history()
    return create_empty_history()

def load_reactions_history():
    """Загружает историю реакций"""
    if os.path.exists(REACTIONS_HISTORY_FILE):
        try:
            with open(REACTIONS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return create_empty_reactions_history()
    return create_empty_reactions_history()

def create_empty_history():
    """Создает пустую структуру истории"""
    return {
        "posts_commented": {},
        "all_comments": [],
        "last_styles": [],
        "daily_count": {},
        "replies_count": {},      # Счетчик ответов под постом
        "last_reply_time": None,  # Время последнего ответа
        "session_id": datetime.now().isoformat()
    }

def create_empty_reactions_history():
    """Создает пустую структуру истории реакций"""
    return {
        "reacted_to": {},
        "all_reactions": [],
        "hourly_count": {},
        "my_messages": [],
        "session_reactions_count": 0  # Счетчик реакций за сессию
    }

def save_history(history):
    """Сохраняет историю комментариев"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def save_reactions_history(history):
    """Сохраняет историю реакций"""
    with open(REACTIONS_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_private_chat_history():
    """Загружает историю личных сообщений"""
    if os.path.exists(PRIVATE_CHAT_HISTORY_FILE):
        try:
            with open(PRIVATE_CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return create_empty_private_history()
    return create_empty_private_history()

def create_empty_private_history():
    """Создает пустую историю личных сообщений"""
    return {
        "replied_to": {},        # {user_id: [timestamps]}
        "daily_replies": {},     # {date: count}
        "last_reply_time": None,
        "ignored_users": []      # Спамеры и боты
    }

def save_private_chat_history(history):
    """Сохраняет историю личных сообщений"""
    with open(PRIVATE_CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def analyze_sentiment(text):
    """Анализирует тональность текста (улучшенная версия)"""
    if not text:
        return "neutral"
    
    text_lower = text.lower()
    
    # Подсчитываем совпадения для каждой категории
    scores = {}
    for sentiment, keywords in SENTIMENT_KEYWORDS.items():
        score = sum(2 if keyword in text_lower else 0 for keyword in keywords)
        # Даем больше веса точным совпадениям
        for keyword in keywords:
            if f" {keyword} " in f" {text_lower} ":
                score += 1
        scores[sentiment] = score
    
    # Если есть явный вопрос, приоритет категории question
    if "?" in text:
        scores["question"] = scores.get("question", 0) + 5
    
    # Возвращаем категорию с максимальным счетом
    if max(scores.values()) == 0:
        return "neutral"
    
    return max(scores, key=scores.get)

def is_comment_interesting(text, post_text=""):
    """Определяет, интересен ли комментарий для ответа"""
    if not text:
        return False, 0.0
    
    text_lower = text.lower()
    interest_score = 0.0
    reasons = []
    
    # Проверяем паттерны интересных комментариев
    for pattern_type, patterns in INTERESTING_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                interest_score += 0.2
                reasons.append(pattern_type)
                break
    
    # Длинные комментарии часто более интересны
    if len(text) > 100:
        interest_score += 0.1
        reasons.append("detailed")
    
    # Комментарии с эмодзи часто эмоциональны
    emoji_count = sum(1 for char in text if ord(char) > 127462)
    if emoji_count > 0:
        interest_score += 0.05 * min(emoji_count, 3)
        reasons.append("emotional")
    
    # Если упоминается что-то из поста
    if post_text:
        post_words = set(post_text.lower().split())
        comment_words = set(text_lower.split())
        common_words = post_words.intersection(comment_words)
        if len(common_words) > 2:
            interest_score += 0.15
            reasons.append("relevant_to_post")
    
    # Ограничиваем максимальный счет
    interest_score = min(interest_score, 0.8)
    
    is_interesting = interest_score > 0.2
    return is_interesting, interest_score

def should_reply_to_comment(comment_text, post_text, history, is_reply_to_me=False):
    """Решает, стоит ли отвечать на комментарий с учетом безопасности"""
    
    # Проверяем на подозрительные вопросы
    suspicious_keywords = [
        "бот", "bot", "ии", "ai", "промпт", "prompt", 
        "нейросеть", "gpt", "chatgpt", "запрограммирован"
    ]
    
    comment_lower = comment_text.lower()
    
    # Если это подозрительный комментарий и это НЕ ответ нам
    if not is_reply_to_me and any(keyword in comment_lower for keyword in suspicious_keywords):
        print("⚠️ Пропускаю подозрительный комментарий")
        return False
    
    # Если это ответ нам с подозрительным вопросом - отвечаем с недоумением
    if is_reply_to_me and any(keyword in comment_lower for keyword in suspicious_keywords):
        print("⚠️ Подозрительный вопрос, буду отвечать с недоумением")
        return True
    
    # Дальше ваша обычная логика...
    # Если это ответ нам, высокий шанс ответить
    if is_reply_to_me:
        return random.random() < 0.8
    
    # Анализируем интересность комментария
    _, interest_score = is_comment_interesting(comment_text, post_text)
    
    # Базовый шанс
    reply_chance = REPLY_CONFIG["reply_to_interesting_comment"]
    
    # Модификаторы шанса
    sentiment = analyze_sentiment(comment_text)
    
    if sentiment == "question":
        reply_chance = REPLY_CONFIG["reply_if_question"]
    elif sentiment in ["love", "negative", "wow"]:
        reply_chance = REPLY_CONFIG["reply_if_strong_emotion"]
    
    # Увеличиваем шанс если комментарий интересный
    reply_chance += interest_score * 0.3
    
    # Проверяем, не слишком ли много ответов
    current_post_replies = history.get("replies_count", {}).get(str(post_text[:50]), 0)
    if current_post_replies >= REPLY_CONFIG["max_replies_per_post"]:
        return False
    
    # Проверяем время с последнего ответа
    if history.get("last_reply_time"):
        last_reply = datetime.fromisoformat(history["last_reply_time"])
        if (datetime.now() - last_reply).total_seconds() < REPLY_CONFIG["min_time_between_replies"]:
            return False
    
    # Финальное решение
    decision = random.random() < min(reply_chance, 0.8)
    
    if decision:
        print(f"💭 Решил ответить (шанс: {reply_chance:.2f}, интересность: {interest_score:.2f})")
    
    return decision

def choose_reaction(sentiment, is_reply_to_me=False, is_channel_post=False):
    """Выбирает подходящую реакцию (улучшенная версия)"""
    # Для постов в канале больше позитива
    if is_channel_post:
        if sentiment not in ["negative"]:
            # 70% шанс позитивной реакции для постов
            if random.random() < 0.7:
                sentiment = random.choice(["positive", "love", "cool", "wow"])
    
    # Если это ответ нам, чаще позитивные реакции
    if is_reply_to_me and sentiment not in ["negative", "question"] and random.random() < 0.8:
        sentiment = "positive"
    
    # Выбираем случайную реакцию из категории
    reactions = REACTIONS_BY_SENTIMENT.get(sentiment, REACTIONS_BY_SENTIMENT["neutral"])
    return random.choice(reactions)

async def can_react(message_id, reactions_history):
    """Проверяет, можно ли поставить реакцию"""
    now = datetime.now()
    current_hour = now.strftime("%Y-%m-%d-%H")
    
    # Проверка 1: Уже реагировали на это сообщение?
    if str(message_id) in reactions_history["reacted_to"]:
        return False
    
    # Проверка 2: Время с последней реакции
    if reactions_history["all_reactions"]:
        last_reaction_time = datetime.fromisoformat(reactions_history["all_reactions"][-1]["time"])
        time_diff = (now - last_reaction_time).total_seconds()
        if time_diff < REACTIONS_CONFIG["min_time_between_reactions"]:
            return False
    
    # Проверка 3: Реакций за час
    hourly_count = reactions_history["hourly_count"].get(current_hour, 0)
    if hourly_count >= REACTIONS_CONFIG["max_reactions_per_hour"]:
        return False
    
    # Проверка 4: Реакций за сессию
    if reactions_history["session_reactions_count"] >= REACTIONS_CONFIG["max_reactions_per_session"]:
        print(f"⚠️ Достигнут лимит реакций за сессию ({REACTIONS_CONFIG['max_reactions_per_session']})")
        return False
    
    return True

async def send_reaction(client, chat, message_id, emoji, reactions_history):
    """Отправляет реакцию на сообщение"""
    try:
        # Правильный способ для Telethon
        await client(SendReactionRequest(
            peer=chat,
            msg_id=message_id,
            reaction=[ReactionEmoji(emoticon=emoji)]  # В СПИСКЕ!
        ))
        
        # Обновляем историю
        now = datetime.now()
        current_hour = now.strftime("%Y-%m-%d-%H")
        
        reactions_history["reacted_to"][str(message_id)] = {
            "reaction": emoji,
            "time": now.isoformat()
        }
        
        reactions_history["all_reactions"].append({
            "message_id": str(message_id),
            "reaction": emoji,
            "time": now.isoformat()
        })
        
        reactions_history["hourly_count"][current_hour] = reactions_history["hourly_count"].get(current_hour, 0) + 1
        reactions_history["session_reactions_count"] += 1
        
        save_reactions_history(reactions_history)
        
        print(f"✅ Реакция {emoji} поставлена на сообщение {message_id}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при отправке реакции: {e}")
        return False

async def simulate_typing(client, peer, duration=None):
    """Имитирует набор текста"""
    if random.random() < ANTIDETECT_CONFIG["typing_chance"]:
        if not duration:
            duration = random.uniform(*ANTIDETECT_CONFIG["typing_duration"])
        
        try:
            # Начинаем "печатать"
            await client(SetTypingRequest(peer, SendMessageTypingAction()))
            print(f"⌨️ Печатаю {duration:.1f} секунд...")
            await asyncio.sleep(duration)
            
            # Останавливаем "печать"
            await client(SetTypingRequest(peer, SendMessageCancelAction()))
        except Exception as e:
            print(f"❌ Ошибка имитации набора: {e}")

async def update_online_status(client, online=True):
    """Обновляет статус онлайн/офлайн"""
    if ANTIDETECT_CONFIG["update_online_status"]:
        try:
            await client(UpdateStatusRequest(offline=not online))
            status = "онлайн 🟢" if online else "офлайн ⚫"
            print(f"📱 Статус: {status}")
        except Exception as e:
            print(f"❌ Ошибка обновления статуса: {e}")

async def read_channel_messages(client, channel, limit=10):
    """Читает сообщения в канале (отмечает как прочитанные)"""
    try:
        # Пробуем разные варианты получения entity
        try:
            # Сначала пробуем как username
            entity = await client.get_entity(f"@{channel}")
        except:
            try:
                # Потом без @
                entity = await client.get_entity(channel)
            except:
                print(f"⚠️ Не могу получить доступ к {channel}")
                return
        
        messages = await client.get_messages(entity, limit=limit)
        if messages:
            await client(ReadHistoryRequest(
                peer=entity,
                max_id=messages[0].id
            ))
            print(f"✅ Прочитано {len(messages)} сообщений в {channel}")
            
            delay = random.uniform(*ANTIDETECT_CONFIG["read_messages_delay"])
            await asyncio.sleep(delay)
    except Exception as e:
        error_type = type(e).__name__
        if "flood" in str(e).lower():
            print(f"⚠️ Флуд-контроль для канала {channel}")
        else:
            print(f"⚠️ Пропускаю канал {channel}: {error_type}")
            
async def handle_discussion_and_comments(client, last_channel_post, post_text, history, reactions_history):
    """Обрабатывает обсуждение с учетом альбомов и ошибок"""
    
    try:
        # Для дополнительных фото из альбома не комментируем
        if last_channel_post.grouped_id and not last_channel_post.text:
            print("⏭️ Пропускаю комментирование дополнительного фото из альбома")
            return
        
        # Анализируем контент поста
        analyzer = ContentAnalyzer()
        has_image = bool(last_channel_post.media or last_channel_post.grouped_id)
        post_analysis = analyzer.analyze_post(post_text, has_image)
        
        # Если это альбом, добавляем информацию
        if last_channel_post.grouped_id:
            post_analysis["is_album"] = True
            post_analysis["main_topic"] = "album" if post_analysis["main_topic"] == "general" else post_analysis["main_topic"]
        
        print("\n📊 Анализ поста:")
        print(f"  - Бренды: {', '.join(post_analysis['brands']) if post_analysis['brands'] else 'не найдено'}")
        print(f"  - Тема: {post_analysis['main_topic']}")
        print(f"  - Тип релиза: {post_analysis['release_type']}")
        print(f"  - Цвета: {', '.join(post_analysis['colors']) if post_analysis['colors'] else 'не указаны'}")
        print(f"  - Настроение: {post_analysis['sentiment']}")
        if post_analysis.get("is_album"):
            print("  - Тип: Альбом с фотографиями")
        
        # Продолжаем обычную логику комментирования
        discussion_msg_id = await find_discussion_msg_id(client, last_channel_post, discussion_chat)
        my_comment_id = None

        if not discussion_msg_id:
            print("❌ Не найдено обсуждение для поста.")
            await process_comment_reactions_and_replies(client, discussion_chat, post_text, reactions_history, history)
            return

        if can_comment(last_channel_post.id, history):
            wait_time = random.randint(10, 30)
            print(f"\n⏳ Жду {wait_time} секунд перед комментарием к посту...")
            await asyncio.sleep(wait_time)
            
            # Используем контекстную генерацию с учетом альбома
            comment = await generate_smart_comment(post_text, post_analysis, history)
            sent_msg = await send_comment_and_get_id(client, discussion_chat, discussion_msg_id, comment, last_channel_post.id, history)
            
            if sent_msg:
                my_comment_id = sent_msg.id
        else:
            print("\n⛔ Комментирование поста заблокировано системой защиты")
        
        await asyncio.sleep(random.randint(20, 60))
        await process_comment_reactions_and_replies(client, discussion_chat, post_text, reactions_history, history, my_comment_id)
        
    except Exception as e:
        print(f"❌ Ошибка в handle_discussion_and_comments: {e}")
        # Продолжаем работу даже при ошибке
        import traceback
        traceback.print_exc()

async def simulate_channel_browsing(client):
    """Имитирует просмотр случайных каналов"""
    if random.random() < ANTIDETECT_CONFIG["random_channel_view_chance"]:
        print("\n🌐 Имитирую просмотр каналов...")
        
        channels = random.sample(POPULAR_CHANNELS, 
                               min(ANTIDETECT_CONFIG["channels_to_view"], len(POPULAR_CHANNELS)))
        
        for channel in channels:
            await read_channel_messages(client, channel, limit=random.randint(5, 15))
            # Пауза между каналами
            await asyncio.sleep(random.uniform(5, 15))

async def should_work_now():
    """Проверяет, должен ли бот работать в текущее время"""
    now = datetime.now()
    hour = now.hour
    
    # Проверка активных часов
    start_hour, end_hour = ANTIDETECT_CONFIG["active_hours"]
    if not (start_hour <= hour < end_hour):
        print(f"😴 Не активное время ({hour}:00). Активен с {start_hour}:00 до {end_hour}:00")
        return False
    
    # Снижение активности в выходные
   # if now.weekday() >= 5:  # Суббота = 5, Воскресенье = 6
   #     if random.random() > ANTIDETECT_CONFIG["weekend_activity_reduction"]:
    #        print("🏖 Выходной день, пропускаю активность")
    #        return False
    
    return True

async def handle_private_message(client, message, private_history):
    """Обрабатывает личные сообщения с проверкой на удаленные"""
    
    # Проверяем, не удалено ли сообщение
    if not message.text or message.text == "**Reply was deleted.**":
        print("⚠️ Пропускаю удаленное сообщение")
        return
    
    peer = message.chat_id if hasattr(message, 'chat_id') else message.peer_id
    user_id = message.sender_id if hasattr(message, 'sender_id') else message.from_id
    if not user_id or not peer:
        print("⚠️ Не могу определить отправителя сообщения")
        return

    if await handle_spam_and_limits(message, user_id, private_history):
        return

    if await should_reply_to_private():
        await reply_to_private_message(client, peer, user_id, message.text, private_history)

def extract_peer_and_user_id(message):
    """Извлекает peer и user_id из сообщения"""
    if hasattr(message, 'peer_id'):
        peer = message.peer_id
        user_id = getattr(peer, 'user_id', None)
    else:
        peer = getattr(message, 'chat_id', None)
        user_id = getattr(message, 'from_id', None)
    return peer, user_id

async def handle_spam_and_limits(message, user_id, private_history):
    """Проверяет спам и лимиты, возвращает True если нужно прекратить обработку"""
    # Проверка на спам
    if any(keyword in message.text.lower() for keyword in ANTIDETECT_CONFIG["ignore_spam_keywords"]):
        print(f"🚫 Игнорирую спам от {user_id}")
        if user_id not in private_history["ignored_users"]:
            private_history["ignored_users"].append(user_id)
            save_private_chat_history(private_history)
        return True

    # Проверка дневного лимита
    today = datetime.now().strftime("%Y-%m-%d")
    daily_count = private_history["daily_replies"].get(today, 0)
    if daily_count >= ANTIDETECT_CONFIG["max_private_replies_per_day"]:
        print(f"⚠️ Достигнут дневной лимит ответов в личке ({daily_count})")
        return True

    # Проверка частоты ответов одному пользователю
    user_replies = private_history["replied_to"].get(str(user_id), [])
    if user_replies:
        last_reply = datetime.fromisoformat(user_replies[-1])
        if (datetime.now() - last_reply).total_seconds() < 3600:
            print(f"⏰ Недавно отвечал пользователю {user_id}")
            return True
    return False

async def should_reply_to_private():
    """Решает, стоит ли отвечать на личное сообщение"""
    return random.random() < ANTIDETECT_CONFIG["private_message_reply_chance"]

async def reply_to_private_message(client, peer, user_id, message_text, private_history):
    """Отвечает на личное сообщение с обработкой ошибок"""
    delay = random.randint(*ANTIDETECT_CONFIG["private_reply_delay"])
    print(f"💬 Отвечу на личное сообщение через {delay} сек...")
    print(f"📍 Peer: {peer}, User ID: {user_id}")
    await asyncio.sleep(delay)
    await simulate_typing(client, peer)
    reply = await generate_private_reply(message_text)
    today = datetime.now().strftime("%Y-%m-%d")
    daily_count = private_history["daily_replies"].get(today, 0)
    
    try:
        await client.send_message(peer, reply)
        
        # Обновляем историю только при успешной отправке
        if str(user_id) not in private_history["replied_to"]:
            private_history["replied_to"][str(user_id)] = []
        private_history["replied_to"][str(user_id)].append(datetime.now().isoformat())
        private_history["daily_replies"][today] = daily_count + 1
        private_history["last_reply_time"] = datetime.now().isoformat()
        save_private_chat_history(private_history)
        print(f"✅ Ответил в личку: {reply}")
        
    except Exception as e:
        error_msg = str(e)
        if "blocked" in error_msg.lower():
            print(f"🚫 Пользователь {user_id} заблокировал бота")
            # Добавляем в игнор-лист
            if user_id not in private_history["ignored_users"]:
                private_history["ignored_users"].append(user_id)
                save_private_chat_history(private_history)
        elif "flood" in error_msg.lower():
            print(f"⚠️ Флуд-контроль, не могу ответить пользователю {user_id}")
        else:
            print(f"❌ Ошибка отправки личного сообщения: {e}")

async def generate_private_reply(message_text):
    """Генерирует ответ на личное сообщение как обычный человек"""
    
    # Проверяем на подозрительные вопросы
    suspicious_keywords = [
        "промпт", "prompt", "система", "system", "ии", "ai", "бот", "bot",
        "искусственный интеллект", "chatgpt", "gpt", "openai", "клод", "claude"
    ]
    
    message_lower = message_text.lower()
    
    # Если вопрос подозрительный
    if any(keyword in message_lower for keyword in suspicious_keywords):
        confused_replies = [
            "чего?",
            "не понял",
            "что за промпт?",
            "о чем ты",
            "хз о чем речь",
            "что",
            "а?",
            "не понимаю",
            "это че",
            "что ты имеешь в виду"
        ]
        return random.choice(confused_replies)
    
    # Определяем тип сообщения
    # Приветствия
    if any(word in message_lower for word in ["привет", "здравствуй", "добрый", "хай", "ку", "прив"]):
        greetings = ["привет", "привет!", "хай", "здарова", "ку", "прив", "йо"]
        return random.choice(greetings)
    
    # Вопросы про кроссовки/одежду
    if any(word in message_lower for word in ["кроссовки", "кроссы", "найк", "адидас", "размер"]):
        sneaker_replies = [
            "не знаю", 
            "хз", 
            "смотри в канале",
            "там написано вроде",
            "в посте есть инфа"
        ]
        return random.choice(sneaker_replies)
    
    # Общие вопросы
    if "?" in message_text:
        question_replies = [
            "не знаю",
            "хз",
            "может быть", 
            "наверное",
            "без понятия",
            "не в курсе",
            "пас"
        ]
        return random.choice(question_replies)
    
    # Для всего остального - нейтральные ответы
    neutral_replies = [
        "ага",
        "понял", 
        "ок",
        "норм",
        "да",
        "ясно",
        "пон"
    ]
    
    # 80% шанс использовать готовый ответ
    if random.random() < 0.8:
        return random.choice(neutral_replies)
    
    # 20% - GPT, но с правильным промптом
    prompt = f"""Ты обычный парень, который подписан на канал про кроссовки. 
НЕ ассистент, НЕ бот, НЕ ИИ - просто обычный человек.
Тебе написали в личку, ответь ОЧЕНЬ коротко (1-5 слов), как обычный человек.
Если не понимаешь о чем речь - так и скажи.
НЕ предлагай помощь, НЕ будь вежливым ассистентом.

Сообщение: {message_text}

Твой короткий ответ как обычного человека:"""

    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=15,
            temperature=0.9,
        )
        reply = response.choices[0].message.content.strip().lower()
        
        # Убираем слова, которые выдают ассистента
        bad_words = ["помочь", "помогу", "ассистент", "рад", "готов", "секрет"]
        for bad_word in bad_words:
            if bad_word in reply:
                return random.choice(neutral_replies)
        
        return reply
    except:
        return random.choice(neutral_replies)

async def perform_random_actions(client):
    """Выполняет случайные действия для имитации активности"""
    actions = [
        ("browse_channels", 0.3),      # 30% шанс
        ("check_saved_messages", 0.2), # 20% шанс
        ("view_profile", 0.1),         # 10% шанс
    ]
    
    for action, chance in actions:
        if random.random() < chance:
            if action == "browse_channels":
                await simulate_channel_browsing(client)
            elif action == "check_saved_messages":
                # Проверяем избранное
                await client.get_messages("me", limit=5)
                print("📌 Проверил избранное")
            elif action == "view_profile":
                # Смотрим случайный профиль
                try:
                    random_channel = random.choice(POPULAR_CHANNELS)
                    await client.get_entity(random_channel)
                    print(f"👤 Посмотрел профиль @{random_channel}")
                except Exception:
                    pass
            
            # Пауза между действиями
            await asyncio.sleep(random.uniform(*ANTIDETECT_CONFIG["action_cooldown"]))

async def check_and_limit_actions(history):
    """Проверяет и ограничивает количество действий"""
    now = datetime.now()
    current_hour = now.strftime("%Y-%m-%d-%H")
    today = now.strftime("%Y-%m-%d")
    
    # Проверяем часовой лимит
    hourly_actions = history.get("hourly_actions", {})
    if hourly_actions.get(current_hour, 0) >= ANTIDETECT_CONFIG["max_messages_per_hour"]:
        print("⚠️ Достигнут часовой лимит сообщений")
        return False
    
    # Проверяем дневной лимит
    daily_actions = history.get("daily_actions", {})
    if daily_actions.get(today, 0) >= ANTIDETECT_CONFIG["max_actions_per_day"]:
        print("⚠️ Достигнут дневной лимит действий")
        return False
    
    return True

async def process_dialog_messages(client, dialog, private_history):
    """Обрабатывает сообщения в одном диалоге"""
    # Получаем последние сообщения
    messages = await client.get_messages(dialog.entity, limit=dialog.unread_count)
    for message in messages:
        if message.out:  # Пропускаем наши сообщения
            continue
        if message.text:  # Обрабатываем только текстовые
            await handle_private_message(client, message, private_history)
    # Отмечаем как прочитанные
    await client.send_read_acknowledge(dialog.entity)

async def monitor_private_messages(client):
    """Мониторит личные сообщения"""
    print("\n📨 Проверяю личные сообщения...")
    private_history = load_private_chat_history()
    
    try:
        dialogs = await client.get_dialogs(limit=10)
        unread_count = 0
        for dialog in dialogs:
            if dialog.is_user and dialog.unread_count > 0:
                unread_count += 1
                await process_unread_dialog(client, dialog, private_history)
        if unread_count == 0:
            print("📭 Нет непрочитанных личных сообщений")
    except Exception as e:
        print(f"❌ Ошибка мониторинга личных сообщений: {e}")

async def process_unread_dialog(client, dialog, private_history):
    """Обрабатывает непрочитанный диалог с проверкой сообщений"""
    print(f"💬 Найден непрочитанный диалог с {dialog.name}: {dialog.unread_count} сообщений")
    
    try:
        messages = await client.get_messages(dialog.entity, limit=dialog.unread_count)
        
        # Сортируем сообщения от старых к новым
        messages = sorted(messages, key=lambda m: m.date)
        
        # Флаг, ответили ли мы уже в этом диалоге
        already_replied = False
        valid_messages = 0  # Счетчик валидных сообщений
        
        for i, message in enumerate(messages):
            if message.out:  # Пропускаем наши сообщения
                continue
            
            # Проверяем валидность сообщения
            if not message.text:
                print("⏭️ Пропускаю сообщение без текста")
                continue
                
            if message.text == "**Reply was deleted.**":
                print("⏭️ Пропускаю удаленное сообщение")
                continue
            
            valid_messages += 1
            print(f"📩 Сообщение {valid_messages}/{len(messages)} от {dialog.name}: {message.text[:30]}...")
            
            # Если уже ответили в этом диалоге, пропускаем с вероятностью 70%
            if already_replied and random.random() < 0.7:
                print("⏭️ Пропускаю сообщение (уже ответил в диалоге)")
                continue
            
            # Решаем, отвечать ли на это сообщение
            should_reply = await decide_if_reply_to_message(message, i, len(messages))
            
            if should_reply:
                await handle_private_message(client, message, private_history)
                already_replied = True
            else:
                print("⏭️ Пропускаю сообщение (не подходит для ответа)")
        
        if valid_messages == 0:
            print("⚠️ Нет валидных сообщений для обработки")
        
        # Отмечаем все как прочитанные
        await client.send_read_acknowledge(dialog.entity)
        
    except Exception as e:
        print(f"❌ Ошибка при обработке диалога: {e}")
        # Все равно отмечаем как прочитанные
        try:
            await client.send_read_acknowledge(dialog.entity)
        except Exception:
            pass
async def decide_if_reply_to_message(message, index, total_messages):
    """Решает, стоит ли отвечать на конкретное сообщение"""
    text_lower = message.text.lower()
    
    # Всегда отвечаем на приветствия
    greetings = ["привет", "здравствуй", "добрый", "хай", "ку", "hello", "hi"]
    if any(greeting in text_lower for greeting in greetings):
        print("✅ Отвечу на приветствие")
        return True
    
    # Всегда отвечаем на прямые вопросы
    if "?" in message.text:
        print("✅ Отвечу на вопрос")
        return True
    
    # Если это последнее сообщение, отвечаем с вероятностью 80%
    if index == total_messages - 1 and random.random() < 0.8:
        print("✅ Отвечу на последнее сообщение")
        return True
    
    # На остальные сообщения отвечаем с базовой вероятностью
    base_chance = ANTIDETECT_CONFIG["private_message_reply_chance"]
    
    # Уменьшаем вероятность для старых сообщений
    if index < total_messages - 1:
        base_chance *= 0.3
    
    if random.random() < base_chance:
        print(f"✅ Отвечу (шанс {base_chance:.0%})")
        return True
    
    return False
async def process_channel_post_reaction(client, post, reactions_history):
    """Обрабатывает реакцию на пост в канале с учетом типа поста"""
    # Проверяем, не ставили ли уже реакцию на этот пост
    if str(post.id) in reactions_history.get("channel_posts_reacted", {}):
        print(f"⚠️ Уже ставил реакцию на пост {post.id}")
        return
    
    if not await can_react(post.id, reactions_history):
        print("⚠️ Не могу поставить реакцию на пост (ограничения)")
        return
    
    # Определяем тональность поста
    post_text = post.text or ""
    
    # Для дополнительных фото из альбома - пропускаем или ставим простую реакцию
    if post.grouped_id and not post_text:
        # 30% шанс поставить реакцию на дополнительное фото
        if random.random() < 0.3:
            sentiment = random.choice(["positive", "love", "cool"])
            print("📸 Ставлю реакцию на дополнительное фото из альбома")
        else:
            print("⏭️ Пропускаю реакцию на дополнительное фото")
            return
    else:
        # Обычная логика для основных постов
        sentiment = analyze_sentiment(post_text) if post_text else "neutral"
        
        # Для постов про кроссовки чаще позитивные реакции
        keywords = ["nike", "jordan", "adidas", "yeezy", "new balance", "кроссовки", "sneakers"]
        if any(keyword in post_text.lower() for keyword in keywords):
            if random.random() < 0.85:
                sentiment = random.choice(["positive", "love", "cool", "wow"])
    
    emoji = choose_reaction(sentiment, is_channel_post=True)
    
    # Случайная задержка
    delay = random.randint(*REACTIONS_CONFIG["reaction_delay"])
    print(f"⏳ Ставлю реакцию {emoji} на пост через {delay} сек...")
    await asyncio.sleep(delay)
    
    success = await send_reaction(client, channel_username, post.id, emoji, reactions_history)
    
    if success:
        # Сохраняем информацию о реакции на пост канала
        if "channel_posts_reacted" not in reactions_history:
            reactions_history["channel_posts_reacted"] = {}
        
        reactions_history["channel_posts_reacted"][str(post.id)] = {
            "reaction": emoji,
            "time": datetime.now().isoformat(),
            "is_album_photo": bool(post.grouped_id and not post.text)
        }
        save_reactions_history(reactions_history)

async def show_coordination_stats():
    """Показывает статистику координации ботов"""
    coordinator = SmartBotCoordinator()
    stats = coordinator.get_activity_stats()
    
    print("\n📊 СТАТИСТИКА КООРДИНАЦИИ БОТОВ")
    print("=" * 50)
    print(f"📝 Всего постов обработано: {stats['total_posts']}")
    print(f"⏰ Постов за последний час: {stats['posts_last_hour']}")
    print(f"📅 Постов за последние 24ч: {stats['posts_last_24h']}")
    print(f"💬 Всего комментариев: {stats['total_comments']}")
    
    if stats['bot_activity']:
        print("\n🤖 Активность по ботам:")
        for phone, activity in stats['bot_activity'].items():
            print(f"  {phone}: {activity['comments']} комментариев")
    
    # Показываем вероятности для следующего поста
    if coordinator.bots:
        print("\n🎲 Вероятности для следующего поста:")
        test_post_id = 99999  # Тестовый ID
        for bot in coordinator.bots:
            if bot.get('status') != 'banned':
                prob = coordinator.calculate_comment_probability(test_post_id, bot['phone'])
                print(f"  {bot['name']}: {prob:.1%}")

async def process_comment_reactions_and_replies(client, discussion_chat, post_text, reactions_history, history, my_comment_id=None):
    """Обрабатывает реакции и ответы на комментарии"""
    print("\n🔍 Проверяю комментарии для реакций и ответов...")
    
    # Добавляем защиту от пустого чата
    try:
        # Проверяем доступность чата
        await client.get_entity(discussion_chat)
    except Exception as e:
        print(f"⚠️ Не могу получить доступ к чату обсуждений: {e}")
        return
    
    if my_comment_id:
        reactions_history["my_messages"].append(str(my_comment_id))
        save_reactions_history(reactions_history)
    
    # Получаем сообщения из чата
    try:
        messages = await client.get_messages(discussion_chat, limit=30)
    except Exception as e:
        print(f"⚠️ Не могу получить сообщения из чата: {e}")
        return
    
    # Проверяем, есть ли вообще сообщения
    if not messages:
        print("📭 В чате обсуждений нет сообщений")
        return
    
    reactions_given = 0
    replies_given = 0
    
    # Фильтруем сообщения
    filtered_messages = [
        msg for msg in messages
        if str(msg.id) not in reactions_history["my_messages"]
        and msg.text
        and msg.date  # Проверяем, что у сообщения есть дата
        and (datetime.now(msg.date.tzinfo) - msg.date).total_seconds() <= 7200
    ]
    
    # Проверяем, есть ли комментарии для обработки
    if not filtered_messages:
        print("📭 Нет новых комментариев для реакций и ответов")
        return
    
    print(f"💬 Найдено {len(filtered_messages)} комментариев для обработки")
    
    for msg in filtered_messages:
        # Проверяем, что сообщение существует и имеет ID
        if not msg or not msg.id:
            continue
            
        is_reply_to_me = (
            msg.reply_to_msg_id and 
            str(msg.reply_to_msg_id) in reactions_history["my_messages"]
        )
        
        # Обработка реакции
        if await handle_comment_reaction(
            client, discussion_chat, msg, reactions_history, is_reply_to_me, reactions_given
        ):
            reactions_given += 1
        
        # Обработка ответа
        if await handle_comment_reply(
            client, discussion_chat, msg, post_text, history, reactions_history, replies_given, is_reply_to_me
        ):
            replies_given += 1
async def process_comment_reactions_and_replies_modified(
    client, discussion_chat, post_text, reactions_history, 
    history, my_comment_id, custom_reactions_config
):
    """Версия с кастомными настройками реакций для ботов, которые не комментировали"""
    print("\n🔍 Проверяю комментарии для реакций и ответов (усиленный режим)...")
    
    # Добавляем наш комментарий в список (если есть)
    if my_comment_id:
        reactions_history["my_messages"].append(str(my_comment_id))
        save_reactions_history(reactions_history)
    
    # Получаем последние комментарии
    messages = await client.get_messages(discussion_chat, limit=30)
    
    # Счетчики для этой сессии
    reactions_given = 0
    replies_given = 0
    
    # Фильтруем сообщения
    filtered_messages = [
        msg for msg in messages
        if str(msg.id) not in reactions_history["my_messages"]
        and msg.text
        and msg.date  # Проверяем, что у сообщения есть дата
        and (datetime.now(msg.date.tzinfo) - msg.date).total_seconds() <= 7200
    ]
    
    # Проверяем, есть ли комментарии для обработки
    if not filtered_messages:
        print("📭 Нет новых комментариев для реакций и ответов")
        return
    
    print(f"💬 Найдено {len(filtered_messages)} комментариев для обработки")
    print(f"⚡ Режим усиленных реакций (шанс увеличен на 50%)")
    
    for msg in filtered_messages:
        # Проверяем, что сообщение существует и имеет ID
        if not msg or not msg.id:
            continue
        
        # Проверяем, это ответ на наш комментарий?
        is_reply_to_me = (
            msg.reply_to_msg_id and 
            str(msg.reply_to_msg_id) in reactions_history["my_messages"]
        )
        
        # === ОБРАБОТКА РЕАКЦИЙ С УВЕЛИЧЕННЫМ ШАНСОМ ===
        if str(msg.id) not in reactions_history.get("reacted_to", []):
            # Используем модифицированные настройки
            if is_reply_to_me:
                reaction_chance = custom_reactions_config.get("react_to_replies_chance", 0.9)
            else:
                reaction_chance = custom_reactions_config.get("comment_reaction_chance", 0.25)
            
            if random.random() < reaction_chance and reactions_given < 5:  # Увеличен лимит до 5
                if await can_react(msg.id, reactions_history):
                    sentiment = analyze_sentiment(msg.text)
                    
                    # Для усиленного режима - больше позитивных реакций
                    if sentiment == "neutral" and random.random() < 0.5:
                        sentiment = "positive"
                    
                    emoji = choose_reaction(sentiment, is_reply_to_me)
                    
                    delay = random.randint(5, 30)  # Быстрее реагируем
                    print(f"⚡ Готовлю реакцию {emoji} на комментарий через {delay} сек...")
                    await asyncio.sleep(delay)
                    
                    if await send_reaction(client, discussion_chat, msg.id, emoji, reactions_history):
                        reactions_given += 1
                        print(f"   ✅ Поставил реакцию (всего в сессии: {reactions_given})")
        
        # === ОБРАБОТКА ОТВЕТОВ (без изменений) ===
        # Проверяем, стоит ли ответить на этот комментарий
        if should_reply_to_comment(msg.text, post_text, history, is_reply_to_me) and replies_given < 1:
            delay = random.randint(*REPLY_CONFIG["reply_delay"])
            print(f"💬 Готовлю ответ на комментарий через {delay} сек...")
            await asyncio.sleep(delay)
            
            sentiment = analyze_sentiment(msg.text)
            
            # Определяем стиль ответа
            if "?" in msg.text:
                style = "answer"
            elif sentiment == "positive":
                style = random.choice(["agree", "positive", "short_reaction"])
            elif sentiment == "negative":
                style = random.choice(["disagree", "neutral", "question"])
            else:
                style = random.choice(["neutral", "short_reaction", "question"])
            
            print(f"🤖 Генерирую ответ (стиль: {style})...")
            
            # Генерируем ответ с контекстом
            reply = await gpt_comment_with_context(post_text, style, history, replied_comment=msg.text)
            
            try:
                # Имитируем набор текста
                await simulate_typing(client, discussion_chat)
                
                sent_reply = await client.send_message(
                    entity=discussion_chat,
                    message=reply,
                    reply_to=msg.id
                )
                
                # Сохраняем в историю
                reactions_history["my_messages"].append(str(sent_reply.id))
                save_reactions_history(reactions_history)
                
                # Обновляем историю ответов
                history["last_reply_time"] = datetime.now().isoformat()
                history.setdefault("replies_count", {})
                post_key = str(post_text[:50])
                history["replies_count"][post_key] = history["replies_count"].get(post_key, 0) + 1
                save_history(history)
                
                print(f"✅ Ответил на комментарий: {reply}")
                replies_given += 1
                
            except Exception as e:
                print(f"❌ Ошибка при отправке ответа: {e}")
    
    # Итоговая статистика
    if reactions_given > 0 or replies_given > 0:
        print(f"\n📊 Итого в усиленном режиме:")
        print(f"   - Реакций поставлено: {reactions_given}")
        print(f"   - Ответов отправлено: {replies_given}")
    else:
        print("📭 Не нашел подходящих комментариев для реакций")

async def handle_comment_reply(client, discussion_chat, msg, post_text, history, reactions_history, replies_given, is_reply_to_me):
    """Обрабатывает ответ на комментарий с контекстом"""
    if replies_given >= 1:
        return False

    if not should_reply_to_comment(msg.text, post_text, history, is_reply_to_me):
        return False

    delay = random.randint(*REPLY_CONFIG["reply_delay"])
    print(f"💬 Готовлю ответ на комментарий через {delay} сек...")
    await asyncio.sleep(delay)

    sentiment = analyze_sentiment(msg.text)
    
    # Определяем стиль ответа на основе анализа
    if "?" in msg.text:  # Если вопрос
        style = "answer"
    elif sentiment == "positive":
        style = random.choice(["agree", "positive", "short_reaction"])
    elif sentiment == "negative":
        style = random.choice(["disagree", "neutral", "question"])
    else:
        style = random.choice(["neutral", "short_reaction", "question"])
    
    print(f"🤖 Генерирую ответ (стиль: {style})...")
    
    # Генерируем ответ С УЧЕТОМ КОНТЕКСТА комментария
    reply = await gpt_comment_with_context(post_text, style, history, replied_comment=msg.text)
    
    try:
        # Имитируем набор текста
        await simulate_typing(client, discussion_chat)
        
        sent_reply = await client.send_message(
            entity=discussion_chat,
            message=reply,
            reply_to=msg.id
        )
        
        # Сохраняем в историю
        reactions_history["my_messages"].append(str(sent_reply.id))
        save_reactions_history(reactions_history)
        
        # Обновляем историю ответов
        history["last_reply_time"] = datetime.now().isoformat()
        history.setdefault("replies_count", {})
        post_key = str(post_text[:50])
        history["replies_count"][post_key] = history["replies_count"].get(post_key, 0) + 1
        save_history(history)
        
        print(f"✅ Ответил на комментарий: {reply}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при отправке ответа: {e}")
        return False

async def handle_comment_reaction(client, discussion_chat, msg, reactions_history, is_reply_to_me, reactions_given):
    """Обрабатывает реакцию на комментарий"""
    if str(msg.id) in reactions_history["reacted_to"]:
        return False

    if reactions_given >= 3:
        return False

    reaction_chance = (
        REACTIONS_CONFIG["react_to_replies_chance"] if is_reply_to_me else REACTIONS_CONFIG["comment_reaction_chance"]
    )

    if random.random() >= reaction_chance:
        return False

    if not await can_react(msg.id, reactions_history):
        return False

    sentiment = analyze_sentiment(msg.text)
    emoji = choose_reaction(sentiment, is_reply_to_me)
    delay = random.randint(*REACTIONS_CONFIG["reaction_delay"])
    print(f"⏳ Готовлю реакцию {emoji} на комментарий через {delay} сек...")
    await asyncio.sleep(delay)

    if await send_reaction(client, discussion_chat, msg.id, emoji, reactions_history):
        return True
    return False

async def handle_comment_reply(client, discussion_chat, msg, post_text, history, reactions_history, replies_given, is_reply_to_me):
    """Обрабатывает ответ на комментарий"""
    if replies_given >= 1:
        return False

    if not should_reply_to_comment(msg.text, post_text, history, is_reply_to_me):
        return False

    delay = random.randint(*REPLY_CONFIG["reply_delay"])
    print(f"💬 Готовлю ответ на комментарий через {delay} сек...")
    await asyncio.sleep(delay)

    sentiment = analyze_sentiment(msg.text)
    if sentiment == "positive":
        style = random.choice(["agree", "positive", "short_reaction"])
    elif sentiment == "negative":
        style = random.choice(["disagree", "neutral", "question"])
    elif sentiment == "question":
        style = random.choice(["answer", "neutral", "positive"])
    else:
        style = random.choice(["neutral", "short_reaction", "question"])

    reply = await gpt_comment_with_context(post_text, style, history, msg.text)

    try:
        await simulate_typing(client, discussion_chat)
        sent_reply = await client.send_message(
            entity=discussion_chat,
            message=reply,
            reply_to=msg.id
        )
        reactions_history["my_messages"].append(str(sent_reply.id))
        history["last_reply_time"] = datetime.now().isoformat()
        post_key = str(post_text[:50])
        history["replies_count"][post_key] = history["replies_count"].get(post_key, 0) + 1
        save_history(history)
        save_reactions_history(reactions_history)
        print(f"✅ Ответил на комментарий: {reply}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при отправке ответа: {e}")
        return False

# Замените функцию gpt_comment_with_context на эту версию:

async def gpt_comment_with_context(post_text, style, history, replied_comment=None):
    """Генерирует комментарий через GPT с учетом контекста"""
    
    # Базовый контекст из поста
    context_text = post_text[:200] if post_text else ""
    
    # Добавляем контекст ответа, если отвечаем на комментарий
    context_addon = ""
    if replied_comment:
        context_addon = f"\nТы отвечаешь на комментарий: '{replied_comment}'. Отреагируй именно на него."
    
    # Список запрещенных слов
    forbidden_patterns = [
        "как ии", "как бот", "искусственный интеллект", "я запрограммирован",
        "как помощник", "могу помочь", "чем могу", "обращайтесь",
        "ai", "assistant", "бот", "ассистент", "готов помочь"
    ]
    
    # Подсказки по стилям
    style_prompts = {
        "positive": "Напиши что-то позитивное или восторженное",
        "negative": "Напиши скептическое мнение",
        "neutral": "Напиши нейтральный комментарий",
        "question": "Задай вопрос по теме",
        "short_reaction": "Короткая реакция 1-2 слова",
        "love": "Покажи что тебе очень нравится",
        "cool": "Напиши что это стильно/круто",
        "funny": "Пошути или напиши что-то веселое",
        "agree": "Согласись с комментарием",
        "disagree": "Вежливо не согласись",
        "answer": "Ответь на вопрос"
    }
    
    # Избегаем повторений
    avoid_text = ""
    if history.get("all_comments"):
        recent_comments = [c["text"] for c in history["all_comments"][-10:]]
        if recent_comments:
            avoid_text = f"\nНЕ повторяй эти фразы: {', '.join(recent_comments[:5])}"
    
    prompt = f"""Ты обычный парень из чата про кроссовки. 
НЕ бот, НЕ ассистент, НЕ ИИ - просто обычный парень.
Пиши ОЧЕНЬ КОРОТКО и ЕСТЕСТВЕННО.

{style_prompts.get(style, '')}

ВАЖНЫЕ ПРАВИЛА:
- Максимум 1-5 слов (редко больше)
- Пиши как в мессенджере: без точек, можешь с ошибками
- Используй простые слова: топ, норм, хз, крч, мб, пон
- НЕ пиши слова: {', '.join(forbidden_patterns)}
- Можешь писать все маленькими буквами
- Редко используй эмодзи (максимум 1)
- НИКОГДА не признавайся что ты бот или ИИ
- Если спрашивают про бота/ИИ - не понимай о чем речь
{avoid_text}
{context_addon}

Контекст: {context_text[:100]}

Напиши ОДИН короткий комментарий:"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=1.0,
        )
        msg = response.choices[0].message.content.strip()
        
        # Постобработка
        msg = msg.rstrip('.')
        msg = msg.strip('"\'')
        
        # 70% шанс сделать все маленькими буквами
        if random.random() < 0.7:
            msg = msg.lower()
        
        # Проверяем на запрещенные слова
        msg_lower = msg.lower()
        for forbidden in forbidden_patterns:
            if forbidden in msg_lower:
                simple_comments = ["топ", "класс", "норм", "ок", "хочу", "круто", "вау"]
                msg = random.choice(simple_comments)
                break
        
        # Финальная проверка на подозрительные фразы
        ai_indicators = ["я бот", "я ии", "я ассистент", "могу помочь", "готов помочь"]
        if any(indicator in msg_lower for indicator in ai_indicators):
            msg = random.choice(["норм", "ок", "топ", "класс"])
        
        print(f"✅ GPT сгенерировал: {msg}")
        return msg
        
    except Exception as e:
        print(f"❌ Ошибка OpenAI: {e}")
        # Улучшенный список запасных комментариев
        fallback_by_style = {
            "positive": ["топ", "класс", "круто", "огонь", "имба"],
            "negative": ["ну такое", "не очень", "хз", "не мое", "спорно"],
            "neutral": ["норм", "ок", "пойдет", "можно", "неплохо"],
            "question": ["сколько?", "где?", "почем?", "откуда?", "когда?"],
            "short_reaction": ["вау", "ого", "+", "++", "жиза"],
            "love": ["хочу", "кайф", "обожаю", "мечта", "надо"],
            "cool": ["стильно", "свежо", "четко", "найс", "чил"],
            "funny": ["ахах", "ору", "ржу", "лол", "топ"],
            "agree": ["да", "точно", "согласен", "+", "факт"],
            "disagree": ["не", "неа", "не думаю", "сомневаюсь", "хз"],
            "answer": ["да", "нет", "может", "хз", "думаю да"]
        }
        
        comments = fallback_by_style.get(style, ["норм", "ок", "топ"])
        return random.choice(comments)
    
    # Расширенные стили с более естественными примерами
    style_prompts = {
        "positive": "Напиши короткий позитивный комментарий. Примеры: 'красиво', 'топ', 'хочу такие', 'огонь просто'",
        "negative": "Напиши скептический комментарий. Примеры: 'ну такое', 'не очень', 'хз', 'не мое'",
        "neutral": "Напиши нейтральный комментарий. Примеры: 'норм', 'ок', 'пойдет', 'можно'",
        "question": "Задай короткий вопрос. Примеры: 'сколько?', 'где взял?', 'есть еще?', 'почем?'",
        "short_reaction": "Очень короткая реакция. Примеры: 'вау', 'ого', '+', 'жиза', 'база'",
        "agree": "Согласись коротко. Примеры: 'согласен', 'плюсую', 'точно', 'факт'",
        "disagree": "Не согласись вежливо. Примеры: 'не согласен', 'спорно', 'хз хз', 'ну не знаю'",
        "answer": "Короткий ответ. Примеры: 'да', 'нет', 'может быть', 'посмотрим'",
        "funny": "Забавный комментарий. Примеры: 'ахахах', 'ору', 'ржу не могу', 'топ прикол'",
        "love": "Восхищение. Примеры: 'обожаю', 'хочу', 'мечта', 'кайф'",
        "cool": "Стильный комментарий. Примеры: 'стильно', 'свежо', 'четко', 'найс'"
    }
    
    # Специальные правила для фото без текста
    if context_text == "Пост без текста (только фото/медиа)":
        photo_comments = {
            "positive": ["красиво", "топ фото", "огонь", "класс", "четко"],
            "love": ["хочу", "кайф", "обожаю такое", "мечта"],
            "cool": ["стильно", "свежо", "найс", "четко"],
            "short_reaction": ["вау", "ого", "++", "🔥", "топ"],
            "question": ["что это?", "где это?", "откуда фото?", "твое?"],
            "neutral": ["норм", "ок", "неплохо", "можно"]
        }
        
        if style in photo_comments:
            return random.choice(photo_comments[style])
    
    context_addon = ""
    if replied_comment:
        context_addon = f"\nТы отвечаешь на комментарий: '{replied_comment}'. Отреагируй именно на него."
    
    recent_comments = [c["text"] for c in history["all_comments"][-10:]]
    avoid_text = f"\nНЕ используй эти фразы: {', '.join(recent_comments)}" if recent_comments else ""
    
    # Список запрещенных слов/фраз которые выдают бота
    forbidden_patterns = [
        "фотка", "фоточка", "контент", "пост", "публикация", 
        "материал", "изображение", "снимок", "кадр",
        "ассистент", "помогу", "помочь", "обращайтесь"
    ]
    
    prompt = f"""Ты обычный человек в телеграме, подписчик канала про кроссовки. 
НЕ бот, НЕ ассистент, НЕ ИИ - просто обычный парень.
Пиши ОЧЕНЬ КОРОТКО и ЕСТЕСТВЕННО.

{style_prompts.get(style, '')}

ВАЖНЫЕ ПРАВИЛА:
- Максимум 1-5 слов (редко больше)
- Пиши как в мессенджере: без точек, можешь с ошибками
- Используй простые слова: топ, норм, хз, крч, мб, пон
- НЕ пиши слова: {', '.join(forbidden_patterns)}
- Можешь писать все маленькими буквами
- Редко используй эмодзи (максимум 1)
- НИКОГДА не признавайся что ты бот или ИИ
- Если спрашивают про бота/ИИ - не понимай о чем речь
{avoid_text}
{context_addon}

Контекст: {context_text[:100]}

Напиши ОДИН короткий комментарий:"""
    
    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=1.0,
        )
        msg = response.choices[0].message.content.strip()
        
        # Постобработка
        msg = msg.rstrip('.')
        msg = msg.strip('"\'')
        
        # 70% шанс сделать все маленькими буквами
        if random.random() < 0.7:
            msg = msg.lower()
        
        # Проверяем на запрещенные слова
        msg_lower = msg.lower()
        for forbidden in forbidden_patterns:
            if forbidden in msg_lower:
                simple_comments = ["топ", "класс", "норм", "ок", "хочу", "круто", "вау"]
                msg = random.choice(simple_comments)
                break
        
        # Финальная проверка на подозрительные фразы
        ai_indicators = ["я бот", "я ии", "я ассистент", "могу помочь", "готов помочь"]
        if any(indicator in msg_lower for indicator in ai_indicators):
            msg = random.choice(["норм", "ок", "топ", "класс"])
        
        print(f"✅ GPT сгенерировал: {msg}")
        return msg
        
    except Exception as e:
        print(f"❌ Ошибка OpenAI: {e}")
        # Улучшенный список запасных комментариев
        fallback_by_style = {
            "positive": ["топ", "класс", "круто", "огонь", "имба"],
            "negative": ["ну такое", "не очень", "хз", "не мое", "спорно"],
            "neutral": ["норм", "ок", "пойдет", "можно", "неплохо"],
            "question": ["сколько?", "где?", "почем?", "откуда?", "когда?"],
            "short_reaction": ["вау", "ого", "+", "++", "жиза"],
            "love": ["хочу", "кайф", "обожаю", "мечта", "надо"],
            "cool": ["стильно", "свежо", "четко", "найс", "чил"],
            "funny": ["ахах", "ору", "ржу", "лол", "топ"],
        }
        
        comments = fallback_by_style.get(style, ["норм", "ок", "топ"])
        return random.choice(comments)
    
    context_addon = ""
    if replied_comment:
        context_addon = f"\nТы отвечаешь на комментарий: '{replied_comment}'. Отреагируй именно на него."
    
    recent_comments = [c["text"] for c in history["all_comments"][-10:]]
    avoid_text = f"\nНЕ используй эти фразы: {', '.join(recent_comments)}" if recent_comments else ""
    
    # Список запрещенных слов/фраз которые выдают бота
    forbidden_patterns = [
        "фотка", "фоточка", "контент", "пост", "публикация", 
        "материал", "изображение", "снимок", "кадр"
    ]
    
    prompt = f"""Ты обычный человек в телеграме. Пиши ОЧЕНЬ КОРОТКО и ЕСТЕСТВЕННО.

{style_prompts.get(style, '')}

ВАЖНЫЕ ПРАВИЛА:
- Максимум 1-5 слов (редко больше)
- Пиши как в мессенджере: без точек, можешь с ошибками
- Используй простые слова: топ, норм, хз, крч, мб, пон
- НЕ пиши слова: {', '.join(forbidden_patterns)}
- Можешь писать все маленькими буквами
- Редко используй эмодзи (максимум 1)
{avoid_text}
{context_addon}

Контекст: {context_text[:100]}

Напиши ОДИН короткий комментарий:"""
    
    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,  # Уменьшаем для более коротких ответов
            temperature=1.0,  # Увеличиваем для разнообразия
        )
        msg = response.choices[0].message.content.strip()
        
        # Постобработка
        # Убираем точки в конце
        msg = msg.rstrip('.')
        
        # Убираем кавычки если есть
        msg = msg.strip('"\'')
        
        # 70% шанс сделать все маленькими буквами
        if random.random() < 0.7:
            msg = msg.lower()
        
        # Проверяем на запрещенные слова
        msg_lower = msg.lower()
        for forbidden in forbidden_patterns:
            if forbidden in msg_lower:
                # Если нашли запрещенное слово, используем простой комментарий
                simple_comments = ["топ", "класс", "норм", "ок", "хочу", "круто", "вау"]
                msg = random.choice(simple_comments)
                break
        
        print(f"✅ GPT сгенерировал: {msg}")
        return msg
        
    except Exception as e:
        print(f"❌ Ошибка OpenAI: {e}")
        # Улучшенный список запасных комментариев
        fallback_by_style = {
            "positive": ["топ", "класс", "круто", "огонь", "имба"],
            "negative": ["ну такое", "не очень", "хз", "не мое", "спорно"],
            "neutral": ["норм", "ок", "пойдет", "можно", "неплохо"],
            "question": ["сколько?", "где?", "почем?", "откуда?", "когда?"],
            "short_reaction": ["вау", "ого", "+", "++", "жиза"],
            "love": ["хочу", "кайф", "обожаю", "мечта", "надо"],
            "cool": ["стильно", "свежо", "четко", "найс", "чил"],
            "funny": ["ахах", "ору", "ржу", "лол", "топ"],
        }
        
        comments = fallback_by_style.get(style, ["норм", "ок", "топ"])
        return random.choice(comments)


# Дополнительная функция для генерации более разнообразных комментариев
def get_contextual_comment(post_text: str, style: str):
    """Генерирует контекстный комментарий без GPT"""
    post_lower = post_text.lower()
    
    # Определяем тематику поста
    if any(word in post_lower for word in ["nike", "adidas", "jordan", "yeezy", "кроссовки", "sneakers"]):
        theme = "sneakers"
    elif any(word in post_lower for word in ["supreme", "palace", "stussy", "одежда", "fashion"]):
        theme = "fashion"
    else:
        theme = "general"
    
    # Комментарии по темам и стилям
    themed_comments = {
        "sneakers": {
            "positive": ["хочу такие", "огонь пара", "топ модель", "надо брать", "четкие"],
            "love": ["мечта", "влюбился", "обожаю такие", "кайф", "хочу хочу хочу"],
            "question": ["сколько стоят?", "где купить?", "есть размеры?", "оригинал?", "почем брал?"],
            "cool": ["свежие", "стильные", "четко", "найс пара", "фреш"]
        },
        "fashion": {
            "positive": ["стильно", "топ лук", "огонь", "круто выглядит", "четко"],
            "love": ["хочу такой", "кайф", "обожаю", "мечта", "влюбился в лук"],
            "question": ["где купить?", "сколько?", "что за бренд?", "есть еще?"],
            "cool": ["свежо", "стиль", "найс", "чил", "вайб"]
        },
        "general": {
            "positive": ["топ", "класс", "круто", "норм", "неплохо"],
            "love": ["кайф", "хочу", "обожаю", "мечта", "огонь"],
            "question": ["что это?", "где?", "сколько?", "откуда?"],
            "cool": ["найс", "четко", "стильно", "свежо", "норм"]
        }
    }
    
    theme_comments = themed_comments.get(theme, themed_comments["general"])
    style_comments = theme_comments.get(style, theme_comments["positive"])
    
    return random.choice(style_comments)

async def find_discussion_msg_id(client, last_channel_post, discussion_chat):
    """Находит ID сообщения обсуждения для данного поста"""
    try:
        # Получаем последние сообщения из обсуждения
        messages = await client.get_messages(discussion_chat, limit=50)
        
        for msg in messages:
            # Проверяем, является ли сообщение форвардом из канала
            if msg.fwd_from and hasattr(msg.fwd_from, 'channel_post'):
                if msg.fwd_from.channel_post == last_channel_post.id:
                    return msg.id
            
            # Альтернативный способ - проверяем reply_to
            if hasattr(msg, 'reply_to') and msg.reply_to:
                if hasattr(msg.reply_to, 'reply_to_msg_id'):
                    # Иногда обсуждение ссылается на пост через reply_to
                    pass
        
        return None
    except Exception as e:
        print(f"❌ Ошибка поиска обсуждения: {e}")
        return None

async def get_last_channel_post(client, channel_username):
    """Получает последний пост из канала (пропускает медиа-группы)"""
    try:
        messages = await client.get_messages(channel_username, limit=10)
        
        for message in messages:
            # Пропускаем сообщения, которые являются частью медиа-группы
            # но не являются первым сообщением в группе
            if message.grouped_id:
                # Это часть альбома
                # Проверяем, является ли это первым постом в группе
                if not message.text:
                    # Это дополнительное фото в альбоме - пропускаем
                    print(f"⏭️ Пропускаю фото из альбома (ID: {message.id})")
                    continue
            
            # Возвращаем первый подходящий пост
            return message
            
        print("❌ Не найдено подходящих постов")
        return None
        
    except Exception as e:
        print(f"❌ Ошибка при получении последнего поста: {e}")
        return None

async def send_comment_and_get_id(client, discussion_chat, discussion_msg_id, comment, post_id, history):
    """Отправляет комментарий в обсуждение и возвращает объект отправленного сообщения"""
    try:
        # Имитируем набор текста
        await simulate_typing(client, discussion_chat)
        
        sent_msg = await client.send_message(
            entity=discussion_chat,
            message=comment,
            reply_to=discussion_msg_id
        )
        
        # Обновляем историю
        now = datetime.now()
        post_key = str(post_id)
        history["posts_commented"][post_key] = {
            "comment_id": sent_msg.id,
            "time": now.isoformat(),
            "text": comment
        }
        history["all_comments"].append({
            "post_id": post_key,
            "comment_id": sent_msg.id,
            "time": now.isoformat(),
            "text": comment
        })
        today = now.strftime("%Y-%m-%d")
        history.setdefault("daily_count", {})
        history["daily_count"][today] = history["daily_count"].get(today, 0) + 1
        save_history(history)
        print(f"✅ Оставлен комментарий: {comment}")
        return sent_msg
    except Exception as e:
        print(f"❌ Ошибка при отправке комментария: {e}")
        return None

# Замените функцию handle_discussion_and_comments на эту версию:

# Добавьте эти изменения в ваш main.py или Ботяра

# В начало файла добавьте импорт:
from smart_bot_coordinator import SmartBotCoordinator, should_comment_smart

# Создайте глобальный координатор
bot_coordinator = SmartBotCoordinator()

# Модифицируйте функцию handle_discussion_and_comments:
async def handle_discussion_and_comments(client, last_channel_post, post_text, history, reactions_history):
    """Обрабатывает обсуждение с умным распределением комментариев"""
    
    # Для дополнительных фото из альбома не комментируем
    if last_channel_post.grouped_id and not last_channel_post.text:
        print("⏭️ Пропускаю комментирование дополнительного фото из альбома")
        return
    
    # Анализируем контент поста
    analyzer = ContentAnalyzer()
    has_image = bool(last_channel_post.media or last_channel_post.grouped_id)
    post_analysis = analyzer.analyze_post(post_text, has_image)
    
    # Если это альбом, добавляем информацию
    if last_channel_post.grouped_id:
        post_analysis["is_album"] = True
        post_analysis["main_topic"] = "album" if post_analysis["main_topic"] == "general" else post_analysis["main_topic"]
    
    print("\n📊 Анализ поста:")
    print(f"  - Бренды: {', '.join(post_analysis['brands']) if post_analysis['brands'] else 'не найдено'}")
    print(f"  - Тема: {post_analysis['main_topic']}")
    print(f"  - Тип релиза: {post_analysis['release_type']}")
    print(f"  - Цвета: {', '.join(post_analysis['colors']) if post_analysis['colors'] else 'не указаны'}")
    print(f"  - Настроение: {post_analysis['sentiment']}")
    if post_analysis.get("is_album"):
        print("  - Тип: Альбом с фотографиями")
    
    # Продолжаем обычную логику комментирования
    discussion_msg_id = await find_discussion_msg_id(client, last_channel_post, discussion_chat)
    my_comment_id = None
    
    if not discussion_msg_id:
        print("❌ Не найдено обсуждение для поста.")
        return
    
    # УМНАЯ ПРОВЕРКА: должен ли этот бот комментировать
    me = await client.get_me()
    bot_phone = f"+{me.phone}" if not me.phone.startswith('+') else me.phone
    
    # Используем координатор для принятия решения
    should_comment = await bot_coordinator.should_bot_comment(
        last_channel_post.id,
        bot_phone,
        force_at_least_one=True
    )
    
    # Дополнительные проверки безопасности
    if should_comment and can_comment(last_channel_post.id, history):
        style = get_comment_style(history)
        wait_time = random.randint(10, 30)
        
        # Добавляем случайность для разных ботов
        if len(bot_coordinator.bots) > 1:
            # Увеличиваем разброс времени при множестве ботов
            wait_time = random.randint(10, 60)
        
        print(f"\n⏳ Жду {wait_time} секунд перед комментарием к посту...")
        await asyncio.sleep(wait_time)
        
        comment = await gpt_comment_with_context(post_text, style, history)
        sent_msg = await send_comment_and_get_id(client, discussion_chat, discussion_msg_id, comment, last_channel_post.id, history)
        
        if sent_msg:
            my_comment_id = sent_msg.id
            print(f"✅ Бот {bot_phone} оставил комментарий")
    else:
        if not should_comment:
            print(f"\n🎲 Координатор решил, что бот {bot_phone} НЕ будет комментировать этот пост")
        else:
            print("\n⛔ Комментирование поста заблокировано системой защиты")
    
    # Обрабатываем реакции и ответы на другие комментарии
    # Небольшая случайная задержка
    await asyncio.sleep(random.randint(20, 60))

if not my_comment_id:
    # Бот не комментировал - компенсируем реакциями
    print("🎯 Бот не комментировал - включаю усиленный режим реакций")
    
    # Создаем модифицированные настройки
    modified_config = {
        "comment_reaction_chance": REACTIONS_CONFIG["comment_reaction_chance"] * 1.5,
        "react_to_replies_chance": REACTIONS_CONFIG["react_to_replies_chance"],
        "reaction_delay": REACTIONS_CONFIG["reaction_delay"],
        "max_reactions_per_session": 8
    }
    
    # Вызываем напрямую с await
    async def call_process_comment_reactions_and_replies_modified():
        await process_comment_reactions_and_replies_modified(
            client, discussion_chat, post_text, reactions_history,
            history, my_comment_id, modified_config
        )
    asyncio.create_task(call_process_comment_reactions_and_replies_modified())
else:
    # Бот прокомментировал - обычный режим
    async def call_process_comment_reactions_and_replies():
        await process_comment_reactions_and_replies(
            client, discussion_chat, post_text, reactions_history, 
            history, my_comment_id
        )
    asyncio.create_task(call_process_comment_reactions_and_replies())


async def generate_smart_comment(post_text: str, analysis: Dict, history) -> str:
    """Генерирует умный комментарий на основе анализа"""
    
    # Специальная обработка для альбомов
    if analysis.get("is_album"):
        # Комментарии про количество/выбор
        album_styles = ["positive", "love", "question", "cool"]
        style = random.choice(album_styles)
    elif analysis["has_question"]:
        style = "answer"
    elif analysis["main_topic"] == "sale":
        style = random.choice(["positive", "short_reaction", "question"])
    elif analysis["main_topic"] == "collaboration":
        style = random.choice(["positive", "love", "question"]) 
    elif analysis["brands"] and "nike" in analysis["brands"]:
        style = random.choice(["positive", "love", "cool"])
    elif analysis["release_type"] == "new_release":
        style = random.choice(["positive", "question", "love"])
    elif analysis["sentiment"] == "positive":
        style = random.choice(["positive", "agree", "cool"])
    elif analysis["sentiment"] == "negative":
        style = random.choice(["neutral", "disagree", "question"])
    else:
        style = get_comment_style(history)
    
    # Для постов без текста (только фото)
    if not post_text or post_text == "Пост без текста (только фото/медиа)":
        return await generate_photo_comment(analysis, style)
    
    # Генерируем контекстный комментарий
    return await generate_contextual_comment(analysis, style)

async def generate_photo_comment(analysis: Dict, style: str) -> str:
    """Генерирует комментарий для поста с фото"""
    photo_comments = {
        "positive": ["красиво", "топ фото", "огонь", "класс", "четкое фото", "найс"],
        "love": ["хочу", "кайф", "обожаю", "мечта", "влюбился"],
        "cool": ["стильно", "свежо", "найс", "четко", "фреш"],
        "short_reaction": ["вау", "ого", "++", "🔥", "топ", "база"],
        "question": ["что это?", "где это?", "откуда фото?", "твое?", "что за модель?"],
        "neutral": ["норм", "ок", "неплохо", "можно", "пойдет"]
    }
    
    # Если определили бренды по другим признакам
    if analysis.get("brands"):
        brand = analysis["brands"][0]
        brand_comments = {
            "nike": ["найк топ", "swoosh 🔥", "nike forever"],
            "adidas": ["три полоски", "адик огонь", "adidas 💪"],
            "new_balance": ["nb красавцы", "нью бэланс топ", "nb 🔥"]
        }
        if brand in brand_comments and random.random() < 0.3:
            return random.choice(brand_comments[brand])
    
    return random.choice(photo_comments.get(style, photo_comments["neutral"]))


# Улучшенная функция для анализа комментариев других пользователей
async def analyze_and_reply_to_comment(comment_text: str) -> Tuple[bool, str]:
    """Анализирует комментарий и решает, стоит ли отвечать"""
    
    comment_lower = comment_text.lower()
    
    # Приоритетные случаи для ответа
    priority_patterns = {
        "direct_question": {
            "patterns": ["сколько", "где купить", "когда релиз", "есть размер", "почем"],
            "reply_chance": 0.8,
            "style": "answer"
        },
        "opinion_request": {
            "patterns": ["как вам", "что думаете", "стоит брать", "норм или нет"],
            "reply_chance": 0.7,
            "style": "opinion"
        },
        "disagreement": {
            "patterns": ["не согласен", "фигня", "переоценены", "не стоят"],
            "reply_chance": 0.6,
            "style": "polite_disagree"
        },
        "enthusiasm": {
            "patterns": ["огонь", "хочу такие", "мечта", "shut up and take"],
            "reply_chance": 0.5,
            "style": "agree"
        }
    }
    
    for pattern_type, config in priority_patterns.items():
        if any(pattern in comment_lower for pattern in config["patterns"]):
            if random.random() < config["reply_chance"]:
                return True, config["style"]
    
    # Базовая вероятность ответа
    return random.random() < 0.15, "neutral"
def can_comment(post_id, history):
    """Проверяет, можно ли комментировать данный пост согласно настройкам защиты от спама"""
    now = datetime.now()
    post_key = str(post_id)
    
    # Проверка: не комментировали ли этот пост ранее
    if post_key in history.get("posts_commented", {}):
        print(f"❌ Уже комментировал пост {post_id}")
        return False
    
    # Проверка: не превышен ли лимит комментариев за день
    daily_count = history.get("daily_count", {})
    today = now.strftime("%Y-%m-%d")
    if daily_count.get(today, 0) >= SPAM_PROTECTION["max_comments_per_day"]:
        print(f"❌ Превышен дневной лимит ({daily_count.get(today, 0)}/{SPAM_PROTECTION['max_comments_per_day']})")
        return False
    
    # Проверка: не слишком ли быстро комментируем
    if history.get("all_comments"):
        last_comment_time = datetime.fromisoformat(history["all_comments"][-1]["time"])
        time_diff = (now - last_comment_time).total_seconds()
        if time_diff < SPAM_PROTECTION["min_time_between_comments"]:
            wait_time = SPAM_PROTECTION["min_time_between_comments"] - time_diff
            print(f"❌ Слишком рано. Подождите еще {int(wait_time)} секунд")
            return False
    
    # Проверка часового лимита
    hour_ago = now - timedelta(hours=1)
    recent_comments = [c for c in history["all_comments"] 
                      if datetime.fromisoformat(c["time"]) > hour_ago]
    if len(recent_comments) >= SPAM_PROTECTION["max_comments_per_hour"]:
        print(f"❌ Превышен лимит комментариев в час ({len(recent_comments)}/{SPAM_PROTECTION['max_comments_per_hour']})")
        return False
    
    print("✅ Проверки пройдены, можно комментировать")
    return True

def print_post_info(post):
    """Печатает информацию о посте с учетом медиа-групп"""
    post_text = post.text or ""
    
    print("\n" + "="*60)
    print("📝 ИНФОРМАЦИЯ О ПОСТЕ:")
    print("="*60)
    print(f"🆔 ID поста: {post.id}")
    print(f"📅 Дата: {post.date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверяем тип поста
    if post.grouped_id:
        print(f"🖼️ Часть альбома: {post.grouped_id}")
    
    if post.media:
        print(f"📎 Медиа: {type(post.media).__name__}")
    
    if post_text:
        print("\n📄 ТЕКСТ ПОСТА:")
        print("-"*60)
        if len(post_text) > 500:
            print(f"{post_text[:500]}...")
            print(f"\n(Полная длина: {len(post_text)} символов)")
        else:
            print(post_text)
        print("-"*60)
    else:
        if post.grouped_id:
            print("\n⚠️ Дополнительное фото из альбома (без текста)")
        else:
            print("\n⚠️ Пост без текста")
    
    print("="*60 + "\n")
    return post_text


def get_comment_style(history):
    """Выбирает стиль комментария, избегая повторений"""
    styles = ["positive", "negative", "neutral", "question", "short_reaction", "funny", "love", "cool"]
    
    if SPAM_PROTECTION["avoid_duplicate_style"] and history["last_styles"]:
        # Избегаем последних 3 использованных стилей
        recent_styles = history["last_styles"][-3:]
        available_styles = [s for s in styles if s not in recent_styles]
        if available_styles:
            style = random.choice(available_styles)
        else:
            style = random.choice(styles)
    else:
        style = random.choice(styles)
    
    # Сохраняем выбранный стиль
    history["last_styles"].append(style)
    if len(history["last_styles"]) > 5:
        history["last_styles"] = history["last_styles"][-5:]
    
    save_history(history)
    return style

def is_comment_unique(comment, history):
    """Проверяет уникальность комментария"""
    # Проверка на точное совпадение
    for old_comment in history["all_comments"][-10:]:  # Проверяем последние 10
        if old_comment["text"].lower() == comment.lower():
            return False
    
    # Проверка на минимум уникальных слов
    words = set(comment.lower().split())
    if len(words) < SPAM_PROTECTION["min_unique_words"]:
        return False
    
    return True

async def main_bot_work(client, history, reactions_history):
    """Основная работа бота с улучшенной обработкой альбомов"""
    # Сбрасываем счетчик реакций за сессию
    reactions_history["session_reactions_count"] = 0
    save_reactions_history(reactions_history)
    
    # Получаем последний пост
    last_channel_post = await get_last_channel_post(client, channel_username)
    if not last_channel_post:
        return
    
    # Проверяем, не обрабатывали ли мы уже этот пост
    post_key = str(last_channel_post.id)
    if post_key in history.get("posts_commented", {}):
        print(f"⚠️ Пост {post_key} уже был обработан")
        
        # Ищем следующий необработанный пост
        messages = await client.get_messages(channel_username, limit=20)
        found_new = False
        
        for msg in messages:
            if str(msg.id) not in history.get("posts_commented", {}) and (msg.text or not msg.grouped_id):
                last_channel_post = msg
                found_new = True
                print(f"✅ Найден необработанный пост: {msg.id}")
                break
        
        if not found_new:
            print("❌ Все последние посты уже обработаны")
            return
    
    post_text = print_post_info(last_channel_post)
    
    # Если это альбом, собираем все связанные медиа
    if last_channel_post.grouped_id:
        print(f"\n📸 Обнаружен альбом (grouped_id: {last_channel_post.grouped_id})")
        album_messages = await client.get_messages(
            channel_username, 
            limit=10,
            min_id=last_channel_post.id - 10,
            max_id=last_channel_post.id + 10
        )
        
        media_count = sum(1 for msg in album_messages if msg.grouped_id == last_channel_post.grouped_id)
        print(f"📸 Фотографий в альбоме: {media_count}")
    
    if not post_text:
        post_text = "Пост без текста (только фото/медиа)"
    
    # Пауза перед реакцией (имитация просмотра)
    await asyncio.sleep(random.uniform(3, 10))
    
    # Ставим реакцию на пост в канале
    await process_channel_post_reaction(client, last_channel_post, reactions_history)
    
    # Обработка обсуждения и комментариев
    await handle_discussion_and_comments(client, last_channel_post, post_text, history, reactions_history)

async def enhanced_main():
    """Основная функция с антидетект защитой"""
    print(f"\n🚀 Запуск бота с антидетект защитой - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ИСПРАВЛЕННАЯ проверка папки sessions
    print("\n📁 Проверяю файлы в папке sessions:")
    if os.path.exists('sessions'):  # Изменено с 'session' на 'sessions'
        files = os.listdir('sessions')
        print(f"Найдено файлов: {len(files)}")
        for file in files:
            print(f"  - {file}")
    else:
        print("❌ Папка sessions не найдена!")
        print("📁 Создаю папку sessions...")
        os.makedirs('sessions', exist_ok=True)
    
    print(f"\n🔍 Ищу файл: {session_file}")
    print(f"📍 Файл существует: {os.path.exists(session_file)}")
    
    print(f"📢 Канал: @{channel_username}")
    print(f"💬 Чат обсуждения: @{discussion_chat}")
    print(f"👍 Реакции на посты: 100%")
    print(f"💭 Умные ответы на комментарии: включены")
        
    # Проверяем время работы
    if not await should_work_now():
        print("💤 Не время для работы")
        return
        
    # Загружаем истории
    history = load_history()
    reactions_history = load_reactions_history()
        
    # Проверяем лимиты
    if not await check_and_limit_actions(history):
        return
        
    # Определяем длительность сессии
    session_duration = random.randint(*ANTIDETECT_CONFIG["session_duration"])
    session_end_time = datetime.now() + timedelta(seconds=session_duration)
    print(f"⏱ Длительность сессии: {session_duration//60} минут")
        
    client = TelegramClient(session_file, api_id, api_hash, proxy=proxy)
        
    # Подключаемся и проверяем авторизацию
    await client.connect()
        
    if not await client.is_user_authorized():
        print("❌ Сессия не найдена или недействительна")
        print("📱 Требуется авторизация...")
        phone = input("Введите номер телефона (с кодом страны): ")
        await client.send_code_request(phone)
        code = input("Введите код из Telegram: ")
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            print(f"❌ Ошибка авторизации: {e}")
            password = input("Введите пароль 2FA (если есть): ")
            await client.sign_in(password=password)
        
    print("✅ Подключение установлено")
        
    try:
        # Обновляем статус онлайн
        await update_online_status(client, True)
            
        # Начальная пауза (имитация обычного поведения)
        await asyncio.sleep(random.uniform(5, 15))
            
        # Выполняем случайные действия
        await perform_random_actions(client)
            
        # Проверяем личные сообщения
        await monitor_private_messages(client)
            
        # Основная работа бота
        await main_bot_work(client, history, reactions_history)
            
        # Дополнительные случайные действия в конце
        if datetime.now() < session_end_time:
            await perform_random_actions(client)
        print("\n✅ Основная работа завершена")
        print("🔄 Переключаюсь в режим постоянного мониторинга...")

        # Обновляем статус (остаемся онлайн)
        await update_online_status(client, True)

        # Запускаем бесконечный цикл мониторинга
        await continuous_monitoring_loop(client, reactions_history)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Этот код выполнится только при принудительной остановке
        try:
            await update_online_status(client, False)
        except Exception as e:
            print(f"Error during updating status: {e}")
        try:
            await client.disconnect()
        except Exception as e:
            print(f"Error during disconnection: {e}")
        print(f"\n👋 Полное завершение работы - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n🚀 Запуск бота с антидетект защитой - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📢 Канал: @{channel_username}")
    print(f"💬 Чат обсуждения: @{discussion_chat}")
    print("👍 Реакции на посты: 100%")
    print("💭 Умные ответы на комментарии: включены")
    
    client = None
    
    try:
        # Проверяем время работы
        if not await should_work_now():
            print("💤 Не время для работы")
            return
        
        # Загружаем истории
        history = load_history()
        reactions_history = load_reactions_history()
        
        # Проверяем лимиты
        if not await check_and_limit_actions(history):
            return
        
        # Определяем длительность сессии
        session_duration = random.randint(*ANTIDETECT_CONFIG["session_duration"])
        session_end_time = datetime.now() + timedelta(seconds=session_duration)
        print(f"⏱ Длительность сессии: {session_duration//60} минут")
        
        client = TelegramClient(session_file, api_id, api_hash, proxy=proxy)
        
        # Подключаемся и проверяем авторизацию
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Сессия не найдена или недействительна")
            print("📱 Требуется авторизация...")
            phone = input("Введите номер телефона (с кодом страны): ")
            await client.send_code_request(phone)
            code = input("Введите код из Telegram: ")
            try:
                await client.sign_in(phone, code)
            except Exception as e:
                print(f"❌ Ошибка авторизации: {e}")
                password = input("Введите пароль 2FA (если есть): ")
                await client.sign_in(password=password)
        
        print("✅ Подключение установлено")
        
        # Обновляем статус онлайн
        await update_online_status(client, True)
        
        # Начальная пауза (имитация обычного поведения)
        await asyncio.sleep(random.uniform(5, 15))
        
        # Выполняем случайные действия
        await perform_random_actions(client)
        
        # Проверяем личные сообщения
        await monitor_private_messages(client)
        
        # Основная работа бота
        await main_bot_work(client, history, reactions_history)
        
        # Дополнительные случайные действия в конце
        if datetime.now() < session_end_time:
            await perform_random_actions(client)
        
        # После основной работы запускаем постоянный мониторинг
        print("\n✅ Основная работа завершена")
        print("🔄 Переключаюсь в режим постоянного мониторинга...")
        
        # Запускаем бесконечный цикл мониторинга
        await continuous_monitoring_loop(client, reactions_history)
        
    except asyncio.CancelledError:
        print("\n⚠️ Получен сигнал отмены, завершаю работу...")
    except KeyboardInterrupt:
        print("\n⚠️ Получено прерывание от пользователя (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Безопасное завершение
        if client and client.is_connected():
            try:
                await update_online_status(client, False)
                await client.disconnect()
            except Exception:
                pass
        print(f"\n👋 Полное завершение работы - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
# Устанавливаем статус онлайн
# await client(UpdateStatusRequest(offline=False))
# print("📱 Статус: онлайн 🟢")
# print("\n✅ Основная работа завершена")
# print("🔄 Переключаюсь в режим постоянного мониторинга...")

# # Запускаем мониторинг
# async def run_monitoring():
#     await continuous_monitoring_mode(client, channel_username, discussion_chat, history, reactions_history, private_chat_history)

# asyncio.create_task(run_monitoring())

# Для запуска используйте:
if __name__ == '__main__':
    try:
        asyncio.run(enhanced_main())
    except KeyboardInterrupt:
        print("\n👋 Программа остановлена пользователем")
