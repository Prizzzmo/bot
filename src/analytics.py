
"""Сервис для аналитики и статистики использования бота"""

import json
import os
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.interfaces import ILogger

class AnalyticsService:
    """
    Сервис для сбора, анализа и предоставления статистики использования бота.
    """
    
    def __init__(self, logger: ILogger, stats_file: str = 'analytics_data.json'):
        """
        Инициализация аналитического сервиса.
        
        Args:
            logger (ILogger): Логгер для записи информации
            stats_file (str): Путь к файлу для хранения статистики
        """
        self.logger = logger
        self.stats_file = stats_file
        self.lock = threading.RLock()  # Для потокобезопасности
        
        # Инициализируем структуру данных для статистики
        self.stats_data = {
            "total_users": 0,
            "total_requests": 0,
            "total_topics": 0,
            "total_tests": 0,
            "hourly_stats": {},
            "daily_stats": {},
            "monthly_stats": {},
            "popular_topics": {},
            "user_stats": {},
            "last_update": int(time.time())
        }
        
        # Загружаем статистику из файла
        self._load_stats()
        
        # Запускаем фоновое сохранение статистики
        self._start_auto_save()
        
        self.logger.info("Аналитический сервис инициализирован")
    
    def track_user_activity(self, user_id: int, activity_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Отслеживание активности пользователя.
        
        Args:
            user_id (int): ID пользователя
            activity_type (str): Тип активности ('message', 'command', 'topic', 'test', etc.)
            details (Dict[str, Any], optional): Дополнительные детали активности
        """
        with self.lock:
            current_time = int(time.time())
            current_datetime = datetime.now()
            
            # Форматируем временные периоды
            hour_key = current_datetime.strftime('%Y-%m-%d-%H')
            day_key = current_datetime.strftime('%Y-%m-%d')
            month_key = current_datetime.strftime('%Y-%m')
            
            # Обновляем общую статистику
            self.stats_data["total_requests"] += 1
            
            # Инициализируем статистику пользователя, если она не существует
            user_id_str = str(user_id)
            if user_id_str not in self.stats_data["user_stats"]:
                self.stats_data["user_stats"][user_id_str] = {
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "total_requests": 0,
                    "activities": {}
                }
                # Увеличиваем счетчик пользователей
                self.stats_data["total_users"] += 1
            
            # Обновляем статистику пользователя
            user_stats = self.stats_data["user_stats"][user_id_str]
            user_stats["last_seen"] = current_time
            user_stats["total_requests"] += 1
            
            # Обновляем статистику по типу активности
            if activity_type not in user_stats["activities"]:
                user_stats["activities"][activity_type] = 0
            user_stats["activities"][activity_type] += 1
            
            # Обновляем почасовую статистику
            if hour_key not in self.stats_data["hourly_stats"]:
                self.stats_data["hourly_stats"][hour_key] = {
                    "requests": 0,
                    "unique_users": set(),
                    "activities": {}
                }
            hourly_stats = self.stats_data["hourly_stats"][hour_key]
            hourly_stats["requests"] += 1
            hourly_stats["unique_users"].add(user_id_str)
            
            if activity_type not in hourly_stats["activities"]:
                hourly_stats["activities"][activity_type] = 0
            hourly_stats["activities"][activity_type] += 1
            
            # Обновляем ежедневную статистику
            if day_key not in self.stats_data["daily_stats"]:
                self.stats_data["daily_stats"][day_key] = {
                    "requests": 0,
                    "unique_users": set(),
                    "activities": {}
                }
            daily_stats = self.stats_data["daily_stats"][day_key]
            daily_stats["requests"] += 1
            daily_stats["unique_users"].add(user_id_str)
            
            if activity_type not in daily_stats["activities"]:
                daily_stats["activities"][activity_type] = 0
            daily_stats["activities"][activity_type] += 1
            
            # Обновляем ежемесячную статистику
            if month_key not in self.stats_data["monthly_stats"]:
                self.stats_data["monthly_stats"][month_key] = {
                    "requests": 0,
                    "unique_users": set(),
                    "activities": {}
                }
            monthly_stats = self.stats_data["monthly_stats"][month_key]
            monthly_stats["requests"] += 1
            monthly_stats["unique_users"].add(user_id_str)
            
            if activity_type not in monthly_stats["activities"]:
                monthly_stats["activities"][activity_type] = 0
            monthly_stats["activities"][activity_type] += 1
            
            # Обрабатываем детали активности
            if details:
                # Отслеживаем популярные темы
                if activity_type == "topic" and "topic_name" in details:
                    topic_name = details["topic_name"]
                    if "popular_topics" not in self.stats_data:
                        self.stats_data["popular_topics"] = {}
                    
                    if topic_name not in self.stats_data["popular_topics"]:
                        self.stats_data["popular_topics"][topic_name] = 0
                    
                    self.stats_data["popular_topics"][topic_name] += 1
                    self.stats_data["total_topics"] += 1
                
                # Отслеживаем тесты
                elif activity_type == "test" and "topic_name" in details:
                    self.stats_data["total_tests"] += 1
            
            # Обновляем время последнего обновления
            self.stats_data["last_update"] = current_time
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получение статистики пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Dict[str, Any]: Статистика пользователя
        """
        with self.lock:
            user_id_str = str(user_id)
            if user_id_str in self.stats_data["user_stats"]:
                stats = self.stats_data["user_stats"][user_id_str].copy()
                
                # Добавляем удобочитаемые даты
                if "first_seen" in stats:
                    stats["first_seen_readable"] = datetime.fromtimestamp(
                        stats["first_seen"]).strftime('%Y-%m-%d %H:%M:%S')
                
                if "last_seen" in stats:
                    stats["last_seen_readable"] = datetime.fromtimestamp(
                        stats["last_seen"]).strftime('%Y-%m-%d %H:%M:%S')
                
                return stats
            
            return {
                "error": "Пользователь не найден в статистике"
            }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Получение общей статистики использования бота.
        
        Returns:
            Dict[str, Any]: Общая статистика
        """
        with self.lock:
            # Создаем копию статистики для безопасности
            stats = {
                "total_users": self.stats_data["total_users"],
                "total_requests": self.stats_data["total_requests"],
                "total_topics": self.stats_data["total_topics"],
                "total_tests": self.stats_data["total_tests"],
                "active_users": {
                    "daily": self._count_active_users(1),
                    "weekly": self._count_active_users(7),
                    "monthly": self._count_active_users(30)
                },
                "popular_topics": self._get_top_items(self.stats_data.get("popular_topics", {}), 10),
                "daily_requests": self._get_daily_requests(7),  # За последние 7 дней
                "hourly_distribution": self._get_hourly_distribution()
            }
            
            return stats
    
    def get_period_stats(self, period_type: str, limit: int = 30) -> Dict[str, Any]:
        """
        Получение статистики за определенный период.
        
        Args:
            period_type (str): Тип периода ('hourly', 'daily', 'monthly')
            limit (int): Ограничение на количество периодов
            
        Returns:
            Dict[str, Any]: Статистика за указанный период
        """
        with self.lock:
            if period_type == "hourly":
                stats_data = self.stats_data["hourly_stats"]
            elif period_type == "daily":
                stats_data = self.stats_data["daily_stats"]
            elif period_type == "monthly":
                stats_data = self.stats_data["monthly_stats"]
            else:
                return {"error": f"Неизвестный тип периода: {period_type}"}
            
            # Сортируем периоды по убыванию даты
            sorted_periods = sorted(stats_data.keys(), reverse=True)[:limit]
            
            # Формируем результат
            result = {}
            for period in sorted_periods:
                period_stats = stats_data[period].copy()
                
                # Преобразуем множество уникальных пользователей в количество
                if "unique_users" in period_stats:
                    period_stats["unique_users_count"] = len(period_stats["unique_users"])
                    period_stats.pop("unique_users")
                
                result[period] = period_stats
            
            return result
    
    def _count_active_users(self, days: int) -> int:
        """
        Подсчет активных пользователей за последние N дней.
        
        Args:
            days (int): Количество дней
            
        Returns:
            int: Количество активных пользователей
        """
        current_time = int(time.time())
        active_threshold = current_time - (days * 24 * 60 * 60)
        
        active_count = 0
        for user_id, stats in self.stats_data["user_stats"].items():
            if stats.get("last_seen", 0) >= active_threshold:
                active_count += 1
        
        return active_count
    
    def _get_top_items(self, items_dict: Dict[str, int], limit: int) -> List[Dict[str, Any]]:
        """
        Получение списка самых популярных элементов.
        
        Args:
            items_dict (Dict[str, int]): Словарь элементов и их счетчиков
            limit (int): Ограничение на количество элементов
            
        Returns:
            List[Dict[str, Any]]: Список самых популярных элементов
        """
        # Сортируем элементы по убыванию счетчика
        sorted_items = sorted(items_dict.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Формируем результат
        return [{"name": item[0], "count": item[1]} for item in sorted_items]
    
    def _get_daily_requests(self, days: int) -> List[Dict[str, Any]]:
        """
        Получение статистики запросов по дням за последние N дней.
        
        Args:
            days (int): Количество дней
            
        Returns:
            List[Dict[str, Any]]: Статистика запросов по дням
        """
        result = []
        
        # Получаем последние N дней
        current_date = datetime.now().date()
        for i in range(days):
            date = current_date - timedelta(days=i)
            day_key = date.strftime('%Y-%m-%d')
            
            if day_key in self.stats_data["daily_stats"]:
                day_stats = self.stats_data["daily_stats"][day_key]
                result.append({
                    "date": day_key,
                    "requests": day_stats["requests"],
                    "unique_users": len(day_stats["unique_users"])
                })
            else:
                result.append({
                    "date": day_key,
                    "requests": 0,
                    "unique_users": 0
                })
        
        # Сортируем по возрастанию даты
        result.sort(key=lambda x: x["date"])
        
        return result
    
    def _get_hourly_distribution(self) -> List[Dict[str, Any]]:
        """
        Получение распределения запросов по часам суток.
        
        Returns:
            List[Dict[str, Any]]: Распределение запросов по часам
        """
        # Инициализируем счетчики для каждого часа
        hourly_counts = {hour: 0 for hour in range(24)}
        
        # Подсчитываем запросы по часам
        for period, stats in self.stats_data["hourly_stats"].items():
            try:
                # Извлекаем час из ключа периода
                hour = int(period.split('-')[-1])
                hourly_counts[hour] += stats["requests"]
            except (ValueError, IndexError):
                pass
        
        # Формируем результат
        result = []
        for hour in range(24):
            result.append({
                "hour": hour,
                "requests": hourly_counts[hour]
            })
        
        return result
    
    def _load_stats(self) -> None:
        """Загружает статистику из файла"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                    # Преобразуем списки уникальных пользователей обратно в множества
                    for period, stats in loaded_data.get("hourly_stats", {}).items():
                        if "unique_users" in stats and isinstance(stats["unique_users"], list):
                            stats["unique_users"] = set(stats["unique_users"])
                    
                    for period, stats in loaded_data.get("daily_stats", {}).items():
                        if "unique_users" in stats and isinstance(stats["unique_users"], list):
                            stats["unique_users"] = set(stats["unique_users"])
                    
                    for period, stats in loaded_data.get("monthly_stats", {}).items():
                        if "unique_users" in stats and isinstance(stats["unique_users"], list):
                            stats["unique_users"] = set(stats["unique_users"])
                    
                    self.stats_data = loaded_data
                    self.logger.info(f"Статистика загружена из файла. Всего пользователей: {self.stats_data['total_users']}")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке статистики: {e}")
    
    def _save_stats(self) -> None:
        """Сохраняет статистику в файл"""
        try:
            with self.lock:
                # Создаем копию статистики для сохранения
                stats_copy = self._prepare_stats_for_save()
                
                with open(self.stats_file, 'w', encoding='utf-8') as f:
                    json.dump(stats_copy, f, ensure_ascii=False, indent=2)
                
                self.logger.debug("Статистика сохранена в файл")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении статистики: {e}")
    
    def _prepare_stats_for_save(self) -> Dict[str, Any]:
        """
        Подготавливает статистику для сохранения в JSON.
        
        Returns:
            Dict[str, Any]: Подготовленная статистика
        """
        stats_copy = self.stats_data.copy()
        
        # Преобразуем множества уникальных пользователей в списки для сериализации
        if "hourly_stats" in stats_copy:
            for period, stats in stats_copy["hourly_stats"].items():
                if "unique_users" in stats and isinstance(stats["unique_users"], set):
                    stats["unique_users"] = list(stats["unique_users"])
        
        if "daily_stats" in stats_copy:
            for period, stats in stats_copy["daily_stats"].items():
                if "unique_users" in stats and isinstance(stats["unique_users"], set):
                    stats["unique_users"] = list(stats["unique_users"])
        
        if "monthly_stats" in stats_copy:
            for period, stats in stats_copy["monthly_stats"].items():
                if "unique_users" in stats and isinstance(stats["unique_users"], set):
                    stats["unique_users"] = list(stats["unique_users"])
        
        return stats_copy
    
    def _start_auto_save(self) -> None:
        """Запускает фоновый поток для автоматического сохранения статистики"""
        def auto_save_job():
            while True:
                time.sleep(300)  # Сохраняем каждые 5 минут
                try:
                    self._save_stats()
                except Exception as e:
                    self.logger.error(f"Ошибка в фоновом сохранении статистики: {e}")
        
        # Запускаем поток как демон, чтобы он автоматически завершался с основным потоком
        auto_save_thread = threading.Thread(target=auto_save_job, daemon=True)
        auto_save_thread.start()
