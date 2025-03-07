
import re
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TestService:
    """Класс для работы с тестами по истории России"""

    def __init__(self, api_client, logger):
        """
        Инициализация сервиса тестирования
        
        Args:
            api_client: Клиент API для получения данных
            logger: Логгер для записи действий
        """
        self.api_client = api_client
        self.logger = logger

    def generate_test(self, topic):
        """
        Генерирует тест по заданной теме.
        
        Args:
            topic (str): Тема для теста
            
        Returns:
            dict: Данные теста с вопросами
        """
        # Запрашиваем простой набор вопросов у API
        prompt = f"Создай 5 простых вопросов для тестирования по теме '{topic}'. Каждый вопрос должен иметь 4 варианта ответа (1-4) и обязательно указанный правильный ответ в формате 'Правильный ответ: X'. Пронумеруй вопросы. НЕ ИСПОЛЬЗУЙ символы форматирования Markdown (* _ ` и т.д.)."
        response = self.api_client.ask_grok(prompt, use_cache=False)
        
        # Разделяем текст на вопросы, используя либо пустые строки, либо номера
        raw_questions = re.split(r'\n\s*\n|\n\d+[\.\)]\s+', response)
        original_questions = []
        display_questions = []
        
        for q in raw_questions:
            q = q.strip()
            if q and len(q) > 10 and ('?' in q or 'Вопрос' in q):
                # Удаляем начальные цифры, если они есть
                q = re.sub(r'^(\d+[\.\)]|\d+\.)\s*', '', q).strip()
                original_questions.append(q)
                
                # Создаем версию для отображения (без правильного ответа)
                display_q = re.sub(r'Правильный ответ:\s*\d+', '', q).strip()
                display_questions.append(display_q)
                
        # Очищаем все вопросы от символов форматирования Markdown
        sanitized_questions = []
        for q in original_questions:
            # Экранируем специальные символы Markdown
            sanitized_q = q.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
            sanitized_q = sanitized_q.replace('[', '\\[').replace(']', '\\]')
            sanitized_q = sanitized_q.replace('(', '\\(').replace(')', '\\)')
            sanitized_questions.append(sanitized_q)
        
        # Валидация данных: проверяем наличие правильных ответов
        valid_test = False
        for question in sanitized_questions:
            if re.search(r"Правильный ответ:\s*[1-4]", question):
                valid_test = True
                break
        
        if not valid_test:
            # Если правильных ответов нет, добавим их автоматически
            self.logger.warning("В вопросах не найдены правильные ответы, добавляем их")
            
            new_questions = []
            for i, q in enumerate(sanitized_questions):
                # Добавляем правильный ответ к каждому вопросу, если его нет
                if not re.search(r"Правильный ответ:", q):
                    # Выбираем случайное число от 1 до 4
                    correct_answer = random.randint(1, 4)
                    q += f"\nПравильный ответ: {correct_answer}"
                new_questions.append(q)
            
            sanitized_questions = new_questions
        
        return {
            "original_questions": sanitized_questions,
            "display_questions": sanitized_questions
        }
    
    def format_question_text(self, question_text):
        """
        Форматирует текст вопроса для отображения
        
        Args:
            question_text (str): Текст вопроса
            
        Returns:
            dict: Словарь с основным вопросом и вариантами ответов
        """
        # Удаляем строки с правильным ответом из отображаемого текста
        question_text = re.sub(r'Правильный ответ:\s*\d+', '', question_text).strip()
        
        # Выделяем основной вопрос и варианты ответов
        lines = question_text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        # Находим вопрос (строка с вопросительным знаком или первая строка)
        main_question = ""
        for line in cleaned_lines:
            if '?' in line:
                main_question = line
                break
        
        # Если вопрос не найден, берем первую строку
        if not main_question and cleaned_lines:
            main_question = cleaned_lines[0]
            
        # Ищем варианты ответов
        options = []
        
        # Сначала ищем стандартные форматы вариантов ответов (цифра с точкой или скобкой)
        for line in cleaned_lines:
            # Пропускаем строку с вопросом
            if line == main_question:
                continue
                
            # Проверяем разные форматы: 1) текст, 1. текст, A) текст, A. текст
            if re.match(r'^\d[\)\.]\s+', line) or re.match(r'^[A-D][\)\.]\s+', line):
                # Преобразуем буквенные варианты в цифровые (A → 1, B → 2, etc.)
                if re.match(r'^[A-D][\)\.]\s+', line):
                    letter = line[0]
                    number = ord(letter) - ord('A') + 1
                    text = line[2:].strip() if len(line) > 2 else f"Вариант {number}"
                    options.append(f"{number}) {text}")
                else:
                    options.append(line)
        
        # Если стандартные варианты не найдены, пытаемся распознать другие форматы
        if not options:
            # Рассматриваем каждую строку после вопроса как потенциальный вариант ответа
            option_index = 0
            for i, line in enumerate(cleaned_lines):
                if line == main_question:
                    option_index = i + 1
                    break
            
            # Берем до 4-х строк после вопроса как варианты ответов
            for i in range(option_index, min(option_index + 4, len(cleaned_lines))):
                if i < len(cleaned_lines):
                    options.append(f"{i - option_index + 1}) {cleaned_lines[i]}")
        
        # Если всё еще нет вариантов или их меньше 4, добавляем заполнители
        if len(options) < 4:
            for i in range(len(options), 4):
                options.append(f"{i+1}) Вариант ответа {i+1}")
                
        return {
            "main_question": main_question,
            "options": options
        }
    
    def parse_correct_answer(self, question_text):
        """
        Извлекает правильный ответ из текста вопроса
        
        Args:
            question_text (str): Текст вопроса
        
        Returns:
            str: Номер правильного ответа или None если не найден
        """
        # Поиск с более гибким регулярным выражением
        patterns = [
            r"Правильный ответ:\s*(\d+)",
            r"Правильный:\s*(\d+)",
            r"Ответ:\s*(\d+)",
            r"Верный ответ:\s*(\d+)"
        ]
        
        for pattern in patterns:
            correct_answer_match = re.search(pattern, question_text)
            if correct_answer_match:
                return correct_answer_match.group(1)
                
        # Попытка найти правильный ответ в конце текста
        lines = question_text.split('\n')
        for line in reversed(lines):
            if re.search(r"\d+", line):
                match = re.search(r"\d+", line)
                if match:
                    return match.group(0)
        
        return None
    
    def recommend_similar_topics(self, current_topic, api_client):
        """
        Рекомендует похожие темы на основе текущей темы
        
        Args:
            current_topic (str): Текущая тема
            api_client: Клиент API для запроса данных
        
        Returns:
            list: Список рекомендованных тем
        """
        try:
            # Формируем запрос на рекомендацию
            prompt = f"На основе темы '{current_topic}' предложи 3 связанные темы по истории России, которые могут заинтересовать пользователя. Перечисли их в формате нумерованного списка без дополнительных пояснений."

            # Получаем ответ от API
            similar_topics_text = api_client.ask_grok(prompt, max_tokens=150, temp=0.4)

            # Парсим темы
            similar_topics = []
            for line in similar_topics_text.split('\n'):
                # Ищем строки с форматом "1. Тема" или "- Тема"
                if (line.strip().startswith(('1.', '2.', '3.', '-'))):
                    # Удаляем префикс и лишние пробелы
                    topic = re.sub(r'^[\d\.\-\s]+', '', line).strip()
                    if topic:
                        similar_topics.append(topic)

            return similar_topics[:3]  # Возвращаем максимум 3 темы
        except Exception as e:
            self.logger.warning(f"Не удалось сгенерировать похожие темы: {e}")
            return []
