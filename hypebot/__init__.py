"""
HypeBot - бот для мониторинга и публикации новостей о кроссовках
"""

__version__ = "2.0.0"

# Импортируем основные компоненты
from . import config
from . import state
from . import handlers
from . import tasks
from . import utils
from . import fetcher
from . import messaging
from . import openai_utils

# Экспортируем для удобства
__all__ = [
    'config',
    'state', 
    'handlers',
    'tasks',
    'utils',
    'fetcher',
    'messaging',
    'openai_utils'
]
