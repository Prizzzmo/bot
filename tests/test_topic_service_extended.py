
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json

# Add path to project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.topic_service import TopicService

class TestTopicServiceExtended(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.mock_api_client = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_cache = MagicMock()
        
        # Configure mock response for API client
        self.mock_api_client.call_api.return_value = {
            "text": "1. Отечественная война 1812 года\n2. Великие реформы Александра II\n3. Октябрьская революция 1917 года",
            "status": "success"
        }
        
        # Create topic service with mocks
        self.topic_service = TopicService(self.mock_api_client, self.mock_logger)
        
        # Патчим метод parse_topics для изолированного тестирования
        self.original_parse_topics = self.topic_service.parse_topics
        self.topic_service.parse_topics = MagicMock(return_value=[
            "Отечественная война 1812 года",
            "Великие реформы Александра II",
            "Октябрьская революция 1917 года"
        ])
    
    def tearDown(self):
        """Clean up after tests"""
        # Восстанавливаем оригинальный метод
        self.topic_service.parse_topics = self.original_parse_topics
    
    def test_parse_topics_real(self):
        """Test the actual implementation of parse_topics"""
        # Восстанавливаем реальный метод для тестирования
        self.topic_service.parse_topics = self.original_parse_topics
        
        # Тестовые данные
        test_text = """
        1. Киевская Русь (IX-XII вв.)
        2. Монгольское нашествие на Русь
        • Образование Российской империи
        - Великая Отечественная война
        """
        
        # Вызываем метод
        result = self.topic_service.parse_topics(test_text)
        
        # Проверяем результат
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        self.assertIn("Киевская Русь (IX-XII вв.)", result)
        self.assertIn("Монгольское нашествие на Русь", result)
        self.assertIn("Образование Российской империи", result)
        self.assertIn("Великая Отечественная война", result)
    
    def test_recommend_topics(self):
        """Test topic recommendation functionality"""
        # Настраиваем мок для API клиента
        self.mock_api_client.call_api.return_value = {
            "text": "1. Крымская война\n2. Русско-турецкая война\n3. Великая Отечественная война",
            "status": "success"
        }
        
        # Вызываем метод с текущей темой
        result = self.topic_service.recommend_similar_topics("Отечественная война 1812 года")
        
        # Проверяем результат
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.mock_api_client.call_api.assert_called_once()
        
        # Проверяем, что запрос содержит текущую тему
        call_args = self.mock_api_client.call_api.call_args[1]
        prompt = call_args.get('prompt', '')
        self.assertIn("Отечественная война 1812 года", prompt)
    
    def test_get_topic_info_with_cache(self):
        """Test getting topic information with cache hit"""
        # Настраиваем мок для кэша
        topic = "Отечественная война 1812 года"
        cached_content = "Cached content for Отечественная война"
        
        # Устанавливаем текстовый кэш
        self.topic_service.text_cache = self.mock_cache
        self.mock_cache.get_text.return_value = cached_content
        
        # Мок для callback
        mock_callback = MagicMock()
        
        # Вызываем метод
        result = self.topic_service.get_topic_info(topic, mock_callback)
        
        # Проверяем результат
        self.mock_cache.get_text.assert_called_once_with(topic, "topic_info")
        self.mock_api_client.call_api.assert_not_called()  # API не должен вызываться при наличии кэша
        mock_callback.assert_called()  # Callback должен быть вызван
        self.assertIn(cached_content, result[0])  # Кэшированный контент должен быть в результате

if __name__ == '__main__':
    unittest.main()
