<<<<<<< ours
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from .config import TELEGRAM_TOKEN
from .handlers.news_handler import register_news
from .handlers.moderation_handler import register_moderation

# 1. Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update, context):
    """Обрабатывает команду /start"""
    await update.message.reply_text("Бот запущен! Отправь мне что-нибудь — я отвечу эхо.")

async def echo(update, context):
    """Повторяет всё, что прислали боту"""
    await update.message.reply_text(update.message.text)
=======
from telegram.ext import ApplicationBuilder
from config import TELEGRAM_TOKEN
from handlers.news_handler import register_news
from handlers.moderation_handler import register_moderation
from handlers.hype_handlers import register_hype
>>>>>>> theirs

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Базовые хендлеры
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Ваши существующие обработчики
    register_news(app)
    register_moderation(app)
<<<<<<< ours

    logging.info("Bot is starting polling…")
=======
    register_hype(app)
>>>>>>> theirs
    app.run_polling()

if __name__ == '__main__':
    main()
