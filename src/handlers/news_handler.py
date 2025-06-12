<<<<<<< ours
"""News related command handlers."""
=======
\"\"\"News related command handlers.\"\"\"
>>>>>>> theirs

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from ..utils.parser import parse_news

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
<<<<<<< ours
    """Send the latest news items to the chat."""
=======
    \"\"\"Send the latest news items to the chat.\"\"\"
>>>>>>> theirs
    news_list = parse_news()
    for item in news_list:
        await update.message.reply_text(
            f"*{item.title}*\n{item.link}",
            parse_mode='Markdown'
        )

def register_news(app) -> None:
<<<<<<< ours
    """Register the news command with the bot application."""
=======
    \"\"\"Register the news command with the bot application.\"\"\"
>>>>>>> theirs
    app.add_handler(CommandHandler('news', news_command))
