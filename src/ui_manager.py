import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.topic_service import TopicService # Import the new TopicService

class UIManager:
    """Класс для управления пользовательским интерфейсом с функциями очистки текста для Telegram"""

    def __init__(self, logger, topic_service: TopicService): # Inject TopicService
        self.logger = logger
        self.topic_service = topic_service
        
    def sanitize_markdown(self, text):
        """
        Очищает текст от символов, которые могут вызвать проблемы при отображении Markdown в Telegram.
        
        Args:
            text (str): Исходный текст
            
        Returns:
            str: Очищенный текст
        """
        if not text:
            return ""
            
        # Экранируем специальные символы Markdown
        chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in chars_to_escape:
            text = text.replace(char, '\\' + char)
            
        return text

    def main_menu(self):
        """
        Создает главное меню в виде кнопок.

        Returns:
            InlineKeyboardMarkup: Клавиатура с кнопками меню
        """
        keyboard = [
            [InlineKeyboardButton("🔍 Выбрать тему", callback_data='topic')],
            [InlineKeyboardButton("✅ Пройти тест", callback_data='test')],
            [InlineKeyboardButton("🗺️ Историческая карта", callback_data='history_map')],
            [InlineKeyboardButton("💬 Беседа о истории России", callback_data='conversation')],
            [InlineKeyboardButton("ℹ️ Информация о проекте", callback_data='project_info')],
            [InlineKeyboardButton("❌ Завершить", callback_data='cancel')]
        ]
        return InlineKeyboardMarkup(keyboard)


    def create_topics_keyboard(self, topics):
        """
        Создает клавиатуру с кнопками для выбора темы.

        Args:
            topics (list): Список тем

        Returns:
            InlineKeyboardMarkup: Клавиатура с кнопками
        """
        keyboard = []

        for i, topic in enumerate(topics, 1):
            # Проверяем, что тема не пустая
            if topic and len(topic.strip()) > 0:
                # Удаляем существующую нумерацию, если она есть
                if re.match(r'^\d+[\.\)\:]\s+', topic):
                    # Тема уже содержит номер, используем ее как есть
                    display_topic = topic
                else:
                    # Добавляем номер к теме
                    display_topic = f"{i}. {topic}"
                
                # Очищаем тему от спецсимволов для безопасного отображения
                display_topic = self.sanitize_markdown(display_topic)
                
                # Ограничиваем длину темы в кнопке
                display_topic = display_topic[:30] + '...' if len(display_topic) > 30 else display_topic
                keyboard.append([InlineKeyboardButton(display_topic, callback_data=f'topic_{i}')])
            else:
                # Если тема пустая, добавляем заполнитель
                keyboard.append([InlineKeyboardButton(f"{i}. [Тема не определена]", callback_data=f'topic_{i}')])

        # Добавляем кнопку для ввода своей темы и показать больше тем
        keyboard.append([
            InlineKeyboardButton("📝 Своя тема", callback_data='custom_topic'),
            InlineKeyboardButton("🔄 Больше тем", callback_data='more_topics')
        ])

        # Добавляем кнопку возврата в меню
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')])

        return InlineKeyboardMarkup(keyboard)

# src/topic_service.py
import re

class TopicService:
    def parse_topics(self, topics_text):
        """
        Парсит текст с темами и возвращает отформатированный список тем с оптимизацией.

        Args:
            topics_text (str): Текст с темами от API

        Returns:
            list: Список отформатированных тем
        """
        filtered_topics = []

        # Оптимизированное регулярное выражение для более эффективного извлечения тем
        pattern = r'(?:^\d+[.):]\s*|^[*•-]\s*|^[а-яА-Я\w]+[:.]\s*)(.+?)$'

        # Используем множество для быстрой проверки дубликатов
        unique_topics_set = set()

        for line in topics_text.split('\n'):
            line = line.strip()
            if not line or len(line) <= 1:
                continue

            # Пытаемся извлечь тему с помощью регулярного выражения
            match = re.search(pattern, line, re.MULTILINE)
            if match:
                topic_text = match.group(1).strip()
                if topic_text and topic_text not in unique_topics_set:
                    filtered_topics.append(topic_text)
                    unique_topics_set.add(topic_text)
            # Если регулярное выражение не сработало, используем упрощенную версию
            elif '.' in line or ':' in line:
                parts = line.split('.', 1) if '.' in line else line.split(':', 1)
                if len(parts) > 1:
                    topic_text = parts[1].strip()
                    if topic_text and topic_text not in unique_topics_set:
                        filtered_topics.append(topic_text)
                        unique_topics_set.add(topic_text)
            # Простая эвристика для строк, начинающихся с цифры
            elif line[0].isdigit():
                i = 1
                while i < len(line) and (line[i].isdigit() or line[i] in ' \t.):'):
                    i += 1
                if i < len(line):
                    topic_text = line[i:].strip()
                    if topic_text and topic_text not in unique_topics_set:
                        filtered_topics.append(topic_text)
                        unique_topics_set.add(topic_text)
            else:
                if line not in unique_topics_set:
                    filtered_topics.append(line)
                    unique_topics_set.add(line)

        # Ограничиваем до 30 тем
        return filtered_topics[:30]