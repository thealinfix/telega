#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict

from hypebot import config, state, handlers, tasks

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)


def main():
    """Основная функция запуска бота"""
    try:
        # Проверка конфигурации
        if not all([config.TELEGRAM_TOKEN, config.OPENAI_API_KEY]):
            logging.critical("Не заданы обязательные переменные окружения")
            exit(1)

        # Создание приложения с поддержкой JobQueue
        app = Application.builder().token(config.TELEGRAM_TOKEN).build()

        # Регистрация обработчиков команд
        app.add_handler(CommandHandler("start", handlers.start_command))
        app.add_handler(CommandHandler("thoughts", handlers.thoughts_command))
        app.add_handler(CommandHandler("skip", handlers.skip_command))
        app.add_handler(CommandHandler("cancel", handlers.cancel_command))
        app.add_handler(CommandHandler("reset_state", handlers.reset_state_command))

        # Регистрация обработчиков сообщений
        app.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))

        # Регистрация обработчика callback-кнопок
        app.add_handler(CallbackQueryHandler(handlers.on_callback))

        # Настройка периодической проверки (если JobQueue доступен)
        if app.job_queue:
            app.job_queue.run_repeating(
                tasks.check_releases_job,
                interval=config.CHECK_INTERVAL_SECONDS,
                first=30,
            )
            logging.info("✅ JobQueue настроен для периодических проверок")
        else:
            logging.warning("⚠️ JobQueue недоступен - автоматические проверки отключены")

        # Информация о запуске
        logging.info("=== HypeBot запущен ===")
        logging.info(f"Admin ID: {config.ADMIN_CHAT_ID if config.ADMIN_CHAT_ID else 'Не установлен'}")
        logging.info(f"Channel: {state.state.get('channel', config.TELEGRAM_CHANNEL)}")
        logging.info(f"Timezone: {state.state.get('timezone', config.DEFAULT_TIMEZONE)}")
        logging.info(f"Источников: {len(config.SOURCES)}")
        logging.info("Новые функции: настройки канала, временные зоны, улучшенные промпты")

        # Запуск бота
        try:
            app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        except Conflict:
            logging.critical("Бот уже запущен в другом процессе.")
            return
            
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
