# test_single_bot.py - Простой тест одного бота

import asyncio
from telethon import TelegramClient

# Конфигурация вашего основного бота
api_id = 2040
api_hash = "b18441a1ff607e10a989891a5462e627"
session_file = "sessions/573181612574.session"
proxy = ("socks5", "217.29.62.212", 12049, True, "ZcqNj3", "KNqLM6")

async def test_bot():
    """Тестирует подключение бота"""
    print("🔍 Тестирование подключения бота...")
    
    client = TelegramClient(session_file, api_id, api_hash, proxy=proxy)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Бот не авторизован!")
            return
        
        # Получаем информацию
        me = await client.get_me()
        print(f"✅ Бот подключен успешно!")
        print(f"📱 Телефон: {me.phone}")
        print(f"👤 Имя: {me.first_name} {me.last_name or ''}")
        print(f"🆔 ID: {me.id}")
        print(f"💎 Premium: {'Да' if me.premium else 'Нет'}")
        
        # Проверяем канал
        try:
            channel = await client.get_entity("@chinapack")
            print(f"\n📢 Канал найден: {channel.title}")
            
            # Получаем последний пост
            messages = await client.get_messages(channel, limit=1)
            if messages:
                print(f"📝 Последний пост: ID {messages[0].id}")
                print(f"📅 Дата: {messages[0].date}")
        except Exception as e:
            print(f"⚠️ Не могу получить канал: {e}")
        
        await client.disconnect()
        print("\n✅ Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        try:
            await client.disconnect()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_bot())