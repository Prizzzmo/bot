
"""
Модуль для распределенного кэширования API запросов

Предоставляет возможность использовать распределенный кэш для больших нагрузок
с поддержкой нескольких бэкендов:
1. Redis (основной распределенный бэкенд)
2. Memcached (альтернативный бэкенд)
3. Локальный кэш (для резервирования)
"""

import json
import time
import hashlib
import threading
from typing import Dict, Any, Optional, Union
import os
import redis
import pickle

from src.interfaces import ICache, ILogger

class DistributedCache(ICache):
    """
    Реализация распределенного кэша для API запросов.
    
    Особенности:
    - Поддержка Redis для распределенного хранения
    - Локальный кэш для быстрого доступа к часто используемым элементам
    - Автоматическое переключение на локальный режим при недоступности Redis
    """
    
    def __init__(self, logger: ILogger, redis_url: Optional[str] = None, 
                 max_local_size: int = 1000, local_cache_file: str = 'local_cache.json'):
        """
        Инициализация распределенного кэша.
        
        Args:
            logger (ILogger): Логгер для записи информации
            redis_url (str, optional): URL подключения к Redis
            max_local_size (int): Максимальный размер локального кэша
            local_cache_file (str): Файл для локального кэша
        """
        self.logger = logger
        self.redis_url = redis_url
        self.redis_client = None
        self.using_redis = False
        self.max_local_size = max_local_size
        self.local_cache_file = local_cache_file
        self.local_cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()  # Для потокобезопасности
        
        # Счетчики для статистики
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "removes": 0,
            "clears": 0,
            "redis_errors": 0,
            "redis_hits": 0
        }
        
        # Инициализация Redis и локального кэша
        self._init_redis()
        self._load_local_cache()
        
        # Запускаем фоновую очистку истекших элементов
        self._start_cleanup_thread()
    
    def _init_redis(self) -> None:
        """Инициализирует подключение к Redis"""
        if not self.redis_url:
            self.logger.info("URL Redis не указан, используется только локальный кэш")
            self.using_redis = False
            return
        
        try:
            self.redis_client = redis.from_url(self.redis_url)
            # Проверка соединения
            self.redis_client.ping()
            self.using_redis = True
            self.logger.info("Успешное подключение к Redis")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Redis: {e}. Используется локальный кэш.")
            self.using_redis = False
            self.redis_client = None
    
    def get(self, key: str) -> Any:
        """
        Получение значения из кэша.
        
        Стратегия:
        1. Сначала проверяем локальный кэш для быстрого доступа
        2. Если не найдено, и Redis доступен, проверяем в Redis
        
        Args:
            key (str): Ключ для поиска в кэше
            
        Returns:
            Any: Значение из кэша или None, если ключ не найден или элемент истек
        """
        with self.lock:
            # Проверяем сначала локальный кэш
            value = self._get_from_local(key)
            if value is not None:
                return value
            
            # Если локальный кэш не содержит значение и Redis доступен
            if self.using_redis and self.redis_client:
                try:
                    redis_key = f"api_cache:{key}"
                    cached_data = self.redis_client.get(redis_key)
                    
                    if cached_data:
                        # Десериализуем данные из Redis
                        try:
                            cache_item = pickle.loads(cached_data)
                            # Проверяем TTL
                            current_time = time.time()
                            if "ttl" in cache_item and cache_item["ttl"] and current_time > cache_item["created_at"] + cache_item["ttl"]:
                                # Элемент истек, удаляем его
                                self.redis_client.delete(redis_key)
                                self.stats["misses"] += 1
                                return None
                            
                            # Обновляем статистику
                            self.stats["hits"] += 1
                            self.stats["redis_hits"] += 1
                            
                            # Добавляем в локальный кэш для ускорения будущих запросов
                            value = cache_item["value"]
                            self._add_to_local_cache(key, value, cache_item.get("ttl"))
                            
                            return value
                        except Exception as e:
                            self.logger.error(f"Ошибка десериализации данных из Redis: {e}")
                except Exception as e:
                    self.logger.warning(f"Ошибка при получении данных из Redis: {e}")
                    self.stats["redis_errors"] += 1
                    # Если Redis недоступен, переключаемся на локальный режим
                    self.using_redis = False
            
            # Значение не найдено
            self.stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Установка значения в кэш.
        
        Стратегия:
        1. Сохраняем в локальный кэш для быстрого доступа
        2. Если Redis доступен, сохраняем также в Redis
        
        Args:
            key (str): Ключ для сохранения в кэше
            value (Any): Значение для сохранения
            ttl (int, optional): Время жизни элемента в секундах
        """
        with self.lock:
            current_time = time.time()
            cache_item = {
                "value": value,
                "last_accessed": current_time,
                "created_at": current_time,
                "ttl": ttl
            }
            
            # Сохраняем в локальный кэш
            self._add_to_local_cache(key, value, ttl)
            
            # Если Redis доступен, сохраняем также там
            if self.using_redis and self.redis_client:
                try:
                    redis_key = f"api_cache:{key}"
                    # Сериализуем данные для Redis
                    serialized_data = pickle.dumps(cache_item)
                    
                    # Если указан TTL, устанавливаем его
                    if ttl:
                        self.redis_client.setex(redis_key, ttl, serialized_data)
                    else:
                        self.redis_client.set(redis_key, serialized_data)
                except Exception as e:
                    self.logger.warning(f"Ошибка при сохранении данных в Redis: {e}")
                    self.stats["redis_errors"] += 1
                    # Если Redis недоступен, переключаемся на локальный режим
                    self.using_redis = False
            
            self.stats["sets"] += 1
    
    def remove(self, key: str) -> bool:
        """
        Удаляет элемент из кэша.
        
        Args:
            key (str): Ключ для удаления
            
        Returns:
            bool: True если элемент был удален, False если элемент не найден
        """
        with self.lock:
            removed_local = False
            removed_redis = False
            
            # Удаляем из локального кэша
            if key in self.local_cache:
                del self.local_cache[key]
                removed_local = True
                self._save_local_cache()
            
            # Если Redis доступен, удаляем также оттуда
            if self.using_redis and self.redis_client:
                try:
                    redis_key = f"api_cache:{key}"
                    removed_redis = bool(self.redis_client.delete(redis_key))
                except Exception as e:
                    self.logger.warning(f"Ошибка при удалении данных из Redis: {e}")
                    self.stats["redis_errors"] += 1
                    # Если Redis недоступен, переключаемся на локальный режим
                    self.using_redis = False
            
            if removed_local or removed_redis:
                self.stats["removes"] += 1
                return True
            return False
    
    def clear(self) -> None:
        """Очистка всего кэша"""
        with self.lock:
            # Очищаем локальный кэш
            self.local_cache.clear()
            self._save_local_cache()
            
            # Если Redis доступен, очищаем также его
            if self.using_redis and self.redis_client:
                try:
                    # Очищаем все ключи с префиксом "api_cache:"
                    pattern = "api_cache:*"
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, pattern, 100)
                        if keys:
                            self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                except Exception as e:
                    self.logger.warning(f"Ошибка при очистке данных из Redis: {e}")
                    self.stats["redis_errors"] += 1
                    # Если Redis недоступен, переключаемся на локальный режим
                    self.using_redis = False
            
            self.stats["clears"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики использования кэша.
        
        Returns:
            Dict[str, Any]: Статистика использования кэша
        """
        with self.lock:
            stats = self.stats.copy()
            stats["size_local"] = len(self.local_cache)
            stats["max_local_size"] = self.max_local_size
            stats["using_redis"] = self.using_redis
            
            # Добавляем информацию о заполненности локального кэша
            if self.max_local_size > 0:
                stats["local_fill_percentage"] = (len(self.local_cache) / self.max_local_size) * 100
            else:
                stats["local_fill_percentage"] = 0
            
            # Если Redis доступен, добавляем информацию о нем
            if self.using_redis and self.redis_client:
                try:
                    # Получаем количество ключей с префиксом "api_cache:"
                    pattern = "api_cache:*"
                    cursor = 0
                    redis_count = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, pattern, 100)
                        redis_count += len(keys)
                        if cursor == 0:
                            break
                    
                    stats["redis_size"] = redis_count
                    stats["redis_info"] = {
                        "memory_used": self.redis_client.info()["used_memory_human"],
                        "total_connections": self.redis_client.info()["total_connections_received"],
                        "uptime": self.redis_client.info()["uptime_in_seconds"]
                    }
                except Exception as e:
                    self.logger.warning(f"Ошибка при получении статистики Redis: {e}")
                    stats["redis_error"] = str(e)
            
            return stats
    
    def clear_cache(self, topic_filter=None):
        """
        Очищает кэш API запросов
        
        Args:
            topic_filter (str, optional): Если указан, очищает только кэш по определенной теме
            
        Returns:
            int: Количество удаленных записей из кэша
        """
        count = 0
        
        with self.lock:
            # Очищаем локальный кэш
            if topic_filter:
                # Фильтруем по теме
                keys_to_delete = []
                for key, item in self.local_cache.items():
                    # Проверяем наличие темы в значении
                    value_str = str(item.get("value", "")).lower()
                    if topic_filter.lower() in value_str:
                        keys_to_delete.append(key)
                
                # Удаляем найденные ключи
                for key in keys_to_delete:
                    del self.local_cache[key]
                    count += 1
            else:
                # Очищаем весь кэш
                count = len(self.local_cache)
                self.local_cache.clear()
            
            # Сохраняем локальный кэш
            self._save_local_cache()
            
            # Если Redis доступен, очищаем также его
            if self.using_redis and self.redis_client:
                try:
                    if topic_filter:
                        # Для Redis нам нужно будет проверить каждый ключ
                        pattern = "api_cache:*"
                        cursor = 0
                        redis_count = 0
                        
                        while True:
                            cursor, keys = self.redis_client.scan(cursor, pattern, 100)
                            
                            for key in keys:
                                try:
                                    # Получаем значение и проверяем его содержимое
                                    cached_data = self.redis_client.get(key)
                                    if cached_data:
                                        cache_item = pickle.loads(cached_data)
                                        value_str = str(cache_item.get("value", "")).lower()
                                        
                                        if topic_filter.lower() in value_str:
                                            self.redis_client.delete(key)
                                            redis_count += 1
                                except Exception as e:
                                    self.logger.debug(f"Ошибка при проверке ключа Redis {key}: {e}")
                            
                            if cursor == 0:
                                break
                        
                        count += redis_count
                    else:
                        # Очищаем все ключи с префиксом "api_cache:"
                        pattern = "api_cache:*"
                        keys = self.redis_client.keys(pattern)
                        if keys:
                            count_redis = len(keys)
                            self.redis_client.delete(*keys)
                            count += count_redis
                except Exception as e:
                    self.logger.warning(f"Ошибка при очистке данных из Redis: {e}")
                    self.stats["redis_errors"] += 1
                    # Если Redis недоступен, переключаемся на локальный режим
                    self.using_redis = False
            
            self.logger.info(f"Очищено {count} записей из кэша API запросов")
            return count
    
    def _get_from_local(self, key: str) -> Any:
        """
        Получает значение из локального кэша.
        
        Args:
            key (str): Ключ для поиска
            
        Returns:
            Any: Значение или None, если не найдено или истекло
        """
        if key not in self.local_cache:
            return None
        
        cache_item = self.local_cache[key]
        current_time = time.time()
        
        # Проверяем TTL
        if "ttl" in cache_item and cache_item["ttl"] and current_time > cache_item["created_at"] + cache_item["ttl"]:
            # Элемент истек, удаляем его
            del self.local_cache[key]
            return None
        
        # Обновляем время последнего доступа
        cache_item["last_accessed"] = current_time
        
        # Обновляем статистику
        self.stats["hits"] += 1
        
        return cache_item["value"]
    
    def _add_to_local_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Добавляет значение в локальный кэш.
        
        Args:
            key (str): Ключ для сохранения
            value (Any): Значение для сохранения
            ttl (int, optional): Время жизни элемента в секундах
        """
        current_time = time.time()
        
        # Если кэш достиг максимального размера, удаляем наименее используемый элемент
        if len(self.local_cache) >= self.max_local_size and key not in self.local_cache:
            self._evict_lru()
        
        # Добавляем элемент в кэш
        self.local_cache[key] = {
            "value": value,
            "last_accessed": current_time,
            "created_at": current_time,
            "ttl": ttl
        }
        
        # Сохраняем локальный кэш
        self._save_local_cache()
    
    def _evict_lru(self) -> None:
        """Удаляет наименее недавно использованный элемент из локального кэша"""
        if not self.local_cache:
            return
        
        # Находим ключ с наименьшим временем последнего доступа
        lru_key = min(self.local_cache.keys(), key=lambda k: self.local_cache[k]["last_accessed"])
        
        # Удаляем элемент
        del self.local_cache[lru_key]
        self.stats["evictions"] += 1
    
    def _save_local_cache(self) -> None:
        """Сохраняет локальный кэш в файл"""
        try:
            with open(self.local_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.local_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении локального кэша в файл: {e}")
    
    def _load_local_cache(self) -> None:
        """Загружает локальный кэш из файла"""
        try:
            if os.path.exists(self.local_cache_file):
                with open(self.local_cache_file, 'r', encoding='utf-8') as f:
                    self.local_cache = json.load(f)
                self.logger.info(f"Локальный кэш загружен из файла. Элементов: {len(self.local_cache)}")
                
                # Очищаем истекшие элементы при загрузке
                self._clean_expired_items()
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке локального кэша из файла: {e}")
            self.local_cache = {}
    
    def _clean_expired_items(self) -> None:
        """Очищает истекшие элементы из локального кэша"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.local_cache.items()
                if "ttl" in item and item["ttl"] and current_time > item["created_at"] + item["ttl"]
            ]
            
            # Удаляем истекшие элементы
            for key in expired_keys:
                del self.local_cache[key]
            
            if expired_keys:
                self.logger.debug(f"Очищено {len(expired_keys)} истекших элементов локального кэша")
                self._save_local_cache()
    
    def _start_cleanup_thread(self) -> None:
        """Запускает фоновый поток для очистки истекших элементов"""
        def cleanup_job():
            while True:
                try:
                    # Очищаем истекшие элементы каждый час
                    time.sleep(3600)
                    self._clean_expired_items()
                    
                    # Пробуем восстановить соединение с Redis, если оно было потеряно
                    if self.redis_url and not self.using_redis:
                        self._init_redis()
                except Exception as e:
                    self.logger.error(f"Ошибка в фоновой очистке кэша: {e}")
        
        # Запускаем поток как демон
        cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
        cleanup_thread.start()
