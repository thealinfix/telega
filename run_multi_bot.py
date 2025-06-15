# run_multi_bot.py - Главный скрипт для запуска системы

import asyncio
import sys
from multi_bot_manager import MultiBotManager, start_multi_bot_system
import json

async def main_menu():
    """Главное меню управления ботами"""
    manager = MultiBotManager()
    
    while True:
        print("\n" + "="*50)
        print("🤖 СИСТЕМА УПРАВЛЕНИЯ МНОЖЕСТВЕННЫМИ БОТАМИ")
        print("="*50)
        print(f"Загружено ботов: {len(manager.bots)}")
        print("\n1. Показать всех ботов")
        print("2. Добавить нового бота")
        print("3. Запустить автоматическую ротацию")
        print("4. Запустить конкретного бота")
        print("5. Проверить статус ботов")
        print("6. Сбросить дневные лимиты")
        print("7. Настройки взаимодействия ботов")
        print("0. Выход")
        
        choice = input("\nВыберите действие: ")
        
        if choice == "1":
            show_all_bots(manager)
        elif choice == "2":
            await add_new_bot(manager)
        elif choice == "3":
            await start_auto_rotation(manager)
        elif choice == "4":
            await run_specific_bot(manager)
        elif choice == "5":
            check_bot_status(manager)
        elif choice == "6":
            await manager.reset_daily_limits()
        elif choice == "7":
            configure_bot_interactions(manager)
        elif choice == "0":
            print("👋 Выход из программы")
            break
        else:
            print("❌ Неверный выбор")

def show_all_bots(manager):
    """Показывает всех ботов"""
    print("\n📋 СПИСОК БОТОВ:")
    print("-" * 80)
    
    for i, bot in enumerate(manager.bots, 1):
        status_emoji = {
            "active": "🟢",
            "inactive": "⚫",
            "banned": "🔴",
            "flood_wait": "🟡"
        }.get(bot.status, "❓")
        
        print(f"{i}. {bot.name or 'Без имени'} ({bot.phone})")
        print(f"   Статус: {status_emoji} {bot.status}")
        print(f"   Роль: {bot.role}")
        print(f"   Действий сегодня: {bot.daily_actions}")
        if bot.last_active:
            print(f"   Последняя активность: {bot.last_active.strftime('%Y-%m-%d %H:%M')}")
        print()

async def add_new_bot(manager):
    """Добавляет нового бота"""
    print("\n➕ ДОБАВЛЕНИЕ НОВОГО БОТА")
    
    phone = input("Номер телефона (с кодом страны): ")
    api_id = int(input("API ID: "))
    api_hash = input("API Hash: ")
    session_file = f"sessions/{phone.replace('+', '')}.session"
    
    print("\nНастройка прокси (оставьте пустым для пропуска):")
    proxy_host = input("Proxy host: ")
    
    proxy = None
    if proxy_host:
        proxy_port = int(input("Proxy port: "))
        proxy_user = input("Proxy username: ")
        proxy_pass = input("Proxy password: ")
        proxy = ("socks5", proxy_host, proxy_port, True, proxy_user, proxy_pass)
    
    role = input("Роль бота (commenter/reactor/lurker/mixed) [mixed]: ") or "mixed"
    
    new_bot = {
        "phone": phone,
        "api_id": api_id,
        "api_hash": api_hash,
        "session_file": session_file,
        "proxy": proxy,
        "role": role,
        "name": "",
        "status": "inactive",
        "daily_actions": 0
    }
    
    # Добавляем в конфиг
    config_file = "bots_config.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {"bots": []}
    
    config["bots"].append(new_bot)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print("✅ Бот добавлен в конфигурацию")
    
    # Перезагружаем конфиг
    manager.load_config()

async def start_auto_rotation(manager):
    """Запускает автоматическую ротацию"""
    print("\n🔄 НАСТРОЙКА АВТОМАТИЧЕСКОЙ РОТАЦИИ")
    
    channel = input("Канал для мониторинга [@chinapack]: ") or "@chinapack"
    discussion = input("Чат обсуждения [@chipack_chat]: ") or "@chipack_chat"
    
    print(f"\n✅ Запуск ротации для {channel} / {discussion}")
    print("Нажмите Ctrl+C для остановки\n")
    
    try:
        await manager.rotate_bots(channel, discussion)
    except KeyboardInterrupt:
        print("\n⏹️ Ротация остановлена")

async def run_specific_bot(manager):
    """Запускает конкретного бота"""
    show_all_bots(manager)
    
    try:
        bot_num = int(input("\nВыберите номер бота: ")) - 1
        if 0 <= bot_num < len(manager.bots):
            bot = manager.bots[bot_num]
            
            duration = int(input("Длительность сессии (минуты) [30]: ") or "30") * 60
            channel = input("Канал [@chinapack]: ") or "@chinapack"
            discussion = input("Чат [@chipack_chat]: ") or "@chipack_chat"
            
            print(f"\n🚀 Запуск бота {bot.name or bot.phone}")
            
            client = await manager.connect_bot(bot)
            if client:
                await manager.run_bot_session(bot, client, channel, discussion, duration)
            else:
                print("❌ Не удалось подключить бота")
        else:
            print("❌ Неверный номер")
    except ValueError:
        print("❌ Введите число")

def check_bot_status(manager):
    """Проверяет статус всех ботов"""
    print("\n📊 СТАТУС БОТОВ:")
    print("-" * 50)
    
    active = sum(1 for b in manager.bots if b.status == "active")
    inactive = sum(1 for b in manager.bots if b.status == "inactive")
    banned = sum(1 for b in manager.bots if b.status == "banned")
    flood = sum(1 for b in manager.bots if b.status == "flood_wait")
    
    print(f"🟢 Активные: {active}")
    print(f"⚫ Неактивные: {inactive}")
    print(f"🔴 Забаненные: {banned}")
    print(f"🟡 Флуд-вейт: {flood}")
    print(f"\n📈 Всего действий сегодня: {sum(b.daily_actions for b in manager.bots)}")

def configure_bot_interactions(manager):
    """Настройка взаимодействий между ботами"""
    print("\n⚙️ НАСТРОЙКИ ВЗАИМОДЕЙСТВИЯ БОТОВ")
    
    config_file = "bots_config.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {}
    
    settings = config.get("interaction_settings", {
        "enable_bot_interactions": True,
        "interaction_chance": 0.3,
        "recognize_other_bots": True,
        "bot_conversation_depth": 3
    })
    
    print(f"\nТекущие настройки:")
    print(f"1. Взаимодействие между ботами: {'Включено' if settings['enable_bot_interactions'] else 'Выключено'}")
    print(f"2. Шанс взаимодействия: {settings['interaction_chance']*100}%")
    print(f"3. Распознавание своих ботов: {'Да' if settings['recognize_other_bots'] else 'Нет'}")
    print(f"4. Глубина диалогов: {settings['bot_conversation_depth']} сообщений")
    
    choice = input("\nИзменить настройки? (y/n): ")
    
    if choice.lower() == 'y':
        settings['enable_bot_interactions'] = input("Включить взаимодействия? (y/n): ").lower() == 'y'
        
        chance = input(f"Шанс взаимодействия (0-100) [{settings['interaction_chance']*100}]: ")
        if chance:
            settings['interaction_chance'] = float(chance) / 100
        
        settings['recognize_other_bots'] = input("Распознавать своих ботов? (y/n): ").lower() == 'y'
        
        depth = input(f"Глубина диалогов [{settings['bot_conversation_depth']}]: ")
        if depth:
            settings['bot_conversation_depth'] = int(depth)
        
        config['interaction_settings'] = settings
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print("✅ Настройки сохранены")

if __name__ == "__main__":
    print("🚀 Запуск системы управления ботами...")
    
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n👋 Программа остановлена")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()