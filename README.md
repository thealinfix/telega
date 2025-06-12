# Telegram Bot Refactored

Modular Telegram bot project.

## Quick Start

1. Activate environment and install dependencies:
   \`\`\`bash
   source env/bin/activate
   pip install -r requirements.txt
   \`\`\`
2. Create a \`.env\` file in the project root with the required variables:
   \`\`\`dotenv
   TELEGRAM_TOKEN=your_telegram_token      # token for your Telegram bot from BotFather
   OPENAI_API_KEY=your_openai_key          # API key used for OpenAI integrations
   TELEGRAM_CHAT_ID=@channelusername       # chat or channel where the bot should post messages
   ADMIN_CHAT_ID=123456789                 # Telegram user ID allowed to manage the bot
   STATE_FILE=state.json                   # path to the JSON file storing bot state
   DEFAULT_TIMEZONE=Europe/Moscow          # timezone used when none is set in state
   CHECK_INTERVAL_SECONDS=1800             # how often to check for scheduled posts
   \`\`\`
3. Run the bot:
   \`\`\`bash
   python3 -m src.bot
   \`\`\`

The original monolithic implementation is preserved at \`legacy/hypebot.py\`.

## Environment Variables

The bot uses these environment variables:

- \`TELEGRAM_TOKEN\` – token for your Telegram bot from BotFather.  
- \`OPENAI_API_KEY\` – API key used for OpenAI integrations.  
- \`TELEGRAM_CHAT_ID\` – chat or channel where the bot should post messages.  
- \`ADMIN_CHAT_ID\` – Telegram user ID allowed to manage the bot.  
- \`STATE_FILE\` – path to the JSON file storing bot state (default: \`state.json\`).  
- \`DEFAULT_TIMEZONE\` – timezone used when none is set in state (default: \`Europe/Moscow\`).  
- \`CHECK_INTERVAL_SECONDS\` – how often to check for scheduled posts (default: \`1800\`).  
