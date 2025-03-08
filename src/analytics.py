"""Сервис для сбора и анализа данных об использовании бота"""

from typing import Dict, Any, List
import json
import os
from datetime import datetime
from src.base_service import BaseService

class AnalyticsService(BaseService):
    """
    Сервис для сбора и анализа данных об использовании бота.
    Отслеживает активность пользователей, популярные темы и результаты тестирования.
    """

    def __init__(self, logger):
        """
        Инициализация сервиса аналитики.

        Args:
            logger: Логгер для записи информации
        """
        super().__init__(logger)
        self.data_file = 'analytics_data.json'
        self.user_data = {}
        self.load_data()
        self._logger.info("Сервис аналитики инициализирован")

    def _do_initialize(self) -> bool:
        """
        Инициализирует сервис аналитики

        Returns:
            bool: True если инициализация успешна
        """
        try:
            # Здесь можно добавить код инициализации, если необходимо
            return True
        except Exception as e:
            self._logger.log_error(e, "Ошибка при инициализации AnalyticsService")
            return False


    def load_data(self):
        """Загружает данные аналитики из файла"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.user_data = json.load(f)
                self._logger.info(f"Загружены данные аналитики для {len(self.user_data)} пользователей")
            else:
                self._logger.info("Файл аналитики не найден, создаем новый")
        except Exception as e:
            self._logger.log_error(e, "Ошибка при загрузке данных аналитики")

    def save_data(self):
        """Сохраняет данные аналитики в файл"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
            self._logger.info("Данные аналитики сохранены")
        except Exception as e:
            self._logger.log_error(e, "Ошибка при сохранении данных аналитики")

    def track_user_activity(self, user_id: int, activity_type: str, data: Dict[str, Any] = None):
        """
        Отслеживает активность пользователя.

        Args:
            user_id (int): ID пользователя
            activity_type (str): Тип активности (например, 'view_topic', 'complete_test')
            data (dict, optional): Дополнительные данные об активности
        """
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {
                "first_seen": datetime.now().isoformat(),
                "activities": [],
                "viewed_topics": [],
                "test_results": {},
                "interaction_count": 0
            }

        activity = {
            "type": activity_type,
            "timestamp": datetime.now().isoformat()
        }

        if data:
            activity["data"] = data

        self.user_data[str(user_id)]["activities"].append(activity)
        self.user_data[str(user_id)]["interaction_count"] += 1

        # Если это просмотр темы, добавляем в список просмотренных тем
        if activity_type == "view_topic" and data and "topic" in data:
            if data["topic"] not in self.user_data[str(user_id)]["viewed_topics"]:
                self.user_data[str(user_id)]["viewed_topics"].append(data["topic"])

        # Если это прохождение теста, сохраняем результат
        if activity_type == "complete_test" and data and "topic" in data and "score" in data:
            self.user_data[str(user_id)]["test_results"][data["topic"]] = data["score"]

        # Сохраняем данные после каждого пятого взаимодействия
        if self.user_data[str(user_id)]["interaction_count"] % 5 == 0:
            self.save_data()

    def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """
        Получает аналитические данные для пользователя.

        Args:
            user_id (int): ID пользователя

        Returns:
            dict: Аналитические данные пользователя
        """
        return self.user_data.get(str(user_id), {})

    def get_popular_topics(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получает список популярных тем.

        Args:
            limit (int): Максимальное количество тем в списке

        Returns:
            list: Список популярных тем с количеством просмотров
        """
        topic_counts = {}

        for user_data in self.user_data.values():
            for topic in user_data.get("viewed_topics", []):
                if topic in topic_counts:
                    topic_counts[topic] += 1
                else:
                    topic_counts[topic] = 1

        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

        return [{"topic": topic, "views": count} for topic, count in sorted_topics[:limit]]

    def get_average_test_scores(self) -> Dict[str, float]:
        """
        Получает средние результаты тестов по темам.

        Returns:
            dict: Словарь с темами и средними результатами
        """
        topic_scores = {}
        topic_counts = {}

        for user_data in self.user_data.values():
            for topic, score in user_data.get("test_results", {}).items():
                if topic in topic_scores:
                    topic_scores[topic] += score
                    topic_counts[topic] += 1
                else:
                    topic_scores[topic] = score
                    topic_counts[topic] = 1

        return {topic: topic_scores[topic] / topic_counts[topic] 
                for topic in topic_scores if topic_counts[topic] > 0}

    def generate_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Генерирует персонализированные рекомендации для пользователя.

        Args:
            user_id (int): ID пользователя

        Returns:
            list: Список рекомендаций
        """
        recommendations = []
        user_analytics = self.get_user_analytics(user_id)

        # 1. Рекомендации на основе низких результатов в тесте
        if "test_results" in user_analytics:
            for topic, score in user_analytics["test_results"].items():
                if score < 0.7:  # Если результат меньше 70%
                    recommendations.append({
                        "type": "review_topic",
                        "topic": topic,
                        "reason": "Низкий результат в тесте",
                        "priority": "high"
                    })

        return recommendations

    def get_daily_activity_stats(self, days_limit: int = 7) -> Dict[str, int]:
        """
        Получает статистику активности по дням.

        Args:
            days_limit (int): Количество последних дней для анализа

        Returns:
            dict: Словарь с датами и количеством активностей
        """
        daily_stats = {}

        for user_data in self.user_data.values():
            for activity in user_data.get("activities", []):
                try:
                    date = activity["timestamp"].split("T")[0]
                    if date in daily_stats:
                        daily_stats[date] += 1
                    else:
                        daily_stats[date] = 1
                except Exception:
                    continue

        # Сортируем по дате и ограничиваем количество дней
        sorted_dates = sorted(daily_stats.items(), reverse=True)[:days_limit]
        return dict(sorted(sorted_dates, key=lambda x: x[0]))