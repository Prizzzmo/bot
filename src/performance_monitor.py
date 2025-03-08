
"""
Модуль для мониторинга производительности приложения.

Предоставляет системы для:
- Отслеживания времени выполнения операций
- Мониторинга использования памяти
- Отслеживания использования API и кэша
- Сбора и анализа метрик производительности
"""

import time
import os
import psutil
import threading
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import functools

from src.interfaces import ILogger
from src.base_service import BaseService

class PerformanceMetric:
    """Класс для хранения информации о метрике производительности"""
    
    def __init__(self, name: str, value: float, timestamp: Optional[float] = None):
        """
        Инициализация метрики производительности.
        
        Args:
            name (str): Имя метрики
            value (float): Значение метрики
            timestamp (float, optional): Временная метка (по умолчанию текущее время)
        """
        self.name = name
        self.value = value
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование метрики в словарь.
        
        Returns:
            Dict[str, Any]: Словарь с данными метрики
        """
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp
        }

class PerformanceMonitor(BaseService):
    """
    Сервис для мониторинга производительности приложения.
    
    Отслеживает:
    - Время выполнения операций
    - Использование памяти
    - Использование API и кэша
    - Время ответа бота
    """
    
    def __init__(self, logger: ILogger, metrics_file: str = 'performance_metrics.json'):
        """
        Инициализация монитора производительности.
        
        Args:
            logger (ILogger): Логгер для записи информации
            metrics_file (str): Путь к файлу для хранения метрик
        """
        super().__init__(logger)
        self.metrics_file = metrics_file
        self.metrics: List[PerformanceMetric] = []
        self.lock = threading.RLock()  # Для потокобезопасности
        self.process = psutil.Process(os.getpid())
        self._load_metrics()
        
        # Запускаем фоновый мониторинг использования памяти
        self._start_memory_monitoring()
    
    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.
        
        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            # Проверяем возможность записи в файл метрик
            self._save_metrics()
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при инициализации PerformanceMonitor: {e}")
            return False
    
    def track_time(self, name: str) -> Callable:
        """
        Декоратор для измерения времени выполнения функции.
        
        Args:
            name (str): Имя метрики
            
        Returns:
            Callable: Декоратор
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed_time = (time.time() - start_time) * 1000  # Переводим в миллисекунды
                self.record_metric(f"{name}_time", elapsed_time)
                return result
            return wrapper
        return decorator
    
    def record_metric(self, name: str, value: float) -> None:
        """
        Записывает метрику.
        
        Args:
            name (str): Имя метрики
            value (float): Значение метрики
        """
        with self.lock:
            metric = PerformanceMetric(name, value)
            self.metrics.append(metric)
            
            # Если накопилось больше 1000 метрик, сохраняем их
            if len(self.metrics) >= 1000:
                self._save_metrics()
    
    def get_metrics(self, name: Optional[str] = None, 
                   start_time: Optional[float] = None, 
                   end_time: Optional[float] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получает метрики по фильтрам.
        
        Args:
            name (str, optional): Имя метрики для фильтрации
            start_time (float, optional): Начальное время для фильтрации
            end_time (float, optional): Конечное время для фильтрации
            limit (int): Максимальное количество возвращаемых метрик
            
        Returns:
            List[Dict[str, Any]]: Список метрик в виде словарей
        """
        with self.lock:
            filtered_metrics = self.metrics
            
            # Применяем фильтры
            if name:
                filtered_metrics = [m for m in filtered_metrics if m.name == name]
            
            if start_time:
                filtered_metrics = [m for m in filtered_metrics if m.timestamp >= start_time]
            
            if end_time:
                filtered_metrics = [m for m in filtered_metrics if m.timestamp <= end_time]
            
            # Сортируем по времени (от новых к старым)
            filtered_metrics.sort(key=lambda m: m.timestamp, reverse=True)
            
            # Ограничиваем количество
            filtered_metrics = filtered_metrics[:limit]
            
            # Преобразуем в словари
            return [m.to_dict() for m in filtered_metrics]
    
    def get_summary_metrics(self, name: str) -> Dict[str, float]:
        """
        Получает статистику по метрике.
        
        Args:
            name (str): Имя метрики
            
        Returns:
            Dict[str, float]: Статистика (min, max, avg, count)
        """
        metrics = [m.value for m in self.metrics if m.name == name]
        
        if not metrics:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "count": 0
            }
        
        return {
            "min": min(metrics),
            "max": max(metrics),
            "avg": sum(metrics) / len(metrics),
            "count": len(metrics)
        }
    
    def measure_memory_usage(self) -> float:
        """
        Измеряет текущее использование памяти процессом.
        
        Returns:
            float: Использование памяти в МБ
        """
        # Получаем информацию о памяти в байтах и конвертируем в МБ
        memory_info = self.process.memory_info()
        memory_usage_mb = memory_info.rss / (1024 * 1024)
        
        # Записываем метрику
        self.record_metric("memory_usage_mb", memory_usage_mb)
        
        return memory_usage_mb
    
    def _start_memory_monitoring(self) -> None:
        """Запускает фоновый поток для мониторинга использования памяти"""
        def memory_monitor():
            while True:
                try:
                    # Измеряем использование памяти каждые 5 минут
                    self.measure_memory_usage()
                    time.sleep(300)  # 5 минут
                except Exception as e:
                    self._logger.warning(f"Ошибка в мониторинге памяти: {e}")
                    time.sleep(60)  # Подождем минуту перед следующей попыткой
        
        # Запускаем поток как демон
        thread = threading.Thread(target=memory_monitor, daemon=True)
        thread.start()
    
    def _save_metrics(self) -> None:
        """Сохраняет метрики в файл"""
        try:
            # Преобразуем метрики в список словарей
            metrics_data = [m.to_dict() for m in self.metrics]
            
            # Если файл существует, загружаем существующие метрики
            existing_metrics = []
            if os.path.exists(self.metrics_file) and os.path.getsize(self.metrics_file) > 0:
                try:
                    with open(self.metrics_file, 'r', encoding='utf-8') as f:
                        existing_metrics = json.load(f)
                except json.JSONDecodeError:
                    self._logger.warning(f"Ошибка чтения файла метрик {self.metrics_file}. Файл будет перезаписан.")
            
            # Объединяем существующие и новые метрики
            all_metrics = existing_metrics + metrics_data
            
            # Ограничиваем количество сохраняемых метрик (хранить не более 10000)
            if len(all_metrics) > 10000:
                all_metrics = all_metrics[-10000:]
            
            # Сохраняем в файл
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(all_metrics, f, ensure_ascii=False, indent=2)
            
            # Очищаем список метрик
            self.metrics = []
            
        except Exception as e:
            self._logger.error(f"Ошибка при сохранении метрик в файл: {e}")
    
    def _load_metrics(self) -> None:
        """Загружает метрики из файла"""
        try:
            if os.path.exists(self.metrics_file) and os.path.getsize(self.metrics_file) > 0:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)
                
                # Преобразуем данные в объекты метрик
                for data in metrics_data:
                    if "name" in data and "value" in data and "timestamp" in data:
                        metric = PerformanceMetric(
                            name=data["name"], 
                            value=data["value"], 
                            timestamp=data["timestamp"]
                        )
                        self.metrics.append(metric)
                
                self._logger.info(f"Загружено {len(self.metrics)} метрик из файла")
        except Exception as e:
            self._logger.error(f"Ошибка при загрузке метрик из файла: {e}")
            self.metrics = []
    
    def clear_metrics(self) -> int:
        """
        Очищает все метрики.
        
        Returns:
            int: Количество удаленных метрик
        """
        with self.lock:
            count = len(self.metrics)
            self.metrics = []
            
            # Очищаем файл
            try:
                with open(self.metrics_file, 'w', encoding='utf-8') as f:
                    f.write('[]')
            except Exception as e:
                self._logger.error(f"Ошибка при очистке файла метрик: {e}")
            
            return count

    def get_api_performance_stats(self) -> Dict[str, Any]:
        """
        Собирает статистику производительности API.
        
        Returns:
            Dict[str, Any]: Статистика производительности API
        """
        api_response_times = self.get_summary_metrics("api_call_time")
        return {
            "avg_response_time_ms": api_response_times["avg"],
            "max_response_time_ms": api_response_times["max"],
            "total_calls": api_response_times["count"]
        }

    def get_bot_performance_stats(self) -> Dict[str, Any]:
        """
        Собирает общую статистику производительности бота.
        
        Returns:
            Dict[str, Any]: Статистика производительности бота
        """
        # Собираем различные метрики
        api_stats = self.get_api_performance_stats()
        command_times = self.get_summary_metrics("command_processing_time")
        message_times = self.get_summary_metrics("message_processing_time")
        memory_usage = self.get_summary_metrics("memory_usage_mb")
        
        # Формируем общую статистику
        return {
            "api": api_stats,
            "commands": {
                "avg_time_ms": command_times["avg"],
                "max_time_ms": command_times["max"],
                "count": command_times["count"]
            },
            "messages": {
                "avg_time_ms": message_times["avg"],
                "max_time_ms": message_times["max"],
                "count": message_times["count"]
            },
            "memory": {
                "avg_usage_mb": memory_usage["avg"],
                "max_usage_mb": memory_usage["max"],
                "current_usage_mb": self.measure_memory_usage()
            }
        }
