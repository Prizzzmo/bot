
"""Модуль для кэширования API запросов"""

import json
import os
import time
from typing import Dict, Any, Optional, List
import threading

from src.interfaces import ICache, ILogger

class APICache(ICache):
    """
    Имплементация интерфейса кэширования для API запросов.
    Поддерживает персистентное хранение и управление временем жизни кэша.
    """
    
    def __init__(self, logger: ILogger, max_size: int = 1000, cache_file: str = 'api_cache.json'):
        """
        Инициализация системы кэширования.
        
        Args:
            logger (ILogger): Логгер для записи информации о работе кэша
            max_size (int): Максимальный размер кэша
            cache_file (str): Путь к файлу для персистентного хранения кэша
        """
        self.logger = logger
        self.max_size = max_size
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()  # Для потокобезопасности
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "removes": 0,
            "clears": 0
        }
        
        # Загрузка кэша из файла при инициализации
        self._load_cache()
        
        # Запускаем фоновую очистку истекших элементов
        self._start_cleanup_thread()
    
    def get(self, key: str) -> Any:
        """
        Получение значения из кэша.
        
        Args:
            key (str): Ключ для поиска в кэше
            
        Returns:
            Any: Значение из кэша или None, если ключ не найден или элемент истек
        """
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None
            
            cache_item = self.cache[key]
            current_time = time.time()
            
            # Проверяем, не истек ли элемент
            if "ttl" in cache_item and cache_item["ttl"]:
                if current_time > cache_item["created_at"] + cache_item["ttl"]:
                    # Элемент истек, удаляем его
                    del self.cache[key]
                    self.stats["misses"] += 1
                    return None
            
            # Обновляем время последнего доступа
            cache_item["last_accessed"] = current_time
            self.stats["hits"] += 1
            return cache_item["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Установка значения в кэш.
        
        Args:
            key (str): Ключ для сохранения в кэше
            value (Any): Значение для сохранения
            ttl (int, optional): Время жизни элемента в секундах
        """
        with self.lock:
            current_time = time.time()
            
            # Если кэш достиг максимального размера, удаляем наименее используемый элемент
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            self.cache[key] = {
                "value": value,
                "last_accessed": current_time,
                "created_at": current_time,
                "ttl": ttl
            }
            
            self.stats["sets"] += 1
            
            # Сохраняем кэш в файл
            self._save_cache()
    
    def remove(self, key: str) -> bool:
        """
        Удаляет элемент из кэша.
        
        Args:
            key (str): Ключ для удаления
            
        Returns:
            bool: True если элемент был удален, False если элемент не найден
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats["removes"] += 1
                self._save_cache()
                return True
            return False
    
    def clear(self) -> None:
        """Очистка всего кэша"""
        with self.lock:
            self.cache.clear()
            self.stats["clears"] += 1
            self._save_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики использования кэша.
        
        Returns:
            Dict[str, Any]: Статистика использования кэша
        """
        with self.lock:
            stats = self.stats.copy()
            stats["size"] = len(self.cache)
            stats["max_size"] = self.max_size
            
            # Добавляем информацию о заполненности кэша
            if self.max_size > 0:
                stats["fill_percentage"] = (len(self.cache) / self.max_size) * 100
            else:
                stats["fill_percentage"] = 0
                
            return stats
    
    def _evict_lru(self) -> None:
        """
        Удаляет наименее недавно использованный элемент из кэша.
        Используется алгоритм LRU (Least Recently Used).
        """
        if not self.cache:
            return
            
        # Находим ключ с наименьшим временем последнего доступа
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k]["last_accessed"])
        
        # Удаляем элемент
        del self.cache[lru_key]
        self.stats["evictions"] += 1
    
    def _save_cache(self) -> None:
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении кэша в файл: {e}")
    
    def _load_cache(self) -> None:
        """Загружает кэш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                self.logger.info(f"Кэш загружен из файла. Элементов: {len(self.cache)}")
                
                # Очищаем истекшие элементы при загрузке
                self._clean_expired_items()
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке кэша из файла: {e}")
            self.cache = {}
    
    def _clean_expired_items(self) -> None:
        """Очищает истекшие элементы из кэша"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, item in self.cache.items():
                if "ttl" in item and item["ttl"]:
                    if current_time > item["created_at"] + item["ttl"]:
                        expired_keys.append(key)
            
            # Удаляем истекшие элементы
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                self.logger.debug(f"Очищено {len(expired_keys)} истекших элементов кэша")
    
    def _start_cleanup_thread(self) -> None:
        """Запускает фоновый поток для очистки истекших элементов"""
        def cleanup_job():
            while True:
                time.sleep(3600)  # Проверяем каждый час
                try:
                    self._clean_expired_items()
                    self._save_cache()
                except Exception as e:
                    self.logger.error(f"Ошибка в фоновой очистке кэша: {e}")
        
        # Запускаем поток как демон, чтобы он автоматически завершался с основным потоком
        cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
        cleanup_thread.start()
