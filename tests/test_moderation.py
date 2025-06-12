import asyncio
from src.handlers import moderation_handler

class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.reply_called = False
        self.reply_arg = None
    async def reply_text(self, text):
        self.reply_called = True
        self.reply_arg = text

class DummyUpdate:
    def __init__(self, text):
        self.message = DummyMessage(text)

class DummyContext:
    pass

def test_moderate_warns_on_badword():
    update = DummyUpdate("This contains badword")
    asyncio.run(moderation_handler.moderate(update, DummyContext()))
    assert update.message.reply_called
    assert update.message.reply_arg == "Please follow the chat rules."

def test_moderate_no_action():
    update = DummyUpdate("All good")
    asyncio.run(moderation_handler.moderate(update, DummyContext()))
    assert not update.message.reply_called
