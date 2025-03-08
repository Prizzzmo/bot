
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import logging
import tempfile
import shutil
from datetime import datetime, timedelta
import json

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logger import Logger

class TestLogger(unittest.TestCase):
    
    def setUp(self):
        """Подготовка окружения для тестов"""
        # Создаем временную директорию для логов
        self.temp_dir = tempfile.mkdtemp()
        self.logger = Logger(log_level=logging.DEBUG, log_dir=self.temp_dir)
        
    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем временную директорию
        shutil.rmtree(self.temp_dir)
    
    def test_log_levels(self):
        """Тест различных уровней логирования"""
        # Логируем сообщения разных уровней
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        
        # Сбрасываем буфер
        self.logger.buffered_logger._check_flush()
        
        # Проверяем, что файл лога создан
        log_files = os.listdir(self.temp_dir)
        self.assertTrue(any(file.startswith('bot') and file.endswith('.log') for file in log_files))
    
    def test_error_logging(self):
        """Тест логирования ошибок"""
        try:
            # Генерируем исключение
            raise ValueError("Test error")
        except Exception as e:
            # Логируем ошибку
            self.logger.log_error(e, {"test_param": "test_value"})
        
        # Сбрасываем буфер
        self.logger.buffered_logger._check_flush()
        
        # Получаем логи
        logs = self.logger.get_logs(level="ERROR", limit=10)
        
        # Проверяем, что ошибка залогирована
        error_logs = [log for log in logs if "ValueError" in log.get("message", "")]
        self.assertTrue(len(error_logs) > 0)
        
        # Проверяем, что дополнительная информация включена
        info_logs = [log for log in logs if "test_param" in log.get("message", "")]
        self.assertTrue(len(info_logs) > 0)
    
    def test_get_logs_with_filter(self):
        """Тест получения логов с фильтрацией"""
        # Создаем логи разных уровней
        self.logger.debug("Debug test message")
        self.logger.info("Info test message")
        self.logger.warning("Warning test message")
        self.logger.error("Error test message")
        
        # Сбрасываем буфер
        self.logger.buffered_logger._check_flush()
        
        # Получаем логи с фильтром по уровню
        error_logs = self.logger.get_logs(level="ERROR", limit=10)
        warning_logs = self.logger.get_logs(level="WARNING", limit=10)
        
        # Проверяем, что фильтрация работает
        self.assertTrue(all(log.get("level") == "ERROR" for log in error_logs))
        self.assertTrue(all(log.get("level") in ["ERROR", "WARNING"] for log in warning_logs))
    
    def test_get_logs_date_range(self):
        """Тест получения логов в диапазоне дат"""
        # Логируем сообщение
        self.logger.error("Date range test message")
        
        # Сбрасываем буфер
        self.logger.buffered_logger._check_flush()
        
        # Устанавливаем диапазон дат
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        
        # Получаем логи в диапазоне дат
        logs = self.logger.get_logs(start_date=start_date, end_date=end_date, limit=10)
        
        # Проверяем, что логи получены
        self.assertTrue(len(logs) > 0)
        
        # Проверяем, что даты в правильном диапазоне
        for log in logs:
            log_date = log.get("timestamp")
            if log_date:
                self.assertTrue(start_date <= log_date <= end_date)
    
    def test_error_descriptions(self):
        """Тест описаний ошибок"""
        # Проверяем наличие известных описаний ошибок
        descriptions = self.logger._load_error_descriptions()
        
        self.assertIn("ConnectionError", descriptions)
        self.assertIn("Timeout", descriptions)
        self.assertIn("JSONDecodeError", descriptions)

if __name__ == '__main__':
    unittest.main()
