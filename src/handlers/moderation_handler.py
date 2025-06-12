from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes

async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if 'badword' in text:
        await update.message.reply_text("Please follow the chat rules.")

def register_moderation(app):
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, moderate)
    )
