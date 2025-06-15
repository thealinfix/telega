# run_all_bots.py - Запуск всех ботов одновременно

import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor
import subprocess
import sys

def load_bots_config():
    """Загружает конфигурацию ботов"""
    with open('bots_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def run_bot_process(bot_index):
    """Запускает отдельный процесс для бота"""
    # Запускаем main.py с параметром номера бота
    subprocess.run([sys.executable, "main.py", "--bot", str(bot_index)])

async def run_all_bots_simultaneously():
    """Запускает всех ботов одновременно"""
    config = load_bots_config()
    bots = config['bots']
    
    print("=" * 60)
    print("🚀 ЗАПУСК ВСЕХ БОТОВ ОДНОВРЕМЕННО")
    print("=" * 60)
    print(f"📋 Найдено ботов: {len(bots)}")
    
    # Показываем список ботов
    for i, bot in enumerate(bots, 1):
        print(f"{i}. {bot['name']} ({bot['phone']})")
    
    print("\n⚙️ Настройки:")
    print(f"- Боты работают одновременно")
    print(f"- Каждый в своем процессе")
    print(f"- Автоматический перезапуск при ошибках")
    
    confirm = input("\nЗапустить всех ботов? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Отменено")
        return
    
    # Создаем отдельные процессы для каждого бота
    processes = []
    
    for i in range(len(bots)):
        print(f"\n🤖 Запуск бота #{i+1}: {bots[i]['name']}...")
        
        # Создаем отдельный Python скрипт для каждого бота
        bot_script = f"""
import asyncio
import sys
sys.path.append('.')

# Настройки бота {i+1}
BOT_INDEX = {i}

from main import *

# Загружаем конфигурацию
config = load_bots_config()
selected_bot = config['bots'][BOT_INDEX]

# Переопределяем глобальные переменные
api_id = selected_bot['api_id']
api_hash = selected_bot['api_hash']
session_file = selected_bot['session_file']
proxy = tuple(selected_bot['proxy']) if selected_bot.get('proxy') else None

print(f"\\n🤖 Бот #{BOT_INDEX+1} ({selected_bot['name']}) запущен")
print(f"📱 Сессия: {{session_file}}")
print(f"🌐 Прокси: {{proxy[1]}}:{{proxy[2]}}\" if proxy else \"Без прокси\")

# Запускаем бота
asyncio.run(enhanced_main())
"""
        
        # Сохраняем скрипт
        script_file = f"bot_{i+1}_runner.py"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(bot_script)
        
        # Запускаем процесс
        process = subprocess.Popen(
            [sys.executable, script_file],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        processes.append((process, bots[i]['name'], script_file))
        
        # Пауза между запусками
        await asyncio.sleep(5)
    
    print(f"\n✅ Запущено ботов: {len(processes)}")
    print("\n📊 Мониторинг:")
    print("Нажмите Ctrl+C для остановки всех ботов\n")
    
    try:
        # Мониторим процессы
        while True:
            await asyncio.sleep(30)
            
            # Проверяем статус процессов
            for i, (process, name, script_file) in enumerate(processes):
                if process.poll() is not None:
                    print(f"⚠️ Бот {name} остановился. Перезапуск...")
                    
                    # Перезапускаем
                    new_process = subprocess.Popen(
                        [sys.executable, script_file],
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                    )
                    processes[i] = (new_process, name, script_file)
                    
    except KeyboardInterrupt:
        print("\n⏹️ Остановка всех ботов...")
        
        # Останавливаем все процессы
        for process, name, script_file in processes:
            try:
                process.terminate()
                print(f"✅ Остановлен: {name}")
                
                # Удаляем временный файл
                if os.path.exists(script_file):
                    os.remove(script_file)
            except:
                pass
        
        print("\n👋 Все боты остановлены")

# Альтернативный вариант - все в одном процессе но разных потоках
async def run_all_bots_async():
    """Запускает всех ботов асинхронно в одном процессе"""
    config = load_bots_config()
    bots = config['bots']
    
    print("🚀 Запуск всех ботов асинхронно...")
    
    # Создаем задачи для каждого бота
    tasks = []
    
    for i, bot_config in enumerate(bots):
        task = asyncio.create_task(run_single_bot(i, bot_config))
        tasks.append(task)
        
        # Небольшая задержка между запусками
        await asyncio.sleep(3)
    
    # Ждем завершения всех задач
    await asyncio.gather(*tasks)

async def run_single_bot(index, bot_config):
    """Запускает одного бота"""
    from telethon import TelegramClient
    
    print(f"\n🤖 Запуск бота #{index+1}: {bot_config['name']}")
    
    client = TelegramClient(
        bot_config['session_file'],
        bot_config['api_id'],
        bot_config['api_hash'],
        proxy=tuple(bot_config['proxy']) if bot_config.get('proxy') else None
    )
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"❌ Бот {bot_config['name']} не авторизован")
            return
        
        me = await client.get_me()
        print(f"✅ Бот {me.first_name} подключен")
        
        # Импортируем функции из main.py
        from main import process_new_posts
        
        # Бесконечный цикл работы
        while True:
            try:
                # Уникальные файлы истории для каждого бота
                history_file = f"history_{bot_config['phone'].replace('+', '')}.json"
                reactions_file = f"reactions_{bot_config['phone'].replace('+', '')}.json"
                
                await process_new_posts(
                    client,
                    "@chinapack",
                    "@chipack_chat",
                    history_file=history_file,
                    reactions_file=reactions_file
                )
                
                # Случайная пауза 5-15 минут
                pause = random.randint(300, 900)
                print(f"💤 Бот {bot_config['name']} отдыхает {pause//60} минут")
                await asyncio.sleep(pause)
                
            except Exception as e:
                print(f"❌ Ошибка бота {bot_config['name']}: {e}")
                await asyncio.sleep(60)
                
    except Exception as e:
        print(f"❌ Критическая ошибка бота {bot_config['name']}: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    print("\n🤖 РЕЖИМЫ ЗАПУСКА БОТОВ:")
    print("1. В отдельных процессах (рекомендуется)")
    print("2. Асинхронно в одном процессе")
    print("3. Классическая ротация (по очереди)")
    
    choice = input("\nВыберите режим (1-3): ")
    
    if choice == "1":
        asyncio.run(run_all_bots_simultaneously())
    elif choice == "2":
        asyncio.run(run_all_bots_async())
    elif choice == "3":
        print("\nДля ротации используйте: python run_multi_bot.py")
    else:
        print("❌ Неверный выбор")