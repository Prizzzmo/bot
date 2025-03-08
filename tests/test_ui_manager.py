
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add path to project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui_manager import UIManager
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TestUIManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.mock_logger = MagicMock()
        self.ui_manager = UIManager(self.mock_logger)
    
    def test_create_main_menu(self):
        """Test creating main menu keyboard"""
        # Вызываем метод
        keyboard = self.ui_manager.create_main_menu()
        
        # Проверяем результат
        self.assertIsInstance(keyboard, InlineKeyboardMarkup)
        self.assertTrue(len(keyboard.inline_keyboard) > 0)
        
        # Проверяем наличие основных пунктов меню
        button_texts = []
        for row in keyboard.inline_keyboard:
            for button in row:
                button_texts.append(button.text)
        
        self.assertIn("📚 Изучить историческую тему", button_texts)
        self.assertIn("🧠 Проверить знания", button_texts)
        self.assertIn("💬 Беседа", button_texts)
    
    def test_create_topics_keyboard(self):
        """Test creating topics keyboard"""
        # Тестовые данные
        topics = ["Тема 1", "Тема 2", "Тема 3", "Тема 4", "Тема 5", "Тема 6"]
        
        # Вызываем метод
        keyboard = self.ui_manager.create_topics_keyboard(topics)
        
        # Проверяем результат
        self.assertIsInstance(keyboard, InlineKeyboardMarkup)
        self.assertTrue(len(keyboard.inline_keyboard) > 0)
        
        # Проверяем, что все темы есть в клавиатуре
        button_data = []
        for row in keyboard.inline_keyboard:
            for button in row:
                button_data.append((button.text, button.callback_data))
        
        for topic in topics:
            self.assertTrue(any(topic in text for text, data in button_data))
        
        # Проверяем наличие кнопки "Назад"
        back_buttons = [button for row in keyboard.inline_keyboard for button in row if '🔙' in button.text]
        self.assertEqual(len(back_buttons), 1)
    
    def test_create_pagination_keyboard(self):
        """Test creating pagination keyboard"""
        # Тестовые данные
        items = [f"Item {i}" for i in range(1, 21)]
        page = 1
        page_size = 5
        callback_prefix = "test"
        
        # Вызываем метод
        keyboard = self.ui_manager.create_pagination_keyboard(items, page, page_size, callback_prefix)
        
        # Проверяем результат
        self.assertIsInstance(keyboard, InlineKeyboardMarkup)
        
        # Проверяем наличие кнопок навигации
        navigation_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data.startswith(f"{callback_prefix}_page"):
                    navigation_buttons.append(button)
        
        # Должны быть кнопки для следующей страницы
        self.assertTrue(any("➡️" in button.text for button in navigation_buttons))
        
        # На первой странице не должно быть кнопки для предыдущей страницы
        self.assertFalse(any("⬅️" in button.text for button in navigation_buttons))
    
    def test_format_message_with_markdown(self):
        """Test markdown formatting"""
        # Тестовые данные
        raw_text = "Это *выделенный* текст с _курсивом_ и `кодом`"
        
        # Вызываем метод
        formatted_text = self.ui_manager.format_message_with_markdown(raw_text)
        
        # Проверяем результат - должен быть обернут в try-except для безопасного форматирования
        self.assertIsInstance(formatted_text, str)
        self.assertIn("*выделенный*", formatted_text)
        self.assertIn("_курсивом_", formatted_text)
        self.assertIn("`кодом`", formatted_text)

if __name__ == '__main__':
    unittest.main()
