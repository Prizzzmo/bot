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

    def __init__(self, logger: ILogger, max_size: int = 1000, cache_file: str = 'api_cache.json', memory_limit_mb: int = 200):
        """
        Инициализация системы кэширования.

        Args:
            logger (ILogger): Логгер для записи информации о работе кэша
            max_size (int): Максимальный размер кэша
            cache_file (str): Путь к файлу для персистентного хранения кэша
            memory_limit_mb (int): Ограничение памяти для кэша в МБ
        """
        self.logger = logger
        self.max_size = max_size
        self.cache_file = cache_file
        self.memory_limit_mb = memory_limit_mb
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_counter = {}  # Для отслеживания частоты использования элементов кэша
        self.last_cleanup_time = time.time()
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

            # Обновляем время последнего доступа и счетчик
            cache_item["last_accessed"] = current_time
            self.access_counter[key] = self.access_counter.get(key, 0) + 1
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
            self._cleanup_cache() #Added cleanup after set

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
                if key in self.access_counter:
                    del self.access_counter[key]
                self.stats["removes"] += 1
                self._save_cache()
                return True
            return False

    def clear(self) -> None:
        """Очистка всего кэша"""
        with self.lock:
            self.cache.clear()
            self.access_counter.clear()
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
            stats["memory_limit_mb"] = self.memory_limit_mb

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
        if lru_key in self.access_counter:
            del self.access_counter[lru_key]
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
            expired_keys = [
                key for key, item in self.cache.items()
                if "ttl" in item and item["ttl"] and current_time > item["created_at"] + item["ttl"]
            ]

            # Удаляем истекшие элементы одним батчем
            for key in expired_keys:
                del self.cache[key]
                if key in self.access_counter:
                    del self.access_counter[key]

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

    def clear_cache(self, topic_filter=None):
        """
        Очищает кэш API запросов

        Args:
            topic_filter (str, optional): Если указан, очищает только кэш по определенной теме

        Returns:
            int: Количество удаленных записей из кэша
        """
        try:
            # Проверяем существование директории кэша
            if not os.path.exists(self.cache_dir):
                return 0

            # Получаем список всех файлов кэша
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            count = 0

            # Если указан фильтр, проверяем содержимое каждого файла кэша
            if topic_filter:
                topic_filter = topic_filter.lower()
                for file_name in cache_files:
                    cache_file = os.path.join(self.cache_dir, file_name)
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                            # Проверяем, содержит ли запрос или ответ указанную тему
                            if ('query' in cache_data and topic_filter in cache_data['query'].lower()) or \
                               ('response' in cache_data and topic_filter in cache_data['response'].lower()):
                                os.remove(cache_file)
                                count += 1
                    except:
                        # Если не удалось прочитать файл, пропускаем его
                        continue
            else:
                # Удаляем все файлы кэша
                for file_name in cache_files:
                    os.remove(os.path.join(self.cache_dir, file_name))
                count = len(cache_files)

            self.logger.info(f"Очищено {count} записей из кэша API запросов")
            return count

        except Exception as e:
            self.logger.error(f"Ошибка при очистке кэша API запросов: {e}")
            return 0

    def _cleanup_cache(self):
        """
        Очищает кэш, если он превышает лимит памяти.
        Использует проверку реального размера объектов в памяти.
        """
        with self.lock:
            import sys
            
            # Проверка по количеству элементов
            if len(self.cache) > self.max_size:
                self._evict_lru()
                return
            
            # Проверка по фактическому использованию памяти
            try:
                total_size_bytes = 0
                memory_limit_bytes = self.memory_limit_mb * 1024 * 1024
                
                # Оцениваем размер в памяти
                for key, item in list(self.cache.items()):
                    # Оценка размера ключа и значения
                    key_size = sys.getsizeof(key)
                    value_size = sys.getsizeof(item.get('value', ''))
                    
                    # Добавляем размер метаданных
                    item_size = key_size + value_size + sys.getsizeof(item)
                    total_size_bytes += item_size
                    
                    # Если превысили лимит, удаляем по LRU
                    if total_size_bytes > memory_limit_bytes:
                        # Сортируем по времени последнего доступа
                        lru_items = sorted(
                            self.cache.items(), 
                            key=lambda x: x[1].get('last_accessed', 0)
                        )
                        
                        # Удаляем 25% самых старых элементов для снижения частоты очистки
                        items_to_remove = max(1, len(lru_items) // 4)
                        for i in range(items_to_remove):
                            if i < len(lru_items):
                                key_to_remove = lru_items[i][0]
                                if key_to_remove in self.cache:
                                    del self.cache[key_to_remove]
                                    if key_to_remove in self.access_counter:
                                        del self.access_counter[key_to_remove]
                                    self.stats["evictions"] += 1
                        
                        self._logger.info(f"Очищено {items_to_remove} элементов кэша из-за превышения лимита памяти")
                        return

            except Exception as e:
                self._logger.error(f"Ошибка при проверке размера кэша: {e}")
                # Если произошла ошибка, используем простую очистку по размеру
                if len(self.cache) > self.max_size * 0.9:  # 90% заполнения
                    self._evict_lru()