
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add path to project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.topic_service import TopicService

class TestTopicService(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.mock_api_client = MagicMock()
        self.mock_logger = MagicMock()
        
        # Configure mock response for API client
        self.mock_api_client.call_api.return_value = {
            "text": "1. Отечественная война 1812 года\n2. Великие реформы Александра II\n3. Октябрьская революция 1917 года",
            "status": "success"
        }
        
        # Create topic service with mocks
        self.topic_service = TopicService(self.mock_api_client, self.mock_logger)
    
    def test_generate_topics_list(self):
        """Test generating list of topics"""
        topics = self.topic_service.generate_topics_list()
        
        # Verify API was called
        self.mock_api_client.call_api.assert_called_once()
        
        # Verify topics list structure
        self.assertIsInstance(topics, list)
        self.assertTrue(len(topics) > 0)
        
    def test_generate_new_topics_list(self):
        """Test generating new topics list"""
        topics = self.topic_service.generate_new_topics_list()
        
        # Verify API was called
        self.mock_api_client.call_api.assert_called()
        
        # Verify topics list structure
        self.assertIsInstance(topics, list)
        self.assertTrue(len(topics) > 0)
    
    @patch('src.topic_service.time.sleep')
    def test_get_topic_info(self, mock_sleep):
        """Test getting topic information"""
        # Configure mock response for specific topic info
        self.mock_api_client.call_api.return_value = {
            "text": "# Отечественная война 1812 года\n\n## Глава 1: Истоки\nТекст главы...\n\n## Глава 2: Ход войны\nТекст главы...",
            "status": "success"
        }
        
        # Mock callback function
        mock_callback = MagicMock()
        
        # Call method
        messages = self.topic_service.get_topic_info("Отечественная война 1812 года", mock_callback)
        
        # Verify API was called
        self.mock_api_client.call_api.assert_called()
        
        # Verify callback was called
        mock_callback.assert_called()
        
        # Verify messages structure
        self.assertIsInstance(messages, list)
        self.assertTrue(len(messages) > 0)

if __name__ == '__main__':
    unittest.main()
