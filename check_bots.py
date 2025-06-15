# check_bots.py - Скрипт для проверки ваших ботов и прокси

import asyncio
import json
import os
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError

async def check_proxy(proxy_config):
    """Проверяет работоспособность прокси"""
    print(f"\n🔍 Проверка прокси {proxy_config[1]}:{proxy_config[2]}...")
    
    # Создаем временную сессию для теста
    test_client = TelegramClient(
        'test_proxy.session',
        2040,  # Ваш API ID
        'b18441a1ff607e10a989891a5462e627',  # Ваш API Hash
        proxy=proxy_config
    )
    
    try:
        await test_client.connect()
        print(f"✅ Прокси подключен успешно!")
        
        # Проверяем IP
        result = await test_client.get_me()
        if result:
            print(f"✅ Прокси работает корректно")
        
        await test_client.disconnect()
        
        # Удаляем тестовую сессию
        if os.path.exists('test_proxy.session'):
            os.remove('test_proxy.session')
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка прокси: {e}")
        try:
            await test_client.disconnect()
        except:
            pass
        
        if os.path.exists('test_proxy.session'):
            os.remove('test_proxy.session')
            
        return False

async def check_bot_session(bot_config):
    """Проверяет сессию бота"""
    print(f"\n🤖 Проверка бота {bot_config['name']} ({bot_config['phone']})...")
    
    # Проверяем существование файла сессии
    if not os.path.exists(bot_config['session_file']):
        print(f"❌ Файл сессии не найден: {bot_config['session_file']}")
        
        # Проверяем альтернативные пути
        alt_paths = [
            f"sessions/{bot_config['phone'].replace('+', '')}.session",
            f"register/{bot_config['phone'].replace('+', '')}.session",
            bot_config['session_file'].replace('.telethon', '')
        ]
        
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                print(f"✅ Найден альтернативный файл: {alt_path}")
                bot_config['session_file'] = alt_path
                break
    
    try:
        client = TelegramClient(
            bot_config['session_file'],
            bot_config['api_id'],
            bot_config['api_hash'],
            proxy=tuple(bot_config['proxy']) if bot_config.get('proxy') else None
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"❌ Бот не авторизован (требуется вход)")
            await client.disconnect()
            return False
        
        # Получаем информацию о боте
        me = await client.get_me()
        print(f"✅ Сессия активна!")
        print(f"   ID: {me.id}")
        print(f"   Имя: {me.first_name} {me.last_name or ''}")
        print(f"   Username: @{me.username}" if me.username else "   Username: не установлен")
        print(f"   Premium: {'Да' if me.premium else 'Нет'}")
        
        await client.disconnect()
        return True
        
    except FloodWaitError as e:
        print(f"⚠️ Flood wait: {e.seconds} секунд")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def main():
    """Основная функция проверки"""
    print("=" * 60)
    print("🔧 ПРОВЕРКА БОТОВ И ПРОКСИ")
    print("=" * 60)
    
    # Загружаем конфигурацию
    if not os.path.exists('bots_config.json'):
        print("❌ Файл bots_config.json не найден!")
        print("Создайте его из примера выше.")
        return
    
    with open('bots_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    bots = config['bots']
    print(f"\n📋 Найдено ботов: {len(bots)}")
    
    # Проверяем уникальные прокси
    unique_proxies = {}
    for bot in bots:
        if bot.get('proxy'):
            proxy_key = f"{bot['proxy'][1]}:{bot['proxy'][2]}"
            if proxy_key not in unique_proxies:
                unique_proxies[proxy_key] = bot['proxy']
    
    print(f"\n🌐 ПРОВЕРКА ПРОКСИ ({len(unique_proxies)} уникальных)")
    print("-" * 60)
    
    working_proxies = []
    for proxy_key, proxy in unique_proxies.items():
        if await check_proxy(tuple(proxy)):
            working_proxies.append(proxy_key)
    
    print(f"\n✅ Рабочих прокси: {len(working_proxies)} из {len(unique_proxies)}")
    
    # Проверяем ботов
    print(f"\n🤖 ПРОВЕРКА БОТОВ")
    print("-" * 60)
    
    working_bots = []
    for bot in bots:
        if await check_bot_session(bot):
            working_bots.append(bot['name'])
    
    # Итоговая статистика
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 60)
    print(f"✅ Рабочих прокси: {len(working_proxies)} из {len(unique_proxies)}")
    print(f"✅ Активных ботов: {len(working_bots)} из {len(bots)}")
    
    if working_bots:
        print(f"\n🟢 Готовые к работе боты:")
        for bot_name in working_bots:
            print(f"   - {bot_name}")
    
    # Сохраняем обновленную конфигурацию
    with open('bots_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Конфигурация обновлена!")

if __name__ == "__main__":
    asyncio.run(main())