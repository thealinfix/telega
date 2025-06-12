from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from ..state import load_state, save_state


state = load_state()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to HypeBot!")


def register_hype(app):
    app.add_handler(CommandHandler("start", start_command))

