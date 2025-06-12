"""Message moderation handlers."""

from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes

async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check messages for banned words and warn users."""
    text = update.message.text.lower()
    if 'badword' in text:
        await update.message.reply_text("Please follow the chat rules.")

def register_moderation(app) -> None:
    """Register the moderation handler with the bot application."""
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, moderate)
    )
