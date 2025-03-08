
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
import tempfile

# Add path to project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_migration import DataMigration

class TestDataMigration(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.mock_logger = MagicMock()
        
        # Создаем временные файлы для тестирования
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        
        # Создаем объект миграции с мок-логгером
        self.migration = DataMigration(self.mock_logger)
        
        # Патчим метод получения текущей версии
        self.migration.get_current_version = MagicMock(return_value=1)
    
    def tearDown(self):
        """Clean up after tests"""
        os.unlink(self.temp_file.name)
    
    def test_create_backup(self):
        """Test creating backup of data files"""
        # Настраиваем мок для os.path.exists
        with patch('os.path.exists', return_value=True), \
             patch('shutil.copy2') as mock_copy, \
             patch('time.time', return_value=12345):
            
            # Вызываем метод
            self.migration.create_backup()
            
            # Проверяем, что была попытка скопировать файлы
            mock_copy.assert_called()
            self.mock_logger.info.assert_called_with(mock_copy.call_args[0][0])
    
    def test_migrate_to_v2(self):
        """Test migration to version 2"""
        # Создаем тестовые данные версии 1
        test_data_v1 = {
            "user_id_1": {
                "name": "Test User",
                "state": "conversation"
            }
        }
        
        # Записываем тестовые данные во временный файл
        with open(self.temp_file.name, 'w') as f:
            json.dump(test_data_v1, f)
        
        # Патчим пути к файлам
        self.migration.user_states_file = self.temp_file.name
        
        # Вызываем метод миграции
        with patch('src.data_migration.DataMigration.update_version') as mock_update_version:
            self.migration.migrate_to_v2()
            
            # Проверяем, что версия была обновлена
            mock_update_version.assert_called_with(2)
        
        # Проверяем, что данные были мигрированы
        with open(self.temp_file.name, 'r') as f:
            migrated_data = json.load(f)
        
        # Проверяем новые поля в структуре данных
        self.assertIn("user_id_1", migrated_data)
        self.assertIn("analytics", migrated_data["user_id_1"])
        self.assertEqual(migrated_data["user_id_1"]["name"], "Test User")
    
    def test_should_migrate(self):
        """Test checking if migration is needed"""
        # Настраиваем мок для get_current_version
        self.migration.get_current_version = MagicMock(return_value=1)
        
        # Проверяем, нужна ли миграция до версии 2
        should_migrate = self.migration.should_migrate(2)
        self.assertTrue(should_migrate)
        
        # Проверяем, нужна ли миграция до версии 1
        should_migrate = self.migration.should_migrate(1)
        self.assertFalse(should_migrate)
        
        # Проверяем, нужна ли миграция до версии 0
        should_migrate = self.migration.should_migrate(0)
        self.assertFalse(should_migrate)
    
    def test_get_current_version_file_not_exists(self):
        """Test getting current version when file doesn't exist"""
        # Восстанавливаем оригинальный метод
        self.migration.get_current_version = DataMigration.get_current_version.__get__(self.migration, DataMigration)
        
        # Настраиваем мок для os.path.exists
        with patch('os.path.exists', return_value=False):
            # Должен вернуть 0, если файл не существует
            version = self.migration.get_current_version()
            self.assertEqual(version, 0)

if __name__ == '__main__':
    unittest.main()
