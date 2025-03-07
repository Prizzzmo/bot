
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import io

class Analytics:
    """Класс для сбора и анализа статистики пользования ботом"""
    
    def __init__(self, logger):
        self.logger = logger
        self.stats_file = "user_stats.json"
        self.user_stats = self._load_stats()
        
    def _load_stats(self):
        """Загружает статистику из файла"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"users": {}, "topics": {}, "daily_activity": {}}
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке статистики: {e}")
            return {"users": {}, "topics": {}, "daily_activity": {}}
            
    def _save_stats(self):
        """Сохраняет статистику в файл"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении статистики: {e}")
    
    def track_user_activity(self, user_id, user_name, activity_type):
        """Отслеживает активность пользователя"""
        today = datetime.now().strftime("%Y-%m-%d")
        user_id = str(user_id)
        
        # Инициализируем данные пользователя, если его еще нет
        if user_id not in self.user_stats["users"]:
            self.user_stats["users"][user_id] = {
                "name": user_name,
                "first_seen": today,
                "activities": {}
            }
            
        # Обновляем счетчик активности
        if activity_type not in self.user_stats["users"][user_id]["activities"]:
            self.user_stats["users"][user_id]["activities"][activity_type] = 0
        self.user_stats["users"][user_id]["activities"][activity_type] += 1
        
        # Обновляем ежедневную активность
        if today not in self.user_stats["daily_activity"]:
            self.user_stats["daily_activity"][today] = {}
        if activity_type not in self.user_stats["daily_activity"][today]:
            self.user_stats["daily_activity"][today][activity_type] = 0
        self.user_stats["daily_activity"][today][activity_type] += 1
        
        # Сохраняем статистику
        self._save_stats()
        
    def track_topic_interest(self, topic):
        """Отслеживает интерес к определенной теме"""
        if "topics" not in self.user_stats:
            self.user_stats["topics"] = {}
            
        if topic not in self.user_stats["topics"]:
            self.user_stats["topics"][topic] = 0
        self.user_stats["topics"][topic] += 1
        
        # Сохраняем статистику
        self._save_stats()
        
    def get_popular_topics(self, limit=10):
        """Возвращает самые популярные темы"""
        if "topics" not in self.user_stats:
            return []
            
        # Сортируем темы по популярности
        sorted_topics = sorted(
            self.user_stats["topics"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return sorted_topics[:limit]
        
    def get_active_users(self, limit=10):
        """Возвращает самых активных пользователей"""
        if not self.user_stats["users"]:
            return []
            
        user_activity = []
        for user_id, user_data in self.user_stats["users"].items():
            total_activity = sum(user_data["activities"].values())
            user_activity.append((user_id, user_data["name"], total_activity))
            
        # Сортируем пользователей по активности
        sorted_users = sorted(user_activity, key=lambda x: x[2], reverse=True)
        
        return sorted_users[:limit]
        
    def generate_activity_chart(self, days=30):
        """Генерирует график активности за последние N дней"""
        try:
            # Получаем даты в обратном порядке (от новых к старым)
            all_dates = sorted(self.user_stats["daily_activity"].keys(), reverse=True)
            dates_to_show = all_dates[:days]
            dates_to_show.reverse()  # Переворачиваем для правильного отображения на графике
            
            # Готовим данные для различных типов активности
            activity_data = {}
            for date in dates_to_show:
                if date in self.user_stats["daily_activity"]:
                    for activity, count in self.user_stats["daily_activity"][date].items():
                        if activity not in activity_data:
                            activity_data[activity] = []
                        activity_data[activity].append(count)
                else:
                    for activity in activity_data:
                        activity_data[activity].append(0)
            
            # Создаем график
            plt.figure(figsize=(12, 6))
            
            for activity, counts in activity_data.items():
                if len(counts) < len(dates_to_show):
                    # Добавляем нули в начало списка, если данных меньше чем дат
                    counts = [0] * (len(dates_to_show) - len(counts)) + counts
                plt.plot(dates_to_show, counts, label=activity)
                
            plt.title("Активность пользователей бота")
            plt.xlabel("Дата")
            plt.ylabel("Количество действий")
            plt.legend()
            plt.grid(True)
            plt.xticks(rotation=45)
            
            # Сохраняем график в байтовый поток
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            
            return buf
        except Exception as e:
            self.logger.error(f"Ошибка при создании графика активности: {e}")
            return None
