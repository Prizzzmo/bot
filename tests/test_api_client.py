
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json

# Add path to project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api_client import APIClient
from src.logger import Logger

class TestAPIClient(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.mock_cache = MagicMock()
        self.mock_cache.get.return_value = None
        self.mock_logger = MagicMock()
        
        # Mock the genai module
        self.patcher = patch('src.api_client.genai')
        self.mock_genai = self.patcher.start()
        
        # Set up mock response for generate_content
        self.mock_response = MagicMock()
        self.mock_response.text = "Test response"
        self.mock_model = MagicMock()
        self.mock_model.generate_content.return_value = self.mock_response
        self.mock_genai.GenerativeModel.return_value = self.mock_model
        
        # Create API client with mocks
        self.api_client = APIClient("fake_api_key", self.mock_cache, self.mock_logger)
        self.api_client.model = self.mock_model
        
    def tearDown(self):
        """Clean up after tests"""
        self.patcher.stop()
    
    def test_call_api(self):
        """Test the call_api method with cache miss"""
        result = self.api_client.call_api("Test prompt", temperature=0.5, max_tokens=100)
        
        # Verify cache was checked
        self.mock_cache.get.assert_called_once()
        
        # Verify API was called
        self.mock_model.generate_content.assert_called_once()
        
        # Verify result structure
        self.assertEqual(result["text"], "Test response")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["model"], "gemini-2.0-flash")
        self.assertIn("elapsed_time", result)
        
        # Verify result was cached
        self.mock_cache.set.assert_called_once()
    
    def test_call_api_with_cache_hit(self):
        """Test the call_api method with cache hit"""
        cached_result = {
            "text": "Cached response",
            "status": "success",
            "model": "gemini-2.0-flash",
            "elapsed_time": 0.1
        }
        self.mock_cache.get.return_value = cached_result
        
        result = self.api_client.call_api("Test prompt", temperature=0.5, max_tokens=100)
        
        # Verify cache was checked
        self.mock_cache.get.assert_called_once()
        
        # Verify API was not called
        self.mock_model.generate_content.assert_not_called()
        
        # Verify cached result was returned
        self.assertEqual(result, cached_result)
    
    def test_validate_historical_topic(self):
        """Test the validate_historical_topic method"""
        # Set up mock response
        self.mock_response.text = "Да"
        
        result = self.api_client.validate_historical_topic("Великая Отечественная война")
        
        # Verify API was called with correct prompt
        self.mock_model.generate_content.assert_called_once()
        call_args = self.mock_model.generate_content.call_args[1]
        self.assertIn("Определи, относится ли следующий запрос к истории России", call_args.get('content', ''))
        
        # Verify result
        self.assertTrue(result)
    
    def test_generate_historical_test(self):
        """Test the generate_historical_test method"""
        # Set up mock response
        test_content = """
        1. Когда началась Великая Отечественная война?
        1) 1939
        2) 1941
        3) 1942
        4) 1945
        Правильный ответ: 2
        
        2. Кто был Верховным Главнокомандующим СССР?
        1) Жуков
        2) Сталин
        3) Молотов
        4) Рокоссовский
        Правильный ответ: 2
        """
        self.mock_response.text = test_content
        
        result = self.api_client.generate_historical_test("Великая Отечественная война")
        
        # Verify API was called with correct prompt
        self.mock_model.generate_content.assert_called_once()
        
        # Verify result structure
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["topic"], "Великая Отечественная война")
        self.assertIsInstance(result["content"], list)
        self.assertIsInstance(result["original_questions"], list)
        self.assertIsInstance(result["display_questions"], list)

if __name__ == '__main__':
    unittest.main()
