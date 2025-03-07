
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class UIManager:
    """Класс для управления пользовательским интерфейсом"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def main_menu(self):
        """Создает клавиатуру с главным меню"""
        keyboard = [
            [InlineKeyboardButton("📚 Выбрать тему", callback_data='topic')],
            [InlineKeyboardButton("🧠 Пройти тест", callback_data='test')],
            [InlineKeyboardButton("🗣️ Беседа об истории", callback_data='conversation')],
            [InlineKeyboardButton("🧹 Очистить чат", callback_data='clear_client')],
            [InlineKeyboardButton("ℹ️ О проекте", callback_data='project_info')]
        ]
        return InlineKeyboardMarkup(keyboard)
        
    def parse_topics(self, topics_text):
        """Парсит темы из текста, возвращенного API"""
        topics = []
        
        # Ищем списки с нумерацией
        matches = re.findall(r'^\s*\d+\.\s+(.+)$', topics_text, re.MULTILINE)
        
        # Если нашли нумерованный список
        if matches:
            topics = [match.strip() for match in matches if match.strip()]
        else:
            # Пробуем искать темы с тире или звездочками
            alt_matches = re.findall(r'^\s*[-*]\s+(.+)$', topics_text, re.MULTILINE)
            if alt_matches:
                topics = [match.strip() for match in alt_matches if match.strip()]
            else:
                # Если не нашли ни нумерованного списка, ни списка с тире, разбиваем по строкам
                lines = topics_text.split('\n')
                topics = [line.strip() for line in lines if line.strip() and len(line.strip()) < 100]
        
        return topics
    
    def create_topics_keyboard(self, topics):
        """Создает клавиатуру с темами"""
        keyboard = []
        
        # Добавляем до 10 тем (по 2 в ряд)
        topics_to_show = topics[:min(20, len(topics))]
        
        for i in range(0, len(topics_to_show), 2):
            row = []
            # Добавляем первую кнопку в ряду
            topic_text = f"{i+1}. {topics_to_show[i]}"
            if len(topic_text) > 40:  # Ограничиваем длину текста кнопки
                topic_text = topic_text[:37] + "..."
            row.append(InlineKeyboardButton(topic_text, callback_data=f'topic_{i+1}'))
            
            # Добавляем вторую кнопку, если она есть
            if i + 1 < len(topics_to_show):
                topic_text = f"{i+2}. {topics_to_show[i+1]}"
                if len(topic_text) > 40:
                    topic_text = topic_text[:37] + "..."
                row.append(InlineKeyboardButton(topic_text, callback_data=f'topic_{i+2}'))
            
            keyboard.append(row)
            
        # Добавляем кнопки меню внизу
        keyboard.append([InlineKeyboardButton("🔄 Больше тем", callback_data='more_topics')])
        keyboard.append([InlineKeyboardButton("✏️ Своя тема", callback_data='custom_topic')])
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')])
        
        return InlineKeyboardMarkup(keyboard)

class UIManager:
    """Класс для управления пользовательским интерфейсом"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def main_menu(self):
        """
        Создает главное меню в виде кнопок.

        Returns:
            InlineKeyboardMarkup: Клавиатура с кнопками меню
        """
        keyboard = [
            [InlineKeyboardButton("🔍 Выбрать тему", callback_data='topic')],
            [InlineKeyboardButton("✅ Пройти тест", callback_data='test')],
            [InlineKeyboardButton("💬 Беседа о истории России", callback_data='conversation')],
            [InlineKeyboardButton("ℹ️ Информация о проекте", callback_data='project_info')],
            [InlineKeyboardButton("❌ Завершить", callback_data='cancel')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
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
                # Ограничиваем длину темы в кнопке
                display_topic = topic[:30] + '...' if len(topic) > 30 else topic
                keyboard.append([InlineKeyboardButton(f"{i}. {display_topic}", callback_data=f'topic_{i}')])
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
