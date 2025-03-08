import re
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.base_service import BaseService

class TestService(BaseService):
    """Сервис для работы с тестами по истории"""

    def __init__(self, api_client, logger):
        super().__init__(logger)
        self.api_client = api_client

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
1) [Конкретный вариант ответа 1, строго по теме]
2) [Конкретный вариант ответа 2, строго по теме]
3) [Конкретный вариант ответа 3, строго по теме]
4) [Конкретный вариант ответа 4, строго по теме]
Правильный ответ: [число от 1 до 4]

Важно:
1. Варианты ответов ВСЕГДА должны быть конкретными и содержательными по теме '{topic}'.
2. НИКОГДА не используй шаблонные фразы типа "Первый вариант ответа" или "Ответ 1".
3. Каждый вариант должен быть логичным и реалистичным в контексте вопроса.
4. Варианты должны быть примерно одинаковой длины.
5. НЕ ИСПОЛЬЗУЙ символы форматирования Markdown (* _ ` и т.д.).
6. Кратко формулируй варианты для лучшего визуального восприятия.

Например:
Вопрос: В каком году произошло Крещение Руси?
1) 988 год
2) 980 год
3) 1054 год
4) 1147 год
Правильный ответ: 1"""

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

                        # Проверяем, нет ли шаблонных ответов
                        if not re.search(r'\d\)\s+(Первый|Второй|Третий|Четвертый) вариант ответа', q, re.IGNORECASE) and \
                           not re.search(r'\d\)\s+Вариант \d+', q, re.IGNORECASE) and \
                           not re.search(r'\d\)\s+Ответ \d+', q, re.IGNORECASE):
                            processed_questions.append(sanitized_q)
                        else:
                            # Если есть шаблонные ответы, пропускаем этот вопрос
                            self.logger.warning(f"Пропуск вопроса с шаблонными ответами: {q[:50]}...")
                            continue
                    else:
                        # Недостаточное количество вариантов, пропускаем
                        self.logger.warning(f"Пропуск вопроса с недостаточным количеством вариантов: {q[:50]}...")
                        continue
                else:
                    # Пропускаем вопросы без вариантов ответов
                    self.logger.warning(f"Пропуск вопроса без вариантов ответов: {q[:50]}...")
                    continue

        # Если после обработки осталось менее 10 вопросов, запрашиваем еще вопросы
        attempts = 0
        while len(processed_questions) < 15 and attempts < 3:
            self.logger.info(f"Недостаточно вопросов ({len(processed_questions)}), запрашиваем еще")
            attempts += 1

            additional_prompt = f"""Создай еще 10 вопросов для тестирования по теме '{topic}'. 
Строго следуй следующему формату и указаниям:

Вопрос: [Текст вопроса]
1) [Конкретный вариант ответа, связанный с темой '{topic}']
2) [Конкретный вариант ответа, связанный с темой '{topic}']
3) [Конкретный вариант ответа, связанный с темой '{topic}']
4) [Конкретный вариант ответа, связанный с темой '{topic}']
Правильный ответ: [число от 1 до 4]

ОБЯЗАТЕЛЬНО: все варианты ответов должны быть СОДЕРЖАТЕЛЬНЫМИ и КОНКРЕТНЫМИ, а не абстрактными."""

            additional_response = self.api_client.ask_grok(additional_prompt, use_cache=False)
            # Обрабатываем дополнительные вопросы так же, как основные
            additional_raw_questions = re.split(r'(?:\n\s*\n)|(?:\nВопрос \d*:?)', additional_response)

            for q in additional_raw_questions:
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

                            # Проверяем, нет ли шаблонных ответов
                            if not re.search(r'\d\)\s+(Первый|Второй|Третий|Четвертый) вариант ответа', q, re.IGNORECASE) and \
                               not re.search(r'\d\)\s+Вариант \d+', q, re.IGNORECASE) and \
                               not re.search(r'\d\)\s+Ответ \d+', q, re.IGNORECASE):
                                processed_questions.append(sanitized_q)

        # Если по-прежнему меньше 20 вопросов, генерируем только недостающее количество качественных вопросов
        if len(processed_questions) < 20:
            # Теперь запрашиваем только точное число нужных вопросов
            needed_questions = 20 - len(processed_questions)
            self.logger.info(f"Генерация еще {needed_questions} вопросов для достижения 20")

            final_prompt = f"""Создай ровно {needed_questions} вопросов для тестирования по теме '{topic}'. 
Это ОЧЕНЬ ВАЖНО - каждый вопрос и ответ должен быть максимально конкретным и содержательным.

Строго следуй формату:
Вопрос: [Конкретный вопрос по теме]
1) [Конкретный ответ]
2) [Конкретный ответ]
3) [Конкретный ответ]
4) [Конкретный ответ]
Правильный ответ: [число от 1 до 4]

ЗАПРЕЩЕНО использовать в вариантах ответов фразы типа:
- "Первый вариант ответа"
- "Второй вариант ответа"
- "Ответ №1", "Ответ 2"
- "Вариант 1", "Вариант 2"

Каждый вариант ответа должен напрямую относиться к теме и содержать конкретную информацию."""

            final_response = self.api_client.ask_grok(final_prompt, use_cache=False)
            final_questions = re.split(r'(?:\n\s*\n)|(?:\nВопрос \d*:?)', final_response)

            for q in final_questions:
                q = q.strip()
                # Стандартные проверки и форматирование
                if q and len(q) > 10 and '?' in q and re.search(r'\n\s*\d\)\s+', q):
                    options_count = len(re.findall(r'\n\s*\d\)\s+', q))
                    if options_count >= 4:
                        if not re.search(r'Правильный ответ:\s*[1-4]', q):
                            correct_answer = random.randint(1, 4)
                            q += f"\nПравильный ответ: {correct_answer}"

                        sanitized_q = q.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                        sanitized_q = sanitized_q.replace('[', '\\[').replace(']', '\\]')
                        sanitized_q = sanitized_q.replace('(', '\\(').replace(')', '\\)')

                        # Строгая проверка на шаблонные ответы
                        if not re.search(r'\d\)\s+(Первый|Второй|Третий|Четвертый) вариант', q, re.IGNORECASE) and \
                           not re.search(r'\d\)\s+Вариант \d+', q, re.IGNORECASE) and \
                           not re.search(r'\d\)\s+Ответ \d+', q, re.IGNORECASE):
                            if len(processed_questions) < 20:
                                processed_questions.append(sanitized_q)

        # Ограничиваем количество вопросов до 20
        processed_questions = processed_questions[:20]

        # Если вопросов все еще менее 20, добавляем специально составленные резервные вопросы
        reserve_questions = [
            f"Какой период истории России относится к теме '{topic}'?\n1) IX-X века\n2) XI-XII века\n3) XIII-XV века\n4) XVI-XVII века\nПравильный ответ: {random.randint(1, 4)}",
            f"Какое историческое событие связано с темой '{topic}'?\n1) Куликовская битва\n2) Отечественная война 1812 года\n3) Крещение Руси\n4) Октябрьская революция\nПравильный ответ: {random.randint(1, 4)}",
            f"Какой исторический деятель внес значительный вклад в развитие темы '{topic}'?\n1) Петр I\n2) Екатерина II\n3) Александр II\n4) Владимир Ленин\nПравильный ответ: {random.randint(1, 4)}",
            f"Какое из этих событий произошло в период, связанный с темой '{topic}'?\n1) Смутное время\n2) Дворцовые перевороты\n3) Великая Отечественная война\n4) Перестройка\nПравильный ответ: {random.randint(1, 4)}",
            f"Какой документ имеет историческое значение для темы '{topic}'?\n1) Русская Правда\n2) Соборное уложение 1649 года\n3) Конституция СССР 1936 года\n4) Манифест об отмене крепостного права\nПравильный ответ: {random.randint(1, 4)}"
        ]

        while len(processed_questions) < 20:
            reserve_index = len(processed_questions) - 15  # Выбираем резервный вопрос по порядку
            if reserve_index < len(reserve_questions):
                processed_questions.append(reserve_questions[reserve_index])
            else:
                # Если резервные вопросы закончились, создаем новый
                q_num = len(processed_questions) + 1
                artificial_q = f"Вопрос {q_num}: Какое значение имеет тема '{topic}' для истории России?\n"
                artificial_q += f"1) Существенное влияние на культурное развитие\n"
                artificial_q += f"2) Значительное влияние на экономическое развитие\n"
                artificial_q += f"3) Определяющее влияние на политическое устройство\n"
                artificial_q += f"4) Важное влияние на международные отношения\n"
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

        # Если в первой строке нет "Вопрос:", добавляем это
        if not re.search(r'Вопрос\s*\d*\s*:', main_question, re.IGNORECASE) and not main_question.strip().endswith('?'):
            main_question = f"Вопрос: {main_question}"

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

                # Проверяем, что это не шаблонный ответ
                if not re.match(r'(Первый|Второй|Третий|Четвертый) вариант ответа', text, re.IGNORECASE) and \
                   not re.match(r'Вариант \d+', text, re.IGNORECASE) and \
                   not re.match(r'Ответ \d+', text, re.IGNORECASE) and \
                   text != "Первый вариант ответа" and \
                   text != "Второй вариант ответа" and \
                   text != "Третий вариант ответа" and \
                   text != "Четвертый вариант ответа" and \
                   text != "Дополнительный вариант ответа":
                    option_lines.append((int(number), text))
                else:
                    # Если это шаблонный ответ, создаем более конкретный ответ
                    current_topic = main_question.split()[-3:] if len(main_question.split()) > 3 else main_question.split()
                    topic_text = " ".join(current_topic)

                    if number == '1':
                        option_lines.append((int(number), f"Ранний период {topic_text}"))
                    elif number == '2':
                        option_lines.append((int(number), f"Средний период {topic_text}"))
                    elif number == '3':
                        option_lines.append((int(number), f"Поздний период {topic_text}"))
                    elif number == '4':
                        option_lines.append((int(number), f"Современный период {topic_text}"))
            elif match_letter:
                letter = match_letter.group(1)
                number = ord(letter) - ord('A') + 1
                text = match_letter.group(2).strip()

                # Проверка на шаблонные ответы
                if not re.match(r'(Первый|Второй|Третий|Четвертый) вариант ответа', text, re.IGNORECASE) and \
                   not re.match(r'Вариант \d+', text, re.IGNORECASE) and \
                   not re.match(r'Ответ \d+', text, re.IGNORECASE):
                    option_lines.append((number, text))
                else:
                    # Заменяем шаблонный ответ
                    current_topic = main_question.split()[-3:] if len(main_question.split()) > 3 else main_question.split()
                    topic_text = " ".join(current_topic)

                    if number == 1:
                        option_lines.append((number, f"Раннее развитие {topic_text}"))
                    elif number == 2:
                        option_lines.append((number, f"Ключевой этап {topic_text}"))
                    elif number == 3:
                        option_lines.append((number, f"Завершающий этап {topic_text}"))
                    elif number == 4:
                        option_lines.append((number, f"Последствия {topic_text}"))

        # Если нашли хотя бы 2 варианта ответа в ожидаемом формате
        if len(option_lines) >= 2:
            # Сортируем варианты по номеру
            option_lines.sort(key=lambda x: x[0])
            # Формируем список вариантов
            for number, text in option_lines:
                if 1 <= number <= 4:  # Проверяем, что номер в диапазоне 1-4
                    options.append(f"{number}) {text}")

        # Если варианты не найдены или их меньше 4, генерируем тематические варианты
        if len(options) < 4:
            # Извлекаем тему из вопроса
            question_keywords = ' '.join([w for w in main_question.split() if len(w) > 3 and w.lower() not in ['вопрос', 'какой', 'когда', 'где', 'почему', 'каким']])

            # Подготовим 4 тематических варианта ответа на основе вопроса
            thematic_options = [
                "Начало исторического периода",
                "Расцвет империи",
                "Период реформ",
                "Революционные изменения",
                "Военные действия", 
                "Культурное влияние",
                "Экономическое развитие",
                "Международные отношения"
            ]

            # Перемешиваем варианты для разнообразия
            import random
            random.shuffle(thematic_options)

            # Добавляем недостающие варианты
            for i in range(len(options), 4):
                options.append(f"{i+1}) {thematic_options[i]}")

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