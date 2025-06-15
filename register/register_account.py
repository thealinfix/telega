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

# ==== КОНФИГ ====
api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'
session_file = 'sessions/172143346_telethon.session'
proxy = ('socks5', '217.29.62.212', 12049, True, 'ZcqNj3', 'KNqLM6')

openai_client = openai.OpenAI(
    api_key="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"
)

# Define the OpenAI GPT model to use
GPT_MODEL = "gpt-3.5-turbo"

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
    "private_message_reply_chance": 0.3,      # 30% шанс ответить на личное сообщение
    "max_private_replies_per_day": 5,         # Максимум ответов в личке за день
    "private_reply_delay": (60, 300),         # Задержка перед ответом в личке (1-5 минут)
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
    "durov", "telegram", "tginfo", "tginforu", "markettwits",
    "breakingmash", "meduzalive", "rian_ru", "rt_russian"
]

# Настройки реакций (из предыдущей версии)
REACTIONS_CONFIG = {
    "channel_post_reaction_chance": 1.0,
    "comment_reaction_chance": 0.3,
    "max_reactions_per_hour": 20,
    "min_time_between_reactions": 20,
    "react_to_replies_chance": 0.9,
    "reaction_delay": (5, 45),
    "max_reactions_per_session": 5
}

REPLY_CONFIG = {
    "reply_to_interesting_comment": 0.15,
    "reply_if_mentioned_brand": 0.4,
    "reply_if_question": 0.6,
    "reply_if_strong_emotion": 0.3,
    "max_replies_per_post": 2,
    "min_time_between_replies": 180,
    "reply_delay": (30, 120)
}

# ... (остальные константы из предыдущей версии) ...

SPAM_PROTECTION = {
    "max_comments_per_day": 10,
    "min_time_between_comments": 120
}

def load_history():
    """Загружает историю комментариев"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return create_empty_history()
    return create_empty_history()

def create_empty_history():
    """Создает пустую историю комментариев"""
    return {
        "posts_commented": {},
        "all_comments": [],
        "daily_count": {},
        "last_styles": []
    }

def save_history(history):
    """Сохраняет историю комментариев"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_reactions_history():
    """Загружает историю реакций"""
    if os.path.exists(REACTIONS_HISTORY_FILE):
        try:
            with open(REACTIONS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return create_empty_reactions_history()
    return create_empty_reactions_history()

def create_empty_reactions_history():
    """Создает пустую историю реакций"""
    return {
        "session_reactions_count": 0
    }

def save_reactions_history(reactions_history):
    """Сохраняет историю реакций"""
    with open(REACTIONS_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(reactions_history, f, ensure_ascii=False, indent=2)

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
        messages = await client.get_messages(channel, limit=limit)
        if messages:
            # Отмечаем как прочитанные
            await client(ReadHistoryRequest(
                peer=channel,
                max_id=messages[0].id
            ))
            print(f"✅ Прочитано {len(messages)} сообщений в @{channel}")
            
            # Случайная задержка между чтением
            delay = random.uniform(*ANTIDETECT_CONFIG["read_messages_delay"])
            await asyncio.sleep(delay)
    except Exception as e:
        print(f"❌ Ошибка чтения канала {channel}: {e}")

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
    if now.weekday() >= 5:
        if random.random() > ANTIDETECT_CONFIG["weekend_activity_reduction"]:
            print("🏖 Выходной день, пропускаю активность")
            return False
    
    return True

async def handle_private_message(client, message, private_history):
    """Обрабатывает личные сообщения"""
    user_id = message.from_id.user_id if hasattr(message.from_id, 'user_id') else message.from_id
    
    # Проверяем, не спам ли это
    if any(keyword in message.text.lower() for keyword in ANTIDETECT_CONFIG["ignore_spam_keywords"]):
        print(f"🚫 Игнорирую спам от {user_id}")
        if user_id not in private_history["ignored_users"]:
            private_history["ignored_users"].append(user_id)
            save_private_chat_history(private_history)
        return
    
    # Проверяем лимиты
    today = datetime.now().strftime("%Y-%m-%d")
    daily_count = private_history["daily_replies"].get(today, 0)
    
    if daily_count >= ANTIDETECT_CONFIG["max_private_replies_per_day"]:
        print(f"⚠️ Достигнут дневной лимит ответов в личке ({daily_count})")
        return
    
    # Проверяем, отвечали ли недавно этому пользователю
    user_replies = private_history["replied_to"].get(str(user_id), [])
    if user_replies:
        last_reply = datetime.fromisoformat(user_replies[-1])
        if (datetime.now() - last_reply).total_seconds() < 3600:  # Не чаще раза в час
            print(f"⏰ Недавно отвечал пользователю {user_id}")
            return
    
    # Решаем, отвечать ли
    if random.random() < ANTIDETECT_CONFIG["private_message_reply_chance"]:
        # Задержка перед ответом
        delay = random.randint(*ANTIDETECT_CONFIG["private_reply_delay"])
        print(f"💬 Отвечу на личное сообщение через {delay} сек...")
        await asyncio.sleep(delay)
        
        # Имитируем набор текста
        await simulate_typing(client, message.from_id)
        
        # Генерируем ответ
        reply = await generate_private_reply(message.text)
        
        try:
            await client.send_message(message.from_id, reply)
            
            # Обновляем историю
            if str(user_id) not in private_history["replied_to"]:
                private_history["replied_to"][str(user_id)] = []
            private_history["replied_to"][str(user_id)].append(datetime.now().isoformat())
            
            private_history["daily_replies"][today] = daily_count + 1
            private_history["last_reply_time"] = datetime.now().isoformat()
            save_private_chat_history(private_history)
            
            print(f"✅ Ответил в личку: {reply}")
            
        except Exception as e:
            print(f"❌ Ошибка отправки личного сообщения: {e}")

async def generate_private_reply(message_text):
    """Генерирует ответ на личное сообщение"""
    prompts = {
        "greeting": "Приветливо ответь на приветствие, но кратко.",
        "question": "Дай короткий дружелюбный ответ на вопрос.",
        "default": "Напиши короткий дружелюбный ответ."
    }
    
    # Определяем тип сообщения
    message_lower = message_text.lower()
    if any(word in message_lower for word in ["привет", "здравствуй", "добрый", "хай", "ку"]):
        prompt_type = "greeting"
    elif "?" in message_text:
        prompt_type = "question"
    else:
        prompt_type = "default"
    
    prompt = f"""Ты обычный пользователь Telegram. {prompts[prompt_type]}
Отвечай кратко (до 10 слов), дружелюбно, как обычный человек.
Можешь использовать эмодзи, но не перебарщивай.
НЕ представляйся, НЕ спрашивай "чем могу помочь".

Сообщение: {message_text}

Твой ответ:"""

    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Запасные ответы
        replies = [
            "привет! 👋",
            "как дела?",
            "норм)",
            "да, все ок",
            "пока не знаю",
            "может быть"
        ]
        return random.choice(replies)

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

async def monitor_private_messages(client):
    """Мониторит личные сообщения"""
    print("\n📨 Проверяю личные сообщения...")
    
    try:
        # Получаем непрочитанные диалоги
        dialogs = await client.get_dialogs(limit=10)
        
        for dialog in dialogs:
            await process_dialog_messages(client, dialog)
                
    except Exception as e:
        print(f"❌ Ошибка мониторинга личных сообщений: {e}")

async def process_dialog_messages(client, dialog):
    """Обрабатывает сообщения в одном диалоге"""
    if dialog.is_user and dialog.unread_count > 0:
        # Получаем последние сообщения
        messages = await client.get_messages(dialog.entity, limit=dialog.unread_count)
        
        for message in messages:
            if message.out:  # Пропускаем наши сообщения
                continue
            
            if message.text:  # Обрабатываем только текстовые
                await handle_private_message(client, message, load_private_chat_history())
        
        # Отмечаем как прочитанные
        await client.send_read_acknowledge(dialog.entity)

async def enhanced_main():
    """Основная функция с антидетект защитой"""
    print(f"\n🚀 Запуск бота с антидетект защитой - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
    await client.start()
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
        
    finally:
        # Обновляем статус офлайн
        await update_online_status(client, False)
        await client.disconnect()
        print(f"\n👋 Завершение сессии - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def get_last_channel_post(client, channel_username):
    """
    Получает последний пост из указанного канала.
    """
    try:
        messages = await client.get_messages(channel_username, limit=1)
        if messages:
            return messages[0]
        else:
            print(f"❌ Нет сообщений в канале @{channel_username}")
            return None
    except Exception as e:
        print(f"❌ Ошибка получения последнего поста: {e}")
        return None

async def main_bot_work(client, history, reactions_history):
    """Основная работа бота (из предыдущей версии)"""
    # Сбрасываем счетчик реакций за сессию
    reactions_history["session_reactions_count"] = 0
    save_reactions_history(reactions_history)
    
    # Получаем последний пост
    last_channel_post = await get_last_channel_post(client, channel_username)
    if not last_channel_post:
        return
    
    post_text = print_post_info(last_channel_post)
    if not post_text:
        post_text = "Пост без текста (только фото/медиа)"
    
    # Пауза перед реакцией (имитация просмотра)
    await asyncio.sleep(random.uniform(3, 10))
    
    # Ставим реакцию на пост в канале
    await process_channel_post_reaction(client, last_channel_post, reactions_history)
    
    # Обработка обсуждения и комментариев
    await handle_discussion_and_comments(client, last_channel_post, post_text, history, reactions_history)
    
    await client.disconnect()
    print(f"\n👋 Бот завершил работу - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def process_channel_post_reaction(client, post, reactions_history):
    """
    Ставит реакцию на пост в канале, если не превышен лимит.
    """
    if reactions_history.get("session_reactions_count", 0) >= REACTIONS_CONFIG["max_reactions_per_session"]:
        print("⚠️ Достигнут лимит реакций за сессию")
        return
    if random.random() > REACTIONS_CONFIG["channel_post_reaction_chance"]:
        print("⏩ Пропускаю реакцию на пост (по вероятности)")
        return
    try:
        emoji_list = ["👍", "🔥", "😂", "😍", "👏", "😮", "😢", "🤔"]
        emoji = random.choice(emoji_list)
        await client(SendReactionRequest(
            peer=post.peer_id,
            msg_id=post.id,
            reaction=[ReactionEmoji(emoticon=emoji)]
        ))
        reactions_history["session_reactions_count"] = reactions_history.get("session_reactions_count", 0) + 1
        save_reactions_history(reactions_history)
        print(f"❤️‍🔥 Поставил реакцию {emoji} на пост {post.id}")
        # Задержка после реакции
        await asyncio.sleep(random.uniform(*REACTIONS_CONFIG["reaction_delay"]))
    except Exception as e:
        print(f"❌ Ошибка при постановке реакции: {e}")

async def find_discussion_msg_id(client, last_channel_post, discussion_chat):
    """
    Находит ID сообщения обсуждения для поста.
    """
    try:
        # Получаем сообщения обсуждения (reply_to_msg_id совпадает с id поста)
        messages = await client.get_messages(discussion_chat, limit=100)
        for msg in messages:
            if getattr(msg, "reply_to_msg_id", None) == last_channel_post.id:
                return msg.id
        return None
    except Exception as e:
        print(f"❌ Ошибка поиска обсуждения: {e}")
        return None

async def process_comment_reactions_and_replies(client, discussion_chat, reactions_history, my_comment_id=None):
    """
    Обрабатывает реакции и ответы на комментарии в обсуждении.
    """
    try:
        # Получаем последние комментарии
        comments = await client.get_messages(discussion_chat, limit=30)
        for comment in comments:
            # Пропускаем свои комментарии, если указан my_comment_id
            if my_comment_id and comment.id == my_comment_id:
                continue
            # Пропускаем не текстовые сообщения
            if not comment.text:
                continue
            # Реакция на комментарий
            if random.random() < REACTIONS_CONFIG["comment_reaction_chance"]:
                emoji_list = ["👍", "😂", "🔥", "👏", "😍", "😮"]
                emoji = random.choice(emoji_list)
                try:
                    await client(SendReactionRequest(
                        peer=comment.peer_id,
                        msg_id=comment.id,
                        reaction=[ReactionEmoji(emoticon=emoji)]
                    ))
                    reactions_history["session_reactions_count"] = reactions_history.get("session_reactions_count", 0) + 1
                    save_reactions_history(reactions_history)
                    print(f"💬 Поставил реакцию {emoji} на комментарий {comment.id}")
                    await asyncio.sleep(random.uniform(*REACTIONS_CONFIG["reaction_delay"]))
                except Exception as e:
                    print(f"❌ Ошибка при реакции на комментарий: {e}")
            # Можно добавить логику для ответов на комментарии
    except Exception as e:
        print(f"❌ Ошибка обработки комментариев: {e}")

async def handle_discussion_and_comments(client, last_channel_post, post_text, history, reactions_history):
    """Обрабатывает обсуждение и комментарии к посту, снижая когнитивную сложность main"""
    discussion_msg_id = await find_discussion_msg_id(client, last_channel_post, discussion_chat)
    my_comment_id = None

    if not discussion_msg_id:
        print("❌ Не найдено обсуждение для поста.")
        # Все равно проверяем комментарии для реакций и ответов
        await process_comment_reactions_and_replies(client, discussion_chat, reactions_history)
        return

    if can_comment(last_channel_post.id, history):
        # Генерируем и отправляем комментарий к посту
        style = get_comment_style(history)
        wait_time = random.randint(10, 30)
        print(f"\n⏳ Жду {wait_time} секунд перед комментарием к посту...")
        await asyncio.sleep(wait_time)
        comment = await gpt_comment_with_context(post_text, style)
        sent_msg = await send_comment_and_get_id(client, discussion_chat, discussion_msg_id, comment, last_channel_post.id, history)
        if sent_msg:
            my_comment_id = sent_msg.id
    else:
        print("\n⛔ Комментирование поста заблокировано системой защиты")
    
    async def send_comment_and_get_id(client, discussion_chat, discussion_msg_id, comment, post_id, history):
        """
        Отправляет комментарий в обсуждение и возвращает объект отправленного сообщения.
        """
        try:
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

    # Обрабатываем реакции и ответы на другие комментарии
    await asyncio.sleep(random.randint(20, 60))
    await process_comment_reactions_and_replies(client, discussion_chat, reactions_history, my_comment_id)

def can_comment(post_id, history):
    """
    Проверяет, можно ли комментировать данный пост согласно настройкам защиты от спама.
    """
    now = datetime.now()
    post_key = str(post_id)
    # Проверка: не комментировали ли этот пост ранее
    if post_key in history.get("posts_commented", {}):
        return False
    # Проверка: не превышен ли лимит комментариев за день
    daily_count = history.get("daily_count", {})
    today = now.strftime("%Y-%m-%d")
    if daily_count.get(today, 0) >= SPAM_PROTECTION["max_comments_per_day"]:
        return False
    # Проверка: не слишком ли быстро комментируем
    if history.get("all_comments"):
        last_comment_time = datetime.fromisoformat(history["all_comments"][-1]["time"])
        if (now - last_comment_time).total_seconds() < SPAM_PROTECTION["min_time_between_comments"]:
            return False
    return True

def print_post_info(post):
    """Печатает информацию о посте и возвращает текст поста"""
    post_text = post.text or post.caption or ""
    print("\n====== ПОСЛЕДНИЙ ПОСТ ======")
    print(f"ID: {post.id}")
    print(f"Дата: {post.date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Текст: {post_text[:300]}")
    print("============================\n")
    return post_text

def get_comment_style(history):
    """
    Выбирает стиль комментария для поста.
    Можно доработать: например, избегать повторов последних стилей.
    """
    styles = ["positive", "neutral", "short_reaction", "question", "funny", "love", "cool"]
    # Можно добавить логику, чтобы не повторять последние стили
    last_styles = history.get("last_styles", [])
    available_styles = [s for s in styles if s not in last_styles[-2:]] if last_styles else styles
    style = random.choice(available_styles)
    # Обновляем историю последних стилей
    history.setdefault("last_styles", []).append(style)
    if len(history["last_styles"]) > 5:
        history["last_styles"] = history["last_styles"][-5:]
    return style

async def gpt_comment_with_context(post_text, style):
    """
    Генерирует комментарий к посту с учетом стиля и истории.
    """
    style_prompts = {
        "positive": "Напиши позитивный, дружелюбный комментарий к этому посту.",
        "neutral": "Напиши нейтральный, короткий комментарий к этому посту.",
        "short_reaction": "Напиши очень короткую реакцию (1-2 слова или эмодзи) на этот пост.",
        "question": "Задай короткий вопрос по теме поста.",
        "funny": "Напиши забавный, не слишком остроумный комментарий к этому посту.",
        "love": "Покажи одобрение или восхищение этим постом.",
        "cool": "Напиши комментарий в стиле 'круто', 'супер', 'огонь'."
    }
    prompt = f"""Ты обычный пользователь Telegram. {style_prompts.get(style, '')}
Пост: {post_text}

Комментарий:"""
    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=40,
            temperature=0.85,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Запасные варианты
        fallback_comments = [
            "Класс! 👍",
            "Интересно.",
            "Согласен!",
            "🔥🔥🔥",
            "Спасибо за пост!",
            "Забавно)",
            "Вау!"
        ]
        return random.choice(fallback_comments)

if __name__ == '__main__':
    asyncio.run(enhanced_main())