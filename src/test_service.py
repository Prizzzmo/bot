
import re
import random
import time
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.base_service import BaseService

class TestService(BaseService):
    """Сервис для работы с тестами по истории"""

    def __init__(self, api_client, logger):
        super().__init__(logger)
        self.api_client = api_client
        self.topic_facts_cache = {}  # Кэш фактов по темам для разнообразия ответов

    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.

        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            if not self.api_client:
                self._logger.error("API клиент не указан")
                return False
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при инициализации TestService: {e}")
            return False

    def _get_topic_facts(self, topic):
        """
        Получает факты по теме для создания разнообразных вариантов ответов.
        
        Args:
            topic (str): Тема
            
        Returns:
            list: Список фактов по теме
        """
        if topic in self.topic_facts_cache:
            return self.topic_facts_cache[topic]
            
        prompt = f"""Предоставь 30 исторических фактов по теме "{topic}" в формате JSON. 
Каждый факт должен быть лаконичным и содержать конкретную историческую информацию.
Структура: [
  {{"факт": "Конкретный исторический факт 1"}},
  {{"факт": "Конкретный исторический факт 2"}},
  ...
]
Факты должны затрагивать разные аспекты темы: события, личности, даты, места, последствия.
"""
        try:
            response = self.api_client.ask_grok(prompt, use_cache=True)
            # Извлекаем JSON из ответа
            json_pattern = r'\[\s*\{.*\}\s*\]'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            facts = []
            if json_match:
                try:
                    facts_json = json_match.group(0)
                    facts_data = json.loads(facts_json)
                    facts = [item.get("факт", "") for item in facts_data if item.get("факт")]
                except json.JSONDecodeError:
                    self._logger.warning(f"Не удалось разобрать JSON с фактами для темы '{topic}'")
            
            # Если не удалось получить факты через JSON, пробуем простой подход
            if not facts:
                # Извлекаем факты из обычного текста
                facts = []
                for line in response.split('\n'):
                    line = line.strip()
                    if line and len(line) > 15 and not line.startswith(('[', ']', '{', '}')):
                        # Убираем номера, маркеры списка и т.д.
                        clean_line = re.sub(r'^[\d\.\-\*]+\s*', '', line)
                        if clean_line and len(clean_line) > 15:
                            facts.append(clean_line)
            
            # Сохраняем в кэш
            self.topic_facts_cache[topic] = facts
            return facts
            
        except Exception as e:
            self._logger.error(f"Ошибка при получении фактов по теме '{topic}': {e}")
            return []

    def _generate_diverse_options(self, topic, correct_answer, question_type, question_context):
        """
        Генерирует разнообразные варианты ответов на основе типа вопроса.
        
        Args:
            topic (str): Тема теста
            correct_answer (str): Правильный ответ
            question_type (str): Тип вопроса (дата, личность, место, причина, результат, общий)
            question_context (str): Контекст вопроса
            
        Returns:
            list: Список из 4 вариантов ответов (включая правильный)
        """
        all_options = [correct_answer]
        facts = self._get_topic_facts(topic)
        
        # Определяем характер правильного ответа для генерации похожих вариантов
        is_year = bool(re.search(r'\b\d{3,4}\s*(?:год|г\.)\b', correct_answer, re.IGNORECASE))
        is_person = bool(re.search(r'[А-Я][а-я]+\s+[А-Я][а-я]+(?:\s+[А-Я][а-я]+)?', correct_answer))
        has_numbers = bool(re.search(r'\d+', correct_answer))
        
        # Специализированные опции по типу вопроса
        if is_year or question_type == "дата":
            # Для дат - генерируем близкие даты
            match = re.search(r'(\d{3,4})', correct_answer)
            if match:
                year = int(match.group(1))
                wrong_years = []
                # Генерируем годы в пределах ±50 лет, но не совпадающие с правильным
                for _ in range(10):  # генерируем больше, чем нужно, для разнообразия
                    offset = random.randint(-50, 50)
                    if offset != 0:
                        wrong_year = year + offset
                        if 800 <= wrong_year <= 2023:  # исторически релевантный диапазон
                            year_str = f"{wrong_year} год"
                            if year_str not in all_options:
                                wrong_years.append(year_str)
                
                # Добавляем сгенерированные годы
                for wrong_year in wrong_years[:3]:  # берем только 3 ошибочных варианта
                    if len(all_options) < 4:
                        all_options.append(wrong_year)
        
        elif is_person or question_type == "личность":
            # Для личностей - используем исторических деятелей из аналогичного периода
            historical_figures = [
                "Пётр I", "Екатерина II", "Александр I", "Николай II", 
                "Иван Грозный", "Александр II", "Елизавета Петровна", "Александр III",
                "А.В. Суворов", "М.И. Кутузов", "Г.К. Жуков", "К.К. Рокоссовский",
                "П.А. Румянцев", "М.Д. Скобелев", "А.М. Василевский", "И.С. Конев",
                "П.А. Столыпин", "С.Ю. Витте", "В.И. Ленин", "И.В. Сталин",
                "Н.С. Хрущёв", "Л.И. Брежнев", "М.С. Горбачёв", "Б.Н. Ельцин"
            ]
            
            random.shuffle(historical_figures)
            for figure in historical_figures:
                if figure not in all_options and len(all_options) < 4:
                    all_options.append(figure)
        
        elif question_type == "место":
            # Для мест - используем исторически значимые города и места
            places = [
                "Москва", "Санкт-Петербург", "Новгород", "Киев", "Казань", 
                "Севастополь", "Владивосток", "Архангельск", "Смоленск", 
                "Бородино", "Полтава", "Сталинград", "Куликово поле",
                "Ленинград", "Нижний Новгород", "Владимир", "Ярославль", 
                "Астрахань", "Азов", "Курск", "Псков", "Рязань"
            ]
            
            random.shuffle(places)
            for place in places:
                if place not in all_options and len(all_options) < 4:
                    all_options.append(place)
        
        # Если специализированные опции не заполнили 4 варианта, добавляем из фактов
        while len(all_options) < 4 and facts:
            # Выбираем случайные факты и делаем из них варианты ответов
            fact = random.choice(facts)
            facts.remove(fact)
            
            # Извлекаем короткую значимую часть факта (не более 70 символов)
            if len(fact) > 70:
                words = fact.split()
                shortened_fact = ""
                for word in words:
                    if len(shortened_fact + word) < 70:
                        shortened_fact += word + " "
                    else:
                        break
                fact = shortened_fact.strip()
            
            if fact and fact not in all_options:
                all_options.append(fact)
        
        # Если всё ещё не хватает вариантов, добавляем общие варианты
        general_options = [
            f"Ранний этап в истории {topic}",
            f"Заключительный период {topic}",
            f"Важный поворотный момент в {topic}",
            f"Решающее событие {topic}",
            f"Второстепенный аспект {topic}",
            f"Ключевой документ в истории {topic}",
            f"Основное последствие {topic}",
            f"Внешнеполитический фактор {topic}",
            f"Реформа, не связанная с {topic}",
            f"Побочный результат {topic}"
        ]
        
        random.shuffle(general_options)
        for option in general_options:
            if option not in all_options and len(all_options) < 4:
                all_options.append(option)
        
        # Перемешиваем варианты ответов, чтобы правильный был не всегда первым
        random.shuffle(all_options)
        
        # Убеждаемся, что у нас ровно 4 варианта
        return all_options[:4]

    def generate_test(self, topic):
        """
        Генерирует тест по заданной теме с гарантированно разными вариантами ответов.

        Args:
            topic (str): Тема для теста

        Returns:
            dict: Данные теста с вопросами
        """
        # Запрашиваем набор из 20 вопросов у API с очень четким форматированием
        prompt = f"""Создай ровно 20 вопросов для тестирования по теме '{topic}'. 
Сосредоточься ТОЛЬКО на вопросе и правильном ответе. 
Строго следуй формату для каждого вопроса:

Вопрос: [Текст вопроса по теме '{topic}']
Правильный ответ: [Короткий однозначный ответ]

ВАЖНО:
1. Правильный ответ должен быть кратким и содержательным - факт, имя, дата, термин, событие.
2. НЕ указывай варианты ответов - они будут сгенерированы отдельно.
3. Вопросы должны быть разнообразными и охватывать разные аспекты темы.
4. НЕ ИСПОЛЬЗУЙ символы форматирования Markdown (* _ ` и т.д.).
5. Для вопросов о датах указывай полный год (например, "1812 год").
6. Не делай нумерацию вопросов. Каждый вопрос начинай со слова "Вопрос:".

Пример:
Вопрос: В каком году произошло Крещение Руси?
Правильный ответ: 988 год

Вопрос: Кто возглавлял русскую армию в Бородинском сражении?
Правильный ответ: М.И. Кутузов"""

        # Запрашиваем вопросы из API
        response = self.api_client.ask_grok(prompt, use_cache=False)

        # Извлекаем вопросы и ответы из текста
        questions_data = []
        raw_questions = response.split("Вопрос:")
        
        for raw_q in raw_questions:
            if not raw_q.strip():
                continue
                
            q_text = "Вопрос: " + raw_q.strip()
            
            # Извлекаем правильный ответ
            answer_match = re.search(r'Правильный ответ:\s*(.*?)(?:\n|$)', q_text)
            if answer_match:
                correct_answer = answer_match.group(1).strip()
                question_text = re.sub(r'Правильный ответ:\s*.*?(?:\n|$)', '', q_text).strip()
                
                # Определяем тип вопроса для генерации релевантных вариантов
                question_type = "общий"
                question_text_lower = question_text.lower()
                
                if 'год' in question_text_lower or 'дат' in question_text_lower or 'когда' in question_text_lower:
                    question_type = "дата"
                elif 'кто' in question_text_lower or 'личност' in question_text_lower or 'правитель' in question_text_lower:
                    question_type = "личность"
                elif 'где' in question_text_lower or 'мест' in question_text_lower or 'территор' in question_text_lower:
                    question_type = "место"
                elif 'причин' in question_text_lower or 'почему' in question_text_lower:
                    question_type = "причина"
                elif 'результат' in question_text_lower or 'последств' in question_text_lower or 'итог' in question_text_lower:
                    question_type = "результат"
                
                # Добавляем вопрос с правильным ответом
                questions_data.append({
                    "question": question_text,
                    "correct_answer": correct_answer,
                    "type": question_type
                })
        
        # Ограничиваем до 20 вопросов
        questions_data = questions_data[:20]
        
        # Если получили менее 20 вопросов, запрашиваем дополнительно
        if len(questions_data) < 20:
            additional_count = 20 - len(questions_data)
            self._logger.info(f"Получено только {len(questions_data)} вопросов, запрашиваем еще {additional_count}")
            
            additional_prompt = f"""Создай ровно {additional_count} вопросов для тестирования по теме '{topic}'. 
Следуй тому же формату, что и раньше:

Вопрос: [Текст вопроса]
Правильный ответ: [Короткий однозначный ответ]

ВАЖНО: Генерируй только КОНКРЕТНЫЕ и СОДЕРЖАТЕЛЬНЫЕ вопросы с реальными правильными ответами.
"""
            
            additional_response = self.api_client.ask_grok(additional_prompt, use_cache=False)
            
            # Обрабатываем дополнительные вопросы
            raw_additional = additional_response.split("Вопрос:")
            for raw_q in raw_additional:
                if not raw_q.strip() or len(questions_data) >= 20:
                    continue
                    
                q_text = "Вопрос: " + raw_q.strip()
                
                # Извлекаем правильный ответ
                answer_match = re.search(r'Правильный ответ:\s*(.*?)(?:\n|$)', q_text)
                if answer_match:
                    correct_answer = answer_match.group(1).strip()
                    question_text = re.sub(r'Правильный ответ:\s*.*?(?:\n|$)', '', q_text).strip()
                    
                    # Определяем тип вопроса
                    question_type = "общий"
                    question_text_lower = question_text.lower()
                    
                    if 'год' in question_text_lower or 'дат' in question_text_lower or 'когда' in question_text_lower:
                        question_type = "дата"
                    elif 'кто' in question_text_lower or 'личност' in question_text_lower or 'правитель' in question_text_lower:
                        question_type = "личность"
                    elif 'где' in question_text_lower or 'мест' in question_text_lower or 'территор' in question_text_lower:
                        question_type = "место"
                    elif 'причин' in question_text_lower or 'почему' in question_text_lower:
                        question_type = "причина"
                    elif 'результат' in question_text_lower or 'последств' in question_text_lower or 'итог' in question_text_lower:
                        question_type = "результат"
                    
                    # Добавляем вопрос с правильным ответом
                    questions_data.append({
                        "question": question_text,
                        "correct_answer": correct_answer,
                        "type": question_type
                    })
        
        # Формируем финальный тест с вариантами ответов
        processed_questions = []
        display_questions = []
        
        for q_data in questions_data[:20]:  # Garantee max 20 questions
            question = q_data["question"]
            correct_answer = q_data["correct_answer"]
            question_type = q_data["type"]
            
            # Генерируем уникальные варианты ответов для этого вопроса
            options = self._generate_diverse_options(
                topic, 
                correct_answer, 
                question_type, 
                question
            )
            
            # Определяем индекс правильного ответа
            correct_index = options.index(correct_answer) + 1
            
            # Форматируем вопрос с вариантами для отображения
            formatted_question = f"{question}\n"
            for i, option in enumerate(options, 1):
                formatted_question += f"{i}) {option}\n"
            formatted_question += f"Правильный ответ: {correct_index}"
            
            # Для отображения - без правильного ответа
            display_question = f"{question}\n"
            for i, option in enumerate(options, 1):
                display_question += f"{i}) {option}\n"
            
            processed_questions.append(formatted_question)
            display_questions.append(display_question)
        
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
        self._logger.info(f"Форматирование вопроса: {question_text[:50]}...")

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

        # Если в первой строке нет "Вопрос:", добавляем это
        if not re.search(r'Вопрос\s*\d*\s*:', main_question, re.IGNORECASE) and not main_question.strip().endswith('?'):
            main_question = f"Вопрос: {main_question}"

        # Ищем варианты ответов с помощью регулярных выражений
        option_pattern = r'(\d)\s*[\)\.]?\s+(.*)'
        options = []

        # Ищем строки с форматом "1) Вариант"
        for line in question_text.split('\n'):
            line = line.strip()
            match = re.match(option_pattern, line)
            if match:
                number = match.group(1)
                text = match.group(2).strip()
                options.append(f"{number}) {text}")

        self._logger.info(f"Сформированы варианты: {len(options)} вариантов")

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
            self._logger.warning(f"Не удалось сгенерировать похожие темы: {e}")
            return []
