from telegram.ext import ApplicationBuilder
from config import TELEGRAM_TOKEN
from handlers.news_handler import register_news
from handlers.moderation_handler import register_moderation

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_news(app)
    register_moderation(app)
    app.run_polling()

if __name__ == '__main__':
    main()
