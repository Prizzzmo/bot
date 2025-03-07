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

    def parse_topics(self, topics_text):
        """Парсит и очищает список тем из текста"""
        # Используем регулярное выражение для извлечения тем
        import re
        # Ищем строки вида "1. Тема" или "1) Тема"
        topics_match = re.findall(r'\d+[\.\)]\s*([^\n]+)', topics_text)

        # Очищаем темы от лишних символов и пробелов
        filtered_topics = []
        for topic in topics_match:
            # Удаляем кавычки, точки в конце и лишние пробелы
            cleaned_topic = topic.strip(' "\'.,;').strip()
            if cleaned_topic:  # Проверяем, что тема не пустая
                filtered_topics.append(cleaned_topic)

        # Если не нашли тем через регулярное выражение, попробуем разбить по строкам
        if not filtered_topics:
            lines = topics_text.strip().split('\n')
            for line in lines:
                # Чистим строку от номеров, лишних символов и пробелов
                clean_line = re.sub(r'^\d+[\.\)]\s*', '', line).strip(' "\'.,;').strip()
                if clean_line:  # Проверяем, что строка не пустая
                    filtered_topics.append(clean_line)

        self.logger.info(f"Распознано {len(filtered_topics)} тем")
        return filtered_topics

    def create_topics_keyboard(self, topics):
        """
        Создает клавиатуру с темами для изучения.

        Args:
            topics (list): Список тем

        Returns:
            InlineKeyboardMarkup: Клавиатура с кнопками для выбора темы
        """
        keyboard = []
        row = []

        try:
            # Добавляем кнопки с темами (по две в ряд)
            for i, topic in enumerate(topics, 1):
                # Если тема имеет формат "номер. тема", извлекаем только тему
                if '. ' in topic and topic.split('. ')[0].isdigit():
                    display_text = topic.split('. ', 1)[1]
                else:
                    display_text = topic

                # Обрезаем текст кнопки, если он слишком длинный
                if len(display_text) > 30:
                    display_text = display_text[:27] + "..."

                button = InlineKeyboardButton(f"{i}. {display_text}", callback_data=f"topic_{i}")
                row.append(button)

                # Добавляем по две кнопки в ряд
                if len(row) == 2 or i == len(topics):
                    keyboard.append(row)
                    row = []

            # Добавляем дополнительные кнопки после списка тем
            keyboard.append([
                InlineKeyboardButton("🔄 Больше тем", callback_data="more_topics"),
                InlineKeyboardButton("✍️ Своя тема", callback_data="custom_topic")
            ])
            keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
        except Exception as e:
            # В случае ошибки создаем минимальную клавиатуру
            keyboard = [
                [InlineKeyboardButton("✍️ Своя тема", callback_data="custom_topic")],
                [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
            ]

        return InlineKeyboardMarkup(keyboard)

    def main_menu(self):
        """Возвращает клавиатуру главного меню (alias для get_main_menu_keyboard)"""
        return self.get_main_menu_keyboard()