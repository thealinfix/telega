from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from ..utils.parser import parse_news

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    news_list = parse_news()
    for item in news_list:
        await update.message.reply_text(
            f"*{item.title}*\n{item.link}",
            parse_mode='Markdown'
        )

def register_news(app):
    app.add_handler(CommandHandler('news', news_command))
