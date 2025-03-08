
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
import time
import tempfile

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api_cache import APICache
from src.interfaces import ILogger

class TestAPICache(unittest.TestCase):
    
    def setUp(self):
        """Подготовка окружения для тестов"""
        self.logger = MagicMock(spec=ILogger)
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.cache = APICache(self.logger, max_size=5, cache_file=self.temp_file.name)
        
    def tearDown(self):
        """Очистка после тестов"""
        os.unlink(self.temp_file.name)
    
    def test_cache_set_get(self):
        """Тест базового функционала установки и получения значений"""
        # Установка значения в кэш
        self.cache.set("test_key", "test_value")
        
        # Получение значения из кэша
        result = self.cache.get("test_key")
        
        # Проверка результата
        self.assertEqual(result, "test_value")
        self.assertEqual(self.cache.stats["sets"], 1)
        self.assertEqual(self.cache.stats["hits"], 1)
    
    def test_cache_expiration(self):
        """Тест истечения срока жизни элемента"""
        # Установка значения в кэш с коротким TTL
        self.cache.set("expiring_key", "expiring_value", ttl=0.1)
        
        # Проверяем, что значение доступно сразу
        self.assertEqual(self.cache.get("expiring_key"), "expiring_value")
        
        # Ждем истечения TTL
        time.sleep(0.2)
        
        # Проверяем, что значение больше недоступно
        self.assertIsNone(self.cache.get("expiring_key"))
        self.assertEqual(self.cache.stats["misses"], 1)
    
    def test_lru_eviction(self):
        """Тест вытеснения по LRU при достижении максимального размера"""
        # Заполняем кэш до максимума
        for i in range(5):
            self.cache.set(f"key_{i}", f"value_{i}")
        
        # Проверяем, что все значения доступны
        for i in range(5):
            self.assertEqual(self.cache.get(f"key_{i}"), f"value_{i}")
        
        # Добавляем еще один элемент, что должно вызвать вытеснение
        self.cache.set("new_key", "new_value")
        
        # Проверяем, что вытеснение произошло (должен быть удален самый старый элемент)
        self.assertIsNone(self.cache.get("key_0"))
        self.assertEqual(self.cache.get("new_key"), "new_value")
        self.assertEqual(self.cache.stats["evictions"], 1)
    
    def test_cache_remove(self):
        """Тест удаления элемента из кэша"""
        # Установка значения
        self.cache.set("remove_key", "remove_value")
        
        # Удаление значения
        result = self.cache.remove("remove_key")
        
        # Проверка результатов
        self.assertTrue(result)
        self.assertIsNone(self.cache.get("remove_key"))
        self.assertEqual(self.cache.stats["removes"], 1)
        
        # Попытка удалить несуществующий ключ
        result = self.cache.remove("nonexistent_key")
        self.assertFalse(result)
    
    def test_cache_clear(self):
        """Тест очистки всего кэша"""
        # Заполняем кэш
        for i in range(3):
            self.cache.set(f"clear_key_{i}", f"clear_value_{i}")
        
        # Проверяем наличие значений
        for i in range(3):
            self.assertEqual(self.cache.get(f"clear_key_{i}"), f"clear_value_{i}")
        
        # Очищаем кэш
        self.cache.clear()
        
        # Проверяем, что все значения удалены
        for i in range(3):
            self.assertIsNone(self.cache.get(f"clear_key_{i}"))
        
        self.assertEqual(self.cache.stats["clears"], 1)
    
    def test_cache_persistence(self):
        """Тест сохранения и загрузки кэша из файла"""
        # Заполняем кэш и сохраняем
        self.cache.set("persist_key", "persist_value")
        self.cache._save_cache()
        
        # Создаем новый экземпляр кэша с тем же файлом
        new_cache = APICache(self.logger, cache_file=self.temp_file.name)
        
        # Проверяем, что данные загружены
        self.assertEqual(new_cache.get("persist_key"), "persist_value")
    
    def test_get_stats(self):
        """Тест получения статистики кэша"""
        # Генерируем некоторую активность для статистики
        self.cache.set("stats_key", "stats_value")
        self.cache.get("stats_key")
        self.cache.get("nonexistent_key")
        
        # Получаем статистику
        stats = self.cache.get_stats()
        
        # Проверяем наличие ключевых метрик
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
        self.assertIn("sets", stats)
        self.assertIn("size", stats)
        self.assertIn("max_size", stats)
        
        # Проверяем значения метрик
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["sets"], 1)
        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["max_size"], 5)

if __name__ == '__main__':
    unittest.main()
