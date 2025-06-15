# smart_bot_coordinator.py - Координатор для умного распределения комментариев

import asyncio
import json
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import math

@dataclass
class PostActivity:
    """Отслеживание активности под постом"""
    post_id: int
    channel: str
    timestamp: datetime
    bots_commented: List[str] = None
    bots_reacted: List[str] = None
    total_comments: int = 0
    
    def __post_init__(self):
        if self.bots_commented is None:
            self.bots_commented = []
        if self.bots_reacted is None:
            self.bots_reacted = []

class SmartBotCoordinator:
    """Координатор для умного распределения активности ботов"""
    
    def __init__(self, config_file="bots_config.json", activity_file="bot_activity.json"):
        self.config_file = config_file
        self.activity_file = activity_file
        self.post_activities: Dict[int, PostActivity] = {}
        self.load_config()
        self.load_activity()
    
    def load_config(self):
        """Загружает конфигурацию"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.bots = self.config.get('bots', [])
    
    def load_activity(self):
        """Загружает историю активности"""
        if os.path.exists(self.activity_file):
            try:
                with open(self.activity_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Восстанавливаем объекты PostActivity
                    for post_id, activity_data in data.items():
                        self.post_activities[int(post_id)] = PostActivity(
                            post_id=activity_data['post_id'],
                            channel=activity_data['channel'],
                            timestamp=datetime.fromisoformat(activity_data['timestamp']),
                            bots_commented=activity_data.get('bots_commented', []),
                            bots_reacted=activity_data.get('bots_reacted', []),
                            total_comments=activity_data.get('total_comments', 0)
                        )
            except:
                self.post_activities = {}
    
    def save_activity(self):
        """Сохраняет историю активности"""
        data = {}
        for post_id, activity in self.post_activities.items():
            data[str(post_id)] = {
                'post_id': activity.post_id,
                'channel': activity.channel,
                'timestamp': activity.timestamp.isoformat(),
                'bots_commented': activity.bots_commented,
                'bots_reacted': activity.bots_reacted,
                'total_comments': activity.total_comments
            }
        
        with open(self.activity_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def calculate_comment_probability(self, post_id: int, bot_phone: str) -> float:
        """Рассчитывает вероятность комментирования для бота"""
        
        # Базовые вероятности в зависимости от количества ботов
        base_probabilities = {
            1: 1.0,      # 1 бот = 100% должен комментировать
            2: 0.7,      # 2 бота = 70% каждый
            3: 0.5,      # 3 бота = 50% каждый
            4: 0.4,      # 4 бота = 40% каждый
            5: 0.35,     # 5 ботов = 35% каждый
            10: 0.25,    # 10 ботов = 25% каждый
            20: 0.15,    # 20 ботов = 15% каждый
        }
        
        active_bots_count = len([b for b in self.bots if b.get('status') != 'banned'])
        
        # Интерполяция для промежуточных значений
        if active_bots_count in base_probabilities:
            base_prob = base_probabilities[active_bots_count]
        else:
            # Логарифмическая зависимость для больших количеств
            base_prob = max(0.1, 1.0 / math.log(active_bots_count + 1))
        
        # Проверяем активность под постом
        activity = self.post_activities.get(post_id)
        if activity:
            # Если уже есть комментарии от наших ботов
            if activity.bots_commented:
                # Уменьшаем вероятность с каждым комментарием
                reduction_factor = 0.7 ** len(activity.bots_commented)
                base_prob *= reduction_factor
                
                # Но гарантируем минимум один комментарий
                if len(activity.bots_commented) == 0 and active_bots_count > 0:
                    base_prob = max(base_prob, 0.9)
        else:
            # Новый пост - гарантируем хотя бы один комментарий
            if active_bots_count == 1:
                base_prob = 1.0
            else:
                base_prob = max(base_prob, 0.8)
        
        # Модификаторы на основе роли бота
        bot_config = next((b for b in self.bots if b['phone'] == bot_phone), None)
        if bot_config:
            role = bot_config.get('role', 'mixed')
            role_modifiers = {
                'commenter': 1.3,    # +30% для комментаторов
                'reactor': 0.5,      # -50% для тех кто больше реагирует
                'lurker': 0.2,       # -80% для наблюдателей
                'mixed': 1.0         # без изменений
            }
            base_prob *= role_modifiers.get(role, 1.0)
        
        # Временной фактор - снижаем активность для старых постов
        if activity and activity.timestamp:
            hours_passed = (datetime.now() - activity.timestamp).total_seconds() / 3600
            if hours_passed > 2:
                base_prob *= 0.5  # -50% для постов старше 2 часов
            if hours_passed > 6:
                base_prob *= 0.5  # еще -50% для постов старше 6 часов
        
        return min(1.0, max(0.05, base_prob))  # От 5% до 100%
    
    async def should_bot_comment(self, post_id: int, bot_phone: str, force_at_least_one: bool = True) -> bool:
        """Решает, должен ли бот комментировать пост"""
        
        # Получаем или создаем активность для поста
        if post_id not in self.post_activities:
            self.post_activities[post_id] = PostActivity(
                post_id=post_id,
                channel="@chinapack",
                timestamp=datetime.now()
            )
        
        activity = self.post_activities[post_id]
        
        # Если бот уже комментировал - не комментируем повторно
        if bot_phone in activity.bots_commented:
            print(f"🚫 Бот {bot_phone} уже комментировал пост {post_id}")
            return False
        
        # Рассчитываем вероятность
        probability = self.calculate_comment_probability(post_id, bot_phone)
        
        # Если нужно гарантировать хотя бы один комментарий
        if force_at_least_one and not activity.bots_commented:
            # Это первый бот, проверяющий пост
            active_bots = [b for b in self.bots if b.get('status') != 'banned']
            if bot_phone == active_bots[0]['phone']:
                # Первый активный бот должен прокомментировать
                probability = 1.0
        
        # Принимаем решение
        should_comment = random.random() < probability
        
        print(f"🎲 Бот {bot_phone}: вероятность {probability:.1%}, решение: {'ДА' if should_comment else 'НЕТ'}")
        
        if should_comment:
            # Записываем решение
            activity.bots_commented.append(bot_phone)
            activity.total_comments += 1
            self.save_activity()
        
        return should_comment
    
    async def coordinate_post_activity(self, post_id: int, channel: str = "@chinapack") -> Dict[str, bool]:
        """Координирует активность всех ботов для поста"""
        
        print(f"\n📊 Координация активности для поста {post_id}")
        print(f"🤖 Активных ботов: {len([b for b in self.bots if b.get('status') != 'banned'])}")
        
        decisions = {}
        
        # Перемешиваем ботов для случайного порядка
        active_bots = [b for b in self.bots if b.get('status') != 'banned']
        random.shuffle(active_bots)
        
        # Проверяем каждого бота
        for i, bot in enumerate(active_bots):
            # Небольшая задержка между решениями
            if i > 0:
                await asyncio.sleep(random.uniform(0.5, 2))
            
            should_comment = await self.should_bot_comment(
                post_id, 
                bot['phone'],
                force_at_least_one=True
            )
            
            decisions[bot['phone']] = should_comment
        
        # Статистика
        commenters = [phone for phone, should in decisions.items() if should]
        print(f"\n📈 Итого будут комментировать: {len(commenters)} из {len(active_bots)} ботов")
        
        return decisions
    
    def get_activity_stats(self) -> Dict:
        """Получает статистику активности"""
        stats = {
            'total_posts': len(self.post_activities),
            'posts_last_hour': 0,
            'posts_last_24h': 0,
            'total_comments': sum(a.total_comments for a in self.post_activities.values()),
            'bot_activity': {}
        }
        
        now = datetime.now()
        
        for activity in self.post_activities.values():
            hours_passed = (now - activity.timestamp).total_seconds() / 3600
            
            if hours_passed <= 1:
                stats['posts_last_hour'] += 1
            if hours_passed <= 24:
                stats['posts_last_24h'] += 1
            
            # Статистика по ботам
            for bot_phone in activity.bots_commented:
                if bot_phone not in stats['bot_activity']:
                    stats['bot_activity'][bot_phone] = {
                        'comments': 0,
                        'reactions': 0
                    }
                stats['bot_activity'][bot_phone]['comments'] += 1
        
        return stats

# Функция для интеграции с main.py
async def check_should_comment(post_id: int, bot_phone: str) -> bool:
    """Проверяет, должен ли бот комментировать (для использования в main.py)"""
    coordinator = SmartBotCoordinator()
    return await coordinator.should_bot_comment(post_id, bot_phone)

# Модифицированная функция для main.py
def should_comment_smart(post_id: int, bot_phone: str, history: Dict) -> bool:
    """Умная проверка с учетом других ботов (синхронная версия)"""
    
    # Загружаем координатор
    coordinator = SmartBotCoordinator()
    
    # Быстрая проверка без async
    probability = coordinator.calculate_comment_probability(post_id, bot_phone)
    
    # Проверяем историю активности
    activity = coordinator.post_activities.get(post_id)
    
    # Если никто еще не комментировал и это первый бот
    if not activity or not activity.bots_commented:
        active_bots = [b for b in coordinator.bots if b.get('status') != 'banned']
        if active_bots and bot_phone == active_bots[0]['phone']:
            return True  # Первый бот должен прокомментировать
    
    # Иначе - случайное решение
    return random.random() < probability

# Пример использования в main.py
"""
# В функции handle_discussion_and_comments добавьте:

# Импортируем умную проверку
from smart_bot_coordinator import should_comment_smart

# Получаем телефон текущего бота
me = await client.get_me()
bot_phone = me.phone

# Вместо обычной проверки can_comment используем:
if should_comment_smart(last_channel_post.id, bot_phone, history):
    # Комментируем
    pass
else:
    print("🎲 Решено не комментировать этот пост")
"""

if __name__ == "__main__":
    # Тест координатора
    async def test():
        coordinator = SmartBotCoordinator()
        
        # Тестируем для поста
        post_id = 12345
        decisions = await coordinator.coordinate_post_activity(post_id)
        
        print("\n📊 Решения по комментированию:")
        for phone, should_comment in decisions.items():
            print(f"  {phone}: {'✅ Да' if should_comment else '❌ Нет'}")
        
        # Статистика
        stats = coordinator.get_activity_stats()
        print(f"\n📈 Статистика:")
        print(f"  Всего постов: {stats['total_posts']}")
        print(f"  Комментариев: {stats['total_comments']}")
    
    asyncio.run(test())