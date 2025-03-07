
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
        # Запрашиваем набор из 20 вопросов у API с очень четким форматированием
        prompt = f"""Создай 20 вопросов для тестирования по теме '{topic}'. 
Строго следуй следующему формату для каждого вопроса:

Вопрос N: [Текст вопроса]
1) [Вариант ответа 1]
2) [Вариант ответа 2]
3) [Вариант ответа 3]
4) [Вариант ответа 4]
Правильный ответ: [число от 1 до 4]

Где N - номер вопроса (от 1 до 20).
Каждый вопрос ДОЛЖЕН иметь ровно 4 варианта ответа.
Каждый вариант ответа ДОЛЖЕН начинаться с цифры и символа ')'.
После каждого набора вариантов ДОЛЖЕН быть указан правильный ответ в формате 'Правильный ответ: X', где X - число от 1 до 4.
НЕ ИСПОЛЬЗУЙ символы форматирования Markdown (* _ ` и т.д.)."""

        response = self.api_client.ask_grok(prompt, use_cache=False)
        
        # Разделяем текст на вопросы по паттерну "Вопрос N:" или просто по пустым строкам
        raw_questions = re.split(r'(?:\n\s*\n)|(?:\nВопрос \d+:)', response)
        
        processed_questions = []
        
        for q in raw_questions:
            q = q.strip()
            # Проверяем, что строка достаточно длинная и содержит вопрос
            if q and len(q) > 10 and ('?' in q or 'вопрос' in q.lower()):
                # Проверяем, есть ли варианты ответов в формате "1) ..."
                has_options = bool(re.search(r'\n\s*\d\)\s+', q))
                
                if has_options:
                    # Убеждаемся, что есть все 4 варианта
                    options_count = len(re.findall(r'\n\s*\d\)\s+', q))
                    if options_count >= 4:
                        # Проверяем, есть ли правильный ответ
                        if not re.search(r'Правильный ответ:\s*[1-4]', q):
                            # Если нет, добавляем случайный
                            correct_answer = random.randint(1, 4)
                            q += f"\nПравильный ответ: {correct_answer}"
                        
                        # Экранируем специальные символы Markdown
                        sanitized_q = q.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                        sanitized_q = sanitized_q.replace('[', '\\[').replace(']', '\\]')
                        sanitized_q = sanitized_q.replace('(', '\\(').replace(')', '\\)')
                        
                        processed_questions.append(sanitized_q)
                else:
                    # Если вариантов нет, формируем их искусственно
                    main_text = q.split('\n')[0] if '\n' in q else q
                    artificial_q = f"{main_text}\n"
                    artificial_q += "1) Первый вариант ответа\n"
                    artificial_q += "2) Второй вариант ответа\n"
                    artificial_q += "3) Третий вариант ответа\n"
                    artificial_q += "4) Четвертый вариант ответа\n"
                    artificial_q += f"Правильный ответ: {random.randint(1, 4)}"
                    
                    # Экранируем специальные символы Markdown
                    sanitized_q = artificial_q.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                    sanitized_q = sanitized_q.replace('[', '\\[').replace(']', '\\]')
                    sanitized_q = sanitized_q.replace('(', '\\(').replace(')', '\\)')
                    
                    processed_questions.append(sanitized_q)
        
        # Ограничиваем количество вопросов до 20
        processed_questions = processed_questions[:20]
        
        # Если вопросов меньше 20, добавляем дополнительные
        while len(processed_questions) < 20:
            q_num = len(processed_questions) + 1
            artificial_q = f"Вопрос {q_num}: Дополнительный вопрос по теме '{topic}'?\n"
            artificial_q += "1) Первый вариант ответа\n"
            artificial_q += "2) Второй вариант ответа\n"
            artificial_q += "3) Третий вариант ответа\n"
            artificial_q += "4) Четвертый вариант ответа\n"
            artificial_q += f"Правильный ответ: {random.randint(1, 4)}"
            processed_questions.append(artificial_q)
        
        # Создаем версию для отображения без правильных ответов
        display_questions = []
        for q in processed_questions:
            display_q = re.sub(r'Правильный ответ:\s*\d+', '', q).strip()
            display_questions.append(display_q)
        
        return {
            "original_questions": processed_questions,
            "display_questions": display_questions
        }
    
    def format_question_text(self, question_text):
        """
        Форматирует текст вопроса для отображения
        
        Args:
            question_text (str): Текст вопроса
            
        Returns:
            dict: Словарь с основным вопросом и вариантами ответов
        """
        self.logger.info(f"Форматирование вопроса: {question_text[:50]}...")
        
        # Удаляем строки с правильным ответом из отображаемого текста
        question_text = re.sub(r'Правильный ответ:\s*\d+', '', question_text).strip()
        
        # Выделяем основной вопрос и варианты ответов
        lines = question_text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        # Находим главный вопрос (строка с вопросительным знаком или первая строка)
        main_question = ""
        for line in cleaned_lines:
            if '?' in line:
                main_question = line
                break
        
        # Если вопрос не найден, берем первую строку
        if not main_question and cleaned_lines:
            main_question = cleaned_lines[0]
        
        # Ищем варианты ответов с помощью регулярных выражений
        option_pattern = r'(\d)\s*[\)\.]?\s+(.*)'
        letter_pattern = r'([A-D])\s*[\)\.]?\s+(.*)'
        
        options = []
        option_lines = []
        
        # Сначала проверяем стандартный формат с новой строки "1) Вариант"
        for line in question_text.split('\n'):
            line = line.strip()
            match_num = re.match(option_pattern, line)
            match_letter = re.match(letter_pattern, line)
            
            if match_num:
                number = match_num.group(1)
                text = match_num.group(2).strip()
                option_lines.append((int(number), text))
            elif match_letter:
                letter = match_letter.group(1)
                number = ord(letter) - ord('A') + 1
                text = match_letter.group(2).strip()
                option_lines.append((number, text))
        
        # Если нашли хотя бы 2 варианта ответа в ожидаемом формате
        if len(option_lines) >= 2:
            # Сортируем варианты по номеру
            option_lines.sort(key=lambda x: x[0])
            # Формируем список вариантов
            for number, text in option_lines:
                if 1 <= number <= 4:  # Проверяем, что номер в диапазоне 1-4
                    options.append(f"{number}) {text}")
        
        # Если варианты не найдены, ищем их в тексте более агрессивно
        if not options:
            # Ищем строки после вопроса, которые могут быть вариантами
            option_texts = re.findall(r'\n\s*\d[\)\.]?\s+.*|\n\s*[A-D][\)\.]?\s+.*', question_text)
            
            if option_texts:
                for i, opt in enumerate(option_texts[:4]):
                    opt = opt.strip()
                    match_num = re.match(option_pattern, opt)
                    match_letter = re.match(letter_pattern, opt)
                    
                    if match_num:
                        number = int(match_num.group(1))
                        text = match_num.group(2).strip()
                        options.append(f"{number}) {text}")
                    elif match_letter:
                        letter = match_letter.group(1)
                        number = ord(letter) - ord('A') + 1
                        text = match_letter.group(2).strip()
                        options.append(f"{number}) {text}")
                    else:
                        # Если формат не распознан, используем порядковый номер
                        options.append(f"{i+1}) {opt}")
        
        # Если варианты всё ещё не найдены, создаем стандартные варианты
        if not options:
            self.logger.warning(f"Варианты ответов не найдены в вопросе. Создаю стандартные варианты.")
            options = [
                "1) Первый вариант ответа",
                "2) Второй вариант ответа",
                "3) Третий вариант ответа",
                "4) Четвертый вариант ответа"
            ]
        
        # Убеждаемся, что у нас ровно 4 варианта ответа
        while len(options) < 4:
            options.append(f"{len(options) + 1}) Дополнительный вариант ответа")
        
        # Ограничиваем до 4 вариантов
        options = options[:4]
        
        # Убеждаемся, что все варианты имеют правильный формат "номер) текст"
        for i in range(len(options)):
            if not re.match(r'^\d\)', options[i]):
                options[i] = f"{i+1}) {options[i]}"
                
        self.logger.info(f"Сформированы варианты: {len(options)} вариантов")
        
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
            similar_topics_text = api_client.ask_grok(prompt, use_cache=True)

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
