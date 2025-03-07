import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class UIManager:
    """Класс для управления пользовательским интерфейсом бота"""

    def __init__(self, logger):
        self.logger = logger

    def get_main_menu_keyboard(self):
        """Возвращает клавиатуру главного меню"""
        keyboard = [
            [InlineKeyboardButton("Изучение истории", callback_data="topic")],
            [InlineKeyboardButton("Тесты", callback_data="test")],
            [InlineKeyboardButton("Беседа с ботом", callback_data="conversation")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_topics_keyboard(self, page=0):
        """Возвращает клавиатуру с историческими темами"""
        topics = [
            "Древняя Русь", "Киевская Русь", "Монгольское иго",
            "Московское царство", "Российская империя", "Революция 1917",
            "СССР", "Великая Отечественная война", "Современная Россия"
        ]

        # Определяем количество тем на странице и пагинацию
        topics_per_page = 3
        start_idx = page * topics_per_page
        end_idx = min(start_idx + topics_per_page, len(topics))

        # Формируем клавиатуру
        keyboard = []
        for i in range(start_idx, end_idx):
            keyboard.append([InlineKeyboardButton(topics[i], callback_data=f"topic_{topics[i]}")])

        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        if end_idx < len(topics):
            nav_buttons.append(InlineKeyboardButton("Далее ➡️", callback_data=f"page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        # Дополнительные кнопки
        keyboard.append([InlineKeyboardButton("Своя тема", callback_data="custom_topic")])
        keyboard.append([InlineKeyboardButton("Назад в меню", callback_data="back_to_menu")])

        return InlineKeyboardMarkup(keyboard)

    def get_test_keyboard(self):
        """Возвращает клавиатуру для тестов"""
        keyboard = [
            [InlineKeyboardButton("Лёгкий тест", callback_data="test_easy")],
            [InlineKeyboardButton("Средний тест", callback_data="test_medium")],
            [InlineKeyboardButton("Сложный тест", callback_data="test_hard")],
            [InlineKeyboardButton("Назад в меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_back_to_menu_keyboard(self):
        """Возвращает клавиатуру с кнопкой возврата в меню"""
        keyboard = [[InlineKeyboardButton("Назад в меню", callback_data="back_to_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def format_message(self, text, max_length=4000):
        """Форматирует сообщение, разбивая его на части, если оно слишком длинное"""
        if len(text) <= max_length:
            return [text]

        # Разбиваем на части по абзацам
        parts = []
        current_part = ""
        paragraphs = text.split("\n\n")

        for paragraph in paragraphs:
            if len(current_part) + len(paragraph) + 2 <= max_length:
                if current_part:
                    current_part += "\n\n"
                current_part += paragraph
            else:
                if current_part:
                    parts.append(current_part)
                current_part = paragraph

        if current_part:
            parts.append(current_part)

        return parts