
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.conversation_service import ConversationService


class TestConversationService(unittest.TestCase):
    """Тесты для ConversationService"""

    def setUp(self):
        """Установка перед каждым тестом"""
        self.api_client = MagicMock()
        self.logger = MagicMock()
        self.conversation_service = ConversationService(self.api_client, self.logger)
        
        # Мокирование методов API
        self.api_client.ask_grok.return_value = "Тестовый ответ от API"

    def test_is_history_related(self):
        """Тест определения связи сообщения с историей"""
        # Сообщения, связанные с историей
        history_messages = [
            "Когда произошла Октябрьская революция?",
            "Расскажи о Петре I",
            "Какие реформы провел Александр II?",
            "История Российской империи",
            "Кто победил в Отечественной войне 1812 года?",
        ]
        
        # Сообщения, не связанные с историей
        non_history_messages = [
            "Какая сегодня погода?",
            "Сколько будет 2+2?",
            "Как приготовить борщ?",
            "Привет, как дела?",
            "Расскажи анекдот",
        ]
        
        # Проверяем, что исторические сообщения распознаются правильно
        for msg in history_messages:
            user_data = {}
            self.assertTrue(
                self.conversation_service._is_history_related(msg, user_data),
                f"Сообщение должно быть определено как историческое: {msg}"
            )
        
        # Проверяем, что неисторические сообщения распознаются правильно
        for msg in non_history_messages:
            user_data = {}
            self.assertFalse(
                self.conversation_service._is_history_related(msg, user_data),
                f"Сообщение не должно быть определено как историческое: {msg}"
            )
    
    def test_is_history_related_with_context(self):
        """Тест определения связи с историей с учетом контекста предыдущих сообщений"""
        # Контекст с историческими сообщениями
        user_data = {'conversation_history': ['Расскажи о Петре I', 'Когда он родился?']}
        
        # Проверяем, что сообщение без явных исторических маркеров 
        # определяется как историческое с учетом контекста
        self.assertTrue(
            self.conversation_service._is_history_related('А чем он известен?', user_data),
            "Сообщение должно быть определено как историческое с учетом контекста"
        )

    def test_enhance_historical_response(self):
        """Тест улучшения форматирования исторического ответа"""
        # Простой ответ
        simple_response = "Краткий ответ на исторический вопрос."
        enhanced_simple = self.conversation_service._enhance_historical_response(simple_response)
        self.assertEqual(enhanced_simple, simple_response)
        
        # Ответ с перечислением
        list_response = "Основные реформы Петра I: создание регулярной армии, строительство флота, реформа образования."
        enhanced_list = self.conversation_service._enhance_historical_response(list_response)
        self.assertIn("•", enhanced_list, "Должно быть добавлено форматирование списка")
        
        # Проверка разбивки длинных абзацев
        long_paragraph = "Длинный абзац. " * 30
        enhanced_long = self.conversation_service._enhance_historical_response(long_paragraph)
        self.assertNotEqual(enhanced_long, long_paragraph, "Длинный абзац должен быть разбит")

    def test_generate_historical_response(self):
        """Тест генерации ответа на исторический вопрос"""
        self.api_client.ask_grok.return_value = "Исторический ответ от API"
        
        user_message = "Когда была Куликовская битва?"
        user_data = {'conversation_history': [user_message]}
        
        response = self.conversation_service._generate_historical_response(user_message, user_data)
        
        # Проверяем, что был вызван метод API с правильными параметрами
        self.api_client.ask_grok.assert_called_once()
        call_args = self.api_client.ask_grok.call_args[0][0]
        self.assertIn(user_message, call_args)
        self.assertIn("истории России", call_args)
        
        # Проверяем результат
        self.assertEqual(response, "Исторический ответ от API")

    def test_get_default_response(self):
        """Тест получения стандартного ответа"""
        default_response = self.conversation_service._get_default_response()
        self.assertIn("истории России", default_response)
        self.assertIn("Пожалуйста, задайте вопрос", default_response)

    def test_normalize_russian_input(self):
        """Тест нормализации русскоязычного пользовательского ввода"""
        # Проверка коррекции опечаток
        misspelled = "истори росии"
        normalized = self.conversation_service._normalize_russian_input(misspelled)
        self.assertIn("история", normalized)
        self.assertIn("россии", normalized)
        
        # Проверка замены латинских символов на кириллические
        mixed_chars = "иcтopия poccии"  # содержит латинские 'c', 'p', 'o'
        normalized = self.conversation_service._normalize_russian_input(mixed_chars)
        self.assertEqual(normalized, "история россии")


if __name__ == '__main__':
    unittest.main()
