<<<<<<< ours
"""Message moderation handlers."""
=======
\"\"\"Message moderation handlers.\"\"\"
>>>>>>> theirs

from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes

async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
<<<<<<< ours
    """Check messages for banned words and warn users."""
=======
    \"\"\"Check messages for banned words and warn users.\"\"\"
>>>>>>> theirs
    text = update.message.text.lower()
    if 'badword' in text:
        await update.message.reply_text("Please follow the chat rules.")

def register_moderation(app) -> None:
<<<<<<< ours
    """Register the moderation handler with the bot application."""
=======
    \"\"\"Register the moderation handler with the bot application.\"\"\"
>>>>>>> theirs
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, moderate)
    )
