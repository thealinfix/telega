# Telegram Bot Refactored

Modular Telegram bot project.

## Quick Start

1. Activate environment and install dependencies:
   \`\`\`bash
   source env/bin/activate
   pip install -r requirements.txt
   \`\`\`
2. Create a \`.env\` file in the project root:
   \`\`\`dotenv
   TELEGRAM_TOKEN=your_telegram_token
   OPENAI_API_KEY=your_openai_key
   \`\`\`
3. Run the bot using the refactored modules:
   \`\`\`bash
   python3 -m src.bot
   \`\`\`

The original monolithic implementation is preserved at `legacy/hypebot.py`.
