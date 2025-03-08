"""Модуль для кэширования текстовых данных"""

import json
import os
import time
import hashlib
from typing import Dict, Any, Optional, List

from src.interfaces import ILogger
from src.base_service import BaseService

class TextCacheService(BaseService):
    """
    Сервис для кэширования текстовых данных, генерируемых ИИ.
    Хранит кэш в файле и обеспечивает быстрый доступ к ранее сгенерированным текстам.
    """

    def __init__(self, logger, cache_file='texts_cache.json', ttl=604800):
        super().__init__(logger)
        self.cache_file = cache_file
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
        }

        self._load_cache()

    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.

        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при инициализации TextCacheService: {e}")
            return False

    def get_text(self, topic: str, text_type: str) -> Optional[str]:
        """
        Получение текста из кэша.

        Args:
            topic (str): Тема, для которой был сгенерирован текст
            text_type (str): Тип текста (например, 'info', 'test', 'summary')

        Returns:
            Optional[str]: Текст из кэша или None, если не найден или истек
        """
        cache_key = self._generate_key(topic, text_type)

        if cache_key not in self.cache:
            self.stats["misses"] += 1
            self.logger.debug(f"Кэш-промах для темы '{topic}' (тип: {text_type})")
            return None

        cache_item = self.cache[cache_key]
        current_time = time.time()

        # Проверяем, не истек ли элемент
        if current_time > cache_item["created_at"] + self.ttl:
            # Элемент истек, удаляем его
            del self.cache[cache_key]
            self._save_cache()
            self.stats["misses"] += 1
            self.logger.debug(f"Истек кэш для темы '{topic}' (тип: {text_type})")
            return None

        # Обновляем время последнего доступа
        cache_item["last_accessed"] = current_time
        self.stats["hits"] += 1
        self.logger.debug(f"Кэш-попадание для темы '{topic}' (тип: {text_type})")
        return cache_item["text"]

    def save_text(self, topic: str, text_type: str, text: str) -> None:
        """
        Сохранение текста в кэш.

        Args:
            topic (str): Тема, для которой был сгенерирован текст
            text_type (str): Тип текста (например, 'info', 'test', 'summary')
            text (str): Текст для сохранения
        """
        cache_key = self._generate_key(topic, text_type)
        current_time = time.time()

        self.cache[cache_key] = {
            "text": text,
            "topic": topic,
            "type": text_type,
            "created_at": current_time,
            "last_accessed": current_time
        }

        self.stats["sets"] += 1
        self._save_cache()
        self.logger.info(f"Текст по теме '{topic}' (тип: {text_type}) сохранен в кэш")

    def clear_cache(self, topic_filter: Optional[str] = None) -> int:
        """
        Очистка кэша текстов.

        Args:
            topic_filter (Optional[str]): Если указан, очищает только кэш по определенной теме

        Returns:
            int: Количество удаленных записей из кэша
        """
        count = 0
        keys_to_delete = []

        if topic_filter:
            topic_filter = topic_filter.lower()
            for key, cache_item in self.cache.items():
                if "topic" in cache_item and topic_filter in cache_item["topic"].lower():
                    keys_to_delete.append(key)
        else:
            keys_to_delete = list(self.cache.keys())

        # Удаляем найденные ключи
        for key in keys_to_delete:
            del self.cache[key]
            count += 1

        if count > 0:
            self._save_cache()
            self.logger.info(f"Очищено {count} записей из кэша текстов")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики использования кэша.

        Returns:
            Dict[str, Any]: Статистика использования кэша
        """
        stats = self.stats.copy()
        stats["size"] = len(self.cache)

        # Вычисляем размер кэша в байтах
        try:
            stats["size_bytes"] = os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
        except:
            stats["size_bytes"] = 0

        # Добавляем размер кэша в мегабайтах
        stats["size_mb"] = round(stats["size_bytes"] / (1024 * 1024), 2) if stats["size_bytes"] > 0 else 0

        return stats

    def _generate_key(self, topic: str, text_type: str) -> str:
        """
        Генерирует ключ кэша для темы и типа текста.

        Args:
            topic (str): Тема текста
            text_type (str): Тип текста

        Returns:
            str: Хеш-ключ для кэша
        """
        # Нормализуем и объединяем тему и тип
        key_data = f"{topic.lower().strip()}:{text_type.lower().strip()}"
        # Создаем хеш для использования в качестве ключа
        return hashlib.md5(key_data.encode()).hexdigest()

    def _save_cache(self) -> None:
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении кэша текстов в файл: {e}")

    def _load_cache(self) -> None:
        """Загружает кэш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                self.logger.info(f"Кэш текстов загружен из файла. Элементов: {len(self.cache)}")
                self._clean_expired_items()
            else:
                self.cache = {}
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке кэша текстов из файла: {e}")
            self.cache = {}

    def _clean_expired_items(self) -> None:
        """Очищает истекшие элементы из кэша"""
        current_time = time.time()
        expired_keys = []

        for key, item in self.cache.items():
            if current_time > item["created_at"] + self.ttl:
                expired_keys.append(key)

        # Удаляем истекшие элементы
        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            self._save_cache()
            self.logger.debug(f"Очищено {len(expired_keys)} истекших элементов кэша текстов")