
import unittest
from unittest.mock import MagicMock, patch
import json
import os
from src.logger import Logger
from src.config import Config
from src.api_cache import APICache
from src.api_client import APIClient
from src.content_service import ContentService
from src.message_manager import MessageManager

class TestBotFunctionality(unittest.TestCase):
    
    def setUp(self):
        """Подготовка окружения для тестов"""
        self.logger = Logger()
        self.config = MagicMock()
        self.config.gemini_api_key = "test_api_key"
        self.api_cache = APICache(self.logger)
        
        # Создаем мок для API клиента
        self.api_client = MagicMock()
        self.api_client.ask_grok.return_value = "Test response"
        
        # Инициализируем тестируемые компоненты
        self.content_service = ContentService(self.api_client, self.logger)
        self.message_manager = MessageManager(self.logger)
        
    def test_api_cache(self):
        """Тест кэширования API запросов"""
        # Добавляем тестовые данные в кэш
        test_key = "test_prompt_0.3_1024"
        test_value = "Test cached response"
        self.api_cache.cache[test_key] = test_value
        
        # Сохраняем кэш в файл
        self.api_cache.save_cache()
        
        # Проверяем, что файл создан
        self.assertTrue(os.path.exists("api_cache.json"))
        
        # Загружаем кэш из файла
        new_cache = APICache(self.logger)
        
        # Проверяем, что данные загружены корректно
        self.assertEqual(new_cache.cache.get(test_key), test_value)
        
        # Очищаем после теста
        if os.path.exists("api_cache.json"):
            os.remove("api_cache.json")
            
    @patch('src.api_client.requests.post')
    def test_api_client(self, mock_post):
        """Тест клиента API с моком запросов"""
        # Настраиваем мок ответа
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Mocked API response"
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Создаем экземпляр API клиента для теста
        test_client = APIClient("test_key", self.api_cache, self.logger)
        
        # Тестируем метод ask_grok
        response = test_client.ask_grok("Test prompt", use_cache=False)
        
        # Проверяем результат
        self.assertEqual(response, "Mocked API response")
        
    def test_content_service_test_generation(self):
        """Тест генерации вопросов для тестирования"""
        # Настраиваем мок ответа API
        self.api_client.ask_grok.return_value = """
        1. Вопрос о восстании декабристов?
        A) Ответ 1
        B) Ответ 2
        C) Ответ 3
        D) Ответ 4
        Правильный ответ: 2
        
        2. Вопрос о Петре I?
        A) Ответ 1
        B) Ответ 2
        C) Ответ 3
        D) Ответ 4
        Правильный ответ: 3
        """
        
        # Вызываем тестируемый метод
        test_data = self.content_service.generate_test("История России")
        
        # Проверяем результаты
        self.assertIn("original_questions", test_data)
        self.assertIn("display_questions", test_data)
        self.assertEqual(len(test_data["original_questions"]), 2)
        self.assertEqual(len(test_data["display_questions"]), 2)

if __name__ == '__main__':
    unittest.main()
