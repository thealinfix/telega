# multi_bot_manager.py - Исправленная версия

import asyncio
import random
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, UserIsBlockedError

@dataclass
class BotAccount:
    """Класс для хранения данных аккаунта бота"""
    phone: str
    api_id: int
    api_hash: str
    session_file: str
    proxy: Optional[tuple] = None
    name: str = ""
    status: str = "inactive"  # active, inactive, banned, flood_wait
    last_active: Optional[datetime] = None
    flood_wait_until: Optional[datetime] = None
    daily_actions: int = 0
    role: str = "commenter"  # commenter, reactor, lurker, mixed

class MultiBotManager:
    """Менеджер для управления несколькими ботами"""
    
    def __init__(self, config_file: str = "bots_config.json"):
        self.config_file = config_file
        self.bots: List[BotAccount] = []
        self.active_clients: Dict[str, TelegramClient] = {}
        self.bot_interactions = {}  # Для отслеживания взаимодействий между ботами
        self.load_config()
        
    def load_config(self):
        """Загружает конфигурацию ботов из файла"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for bot_data in config.get('bots', []):
                    # Преобразуем списки в кортежи для proxy
                    if bot_data.get('proxy'):
                        bot_data['proxy'] = tuple(bot_data['proxy'])
                    
                    # Создаем BotAccount без лишних полей
                    bot_fields = {
                        'phone': bot_data.get('phone'),
                        'api_id': bot_data.get('api_id'),
                        'api_hash': bot_data.get('api_hash'),
                        'session_file': bot_data.get('session_file'),
                        'proxy': bot_data.get('proxy'),
                        'name': bot_data.get('name', ''),
                        'status': bot_data.get('status', 'inactive'),
                        'role': bot_data.get('role', 'commenter')
                    }
                    
                    bot = BotAccount(**bot_fields)
                    self.bots.append(bot)
        else:
            # Создаем пример конфигурации
            self.create_example_config()
    
    def create_example_config(self):
        """Создает пример конфигурационного файла"""
        example_config = {
            "bots": [
                {
                    "phone": "+1234567890",
                    "api_id": 123456,
                    "api_hash": "your_api_hash_here",
                    "session_file": "sessions/bot1.session",
                    "proxy": ["socks5", "proxy.host", 1080, True, "username", "password"],
                    "name": "Bot1",
                    "role": "commenter"
                }
            ],
            "interaction_settings": {
                "enable_bot_interactions": True,
                "interaction_chance": 0.3,
                "recognize_other_bots": True,
                "bot_conversation_depth": 3
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(example_config, f, indent=4, ensure_ascii=False)
        print(f"✅ Создан пример конфигурации: {self.config_file}")
    
    def save_config(self):
        """Сохраняет текущую конфигурацию"""
        config = {
            "bots": [
                {
                    "phone": bot.phone,
                    "api_id": bot.api_id,
                    "api_hash": bot.api_hash,
                    "session_file": bot.session_file,
                    "proxy": list(bot.proxy) if bot.proxy else None,
                    "name": bot.name,
                    "role": bot.role,
                    "status": bot.status,
                    "last_active": bot.last_active.isoformat() if bot.last_active else None,
                    "daily_actions": bot.daily_actions
                }
                for bot in self.bots
            ]
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    async def connect_bot(self, bot: BotAccount) -> Optional[TelegramClient]:
        """Подключает бота"""
        try:
            client = TelegramClient(
                bot.session_file,
                bot.api_id,
                bot.api_hash,
                proxy=bot.proxy
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"❌ Бот {bot.name} не авторизован")
                return None
            
            bot.status = "active"
            bot.last_active = datetime.now()
            self.active_clients[bot.phone] = client
            
            # Получаем информацию о боте
            me = await client.get_me()
            bot.name = f"{me.first_name or ''} {me.last_name or ''}".strip()
            
            print(f"✅ Подключен бот: {bot.name} ({bot.phone})")
            return client
            
        except FloodWaitError as e:
            bot.status = "flood_wait"
            bot.flood_wait_until = datetime.now() + timedelta(seconds=e.seconds)
            print(f"⚠️ Бот {bot.name} в флуд-вейте на {e.seconds} секунд")
            return None
            
        except UserIsBlockedError:
            bot.status = "banned"
            print(f"❌ Бот {bot.name} заблокирован")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка подключения бота {bot.name}: {e}")
            return None
    
    async def get_available_bot(self, exclude_phones: List[str] = None) -> Optional[tuple]:
        """Получает доступного бота для работы"""
        exclude_phones = exclude_phones or []
        available_bots = []
        
        for bot in self.bots:
            # Пропускаем исключенные номера
            if bot.phone in exclude_phones:
                continue
            
            # Проверяем статус
            if bot.status == "banned":
                continue
            
            # Проверяем флуд-вейт
            if bot.status == "flood_wait" and bot.flood_wait_until:
                if datetime.now() < bot.flood_wait_until:
                    continue
                else:
                    bot.status = "inactive"
                    bot.flood_wait_until = None
            
            # Проверяем дневной лимит
            if bot.daily_actions >= 100:  # Настраиваемый лимит
                continue
            
            available_bots.append(bot)
        
        if not available_bots:
            return None
        
        # Выбираем бота с наименьшим количеством действий
        bot = min(available_bots, key=lambda b: b.daily_actions)
        
        # Подключаем если не подключен
        if bot.phone not in self.active_clients:
            client = await self.connect_bot(bot)
            if not client:
                return None
        else:
            client = self.active_clients[bot.phone]
        
        return bot, client
    
    async def rotate_bots(self, channel: str, discussion_chat: str):
        """Основной цикл ротации ботов"""
        print("🔄 Запуск системы ротации ботов...")
        
        while True:
            # Получаем доступного бота
            bot_data = await self.get_available_bot()
            if not bot_data:
                print("❌ Нет доступных ботов, ожидание...")
                await asyncio.sleep(300)  # Ждем 5 минут
                continue
            
            bot, client = bot_data
            print(f"\n🤖 Активирован бот: {bot.name}")
            
            try:
                # Запускаем сессию бота
                session_duration = random.randint(1800, 3600)  # 30-60 минут
                await self.run_bot_session(bot, client, channel, discussion_chat, session_duration)
                
            except Exception as e:
                print(f"❌ Ошибка в сессии бота {bot.name}: {e}")
            
            # Деактивируем бота
            bot.status = "inactive"
            bot.daily_actions += random.randint(10, 20)
            self.save_config()
            
            # Пауза между ботами
            pause = random.randint(300, 600)  # 5-10 минут
            print(f"⏸️ Пауза {pause//60} минут до следующего бота...")
            await asyncio.sleep(pause)
    
    async def run_bot_session(self, bot: BotAccount, client: TelegramClient, 
                             channel: str, discussion_chat: str, duration: int):
        """Запускает сессию конкретного бота"""
        # Импортируем вашу основную функцию
        try:
            from main import process_new_posts
        except ImportError:
            print("⚠️ Не могу импортировать process_new_posts из main.py")
            print("Используйте обычный запуск через main.py")
            return
        
        session_end = datetime.now() + timedelta(seconds=duration)
        print(f"⏱️ Сессия продлится {duration//60} минут")
        
        # Загружаем историю для этого бота
        bot_history_file = f"history_{bot.phone.replace('+', '')}.json"
        bot_reactions_file = f"reactions_{bot.phone.replace('+', '')}.json"
        
        while datetime.now() < session_end:
            try:
                # Обрабатываем посты
                await process_new_posts(
                    client, 
                    channel, 
                    discussion_chat,
                    history_file=bot_history_file,
                    reactions_file=bot_reactions_file
                )
                
                # Проверяем взаимодействия с другими ботами
                await self.check_bot_interactions(bot, client, discussion_chat)
                
                # Случайная пауза
                await asyncio.sleep(random.randint(60, 180))
                
            except Exception as e:
                print(f"⚠️ Ошибка в цикле бота: {e}")
                await asyncio.sleep(60)
    
    async def check_bot_interactions(self, current_bot: BotAccount, 
                                   client: TelegramClient, discussion_chat: str):
        """Проверяет и обрабатывает взаимодействия между ботами"""
        # Получаем список всех наших ботов
        our_bot_names = [b.name for b in self.bots if b.name and b.phone != current_bot.phone]
        
        try:
            # Получаем последние сообщения
            messages = await client.get_messages(discussion_chat, limit=20)
            
            for msg in messages:
                if not msg.sender or not msg.text:
                    continue
                
                sender_name = f"{msg.sender.first_name or ''} {msg.sender.last_name or ''}".strip()
                
                # Проверяем, это наш бот?
                if sender_name in our_bot_names:
                    # Определяем, стоит ли взаимодействовать
                    if random.random() < 0.3:  # 30% шанс взаимодействия
                        print(f"🤝 Обнаружен свой бот: {sender_name}")
                        
                        # Можем поставить реакцию или ответить
                        if random.random() < 0.7:  # 70% реакция, 30% ответ
                            # Ставим реакцию
                            emoji = random.choice(["👍", "❤️", "🔥", "😊"])
                            try:
                                from telethon.tl.functions.messages import SendReactionRequest
                                from telethon.tl.types import ReactionEmoji
                                
                                await client(SendReactionRequest(
                                    peer=discussion_chat,
                                    msg_id=msg.id,
                                    reaction=[ReactionEmoji(emoticon=emoji)]
                                ))
                                print(f"✅ Поставил реакцию {emoji} боту {sender_name}")
                            except:
                                pass
                        else:
                            # Отвечаем
                            response = random.choice([
                                "согласен", "точно", "+1", "тоже так думаю",
                                "интересно", "не знал", "спасибо за инфу"
                            ])
                            
                            await asyncio.sleep(random.randint(30, 90))
                            
                            try:
                                await client.send_message(
                                    discussion_chat,
                                    response,
                                    reply_to=msg.id
                                )
                                print(f"✅ Ответил боту {sender_name}: {response}")
                            except:
                                pass
        except Exception as e:
            print(f"⚠️ Ошибка при проверке взаимодействий: {e}")
    
    async def reset_daily_limits(self):
        """Сбрасывает дневные лимиты всех ботов (запускать раз в сутки)"""
        for bot in self.bots:
            bot.daily_actions = 0
        self.save_config()
        print("✅ Дневные лимиты сброшены")

# Функция для запуска системы
async def start_multi_bot_system():
    """Запускает систему с несколькими ботами"""
    manager = MultiBotManager()
    
    # Запускаем сброс лимитов каждые 24 часа
    async def daily_reset():
        while True:
            await asyncio.sleep(86400)  # 24 часа
            await manager.reset_daily_limits()
    
    # Запускаем параллельно
    await asyncio.gather(
        manager.rotate_bots("@chinapack", "@chipack_chat"),
        daily_reset()
    )

if __name__ == "__main__":
    asyncio.run(start_multi_bot_system())