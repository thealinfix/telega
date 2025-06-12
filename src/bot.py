import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from .config import TELEGRAM_TOKEN
from .handlers.news_handler import register_news
from .handlers.moderation_handler import register_moderation
from .handlers.hype_handlers import register_hype

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def echo(update, context):
    """Повторяет всё, что прислали боту"""
    await update.message.reply_text(update.message.text)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Регистрируем хендлер меню из hype_handlers (включает /start)
    register_hype(app)
    # Регистрируем прочие
    register_news(app)
    register_moderation(app)
    # Эхо на всё остальное
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logging.info("Bot is starting polling…")
    app.run_polling()

if __name__ == '__main__':
    main()
