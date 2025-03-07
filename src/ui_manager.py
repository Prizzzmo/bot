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
        """Создаёт клавиатуру с темами для изучения"""
        keyboard = []
        
        # Ограничиваем количество тем для отображения
        max_topics = min(20, len(topics))
        
        # Формируем клавиатуру: по одной теме на строку
        for i in range(max_topics):
            # Добавляем номер для удобства
            display_name = f"{i+1}. {topics[i]}"
            # Обрезаем длинные темы для кнопок
            if len(display_name) > 35:
                display_name = display_name[:32] + "..."
            
            # Значение callback_data должно быть небольшим, используем индекс
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"topic_{i+1}")])
        
        # Добавляем кнопки для дополнительных опций
        keyboard.append([InlineKeyboardButton("🔄 Больше тем", callback_data="more_topics")])
        keyboard.append([InlineKeyboardButton("✏️ Своя тема", callback_data="custom_topic")])
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
        
        return InlineKeyboardMarkup(keyboard)
        
    def main_menu(self):
        """Возвращает клавиатуру главного меню (alias для get_main_menu_keyboard)"""
        return self.get_main_menu_keyboard()