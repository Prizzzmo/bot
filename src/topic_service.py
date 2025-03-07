
import re
import random

class TopicService:
    """Класс для работы с темами по истории России"""
    
    def __init__(self, api_client, logger):
        """
        Инициализация сервиса тем
        
        Args:
            api_client: Клиент API для получения данных
            logger: Логгер для записи действий
        """
        self.api_client = api_client
        self.logger = logger
        
    def generate_topics_list(self, use_cache=True):
        """
        Генерирует список тем по истории России
        
        Args:
            use_cache (bool): Использовать ли кэш
            
        Returns:
            list: Список тем
        """
        prompt = "Составь список из 30 ключевых тем по истории России, которые могут быть интересны для изучения. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
        topics_text = self.api_client.ask_grok(prompt, use_cache=use_cache)
        
        # Парсим и возвращаем темы
        return self.parse_topics(topics_text)
    
    def generate_new_topics_list(self):
        """
        Генерирует новый список тем с разнообразным содержанием
        
        Returns:
            list: Новый список тем
        """
        # Добавляем случайный параметр для получения разных тем
        random_seed = random.randint(1, 1000)
        prompt = f"Составь список из 30 новых и оригинальных тем по истории России, которые могут быть интересны для изучения. Сосредоточься на темах {random_seed}. Выбери темы, отличные от стандартных и ранее предложенных. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
        
        # Отключаем кэширование для получения действительно новых тем
        topics_text = self.api_client.ask_grok(prompt, use_cache=False)
        
        # Парсим и возвращаем темы
        return self.parse_topics(topics_text)
    
    def parse_topics(self, topics_text):
        """
        Парсит темы из текстового ответа API
        
        Args:
            topics_text (str): Текстовый ответ от API
            
        Returns:
            list: Список тем
        """
        topics = []
        
        # Разбиваем текст на строки и ищем нумерованные пункты
        for line in topics_text.splitlines():
            # Ищем строки вида "1. Тема" или "1) Тема"
            match = re.match(r'^\s*(\d+)[\.\)]\s+(.*?)$', line)
            if match:
                number, topic = match.groups()
                # Добавляем тему с номером для сохранения порядка
                topics.append(f"{number}. {topic.strip()}")
        
        # Если ничего не нашли, пробуем другие форматы
        if not topics:
            for line in topics_text.splitlines():
                # Ищем строки, которые могут быть темами без нумерации
                if line.strip() and not line.startswith('#') and not line.startswith('**'):
                    topics.append(line.strip())
        
        # Очищаем список от возможных дубликатов
        filtered_topics = []
        seen_topics = set()
        
        for topic in topics:
            # Извлекаем текст темы без номера
            text = topic.split('. ', 1)[1] if '. ' in topic else topic
            text_lower = text.lower()
            
            # Добавляем только если такой темы еще не было
            if text_lower not in seen_topics:
                filtered_topics.append(topic)
                seen_topics.add(text_lower)
        
        return filtered_topics
    
    def get_topic_info(self, topic, update_callback=None):
        """
        Получает подробную информацию по теме
        
        Args:
            topic (str): Тема для получения информации
            update_callback (function): Функция обратного вызова для обновления статуса
            
        Returns:
            list: Список сообщений с информацией по теме (по одному на каждую главу)
        """
        try:
            # Очищаем тему от специальных символов для безопасной обработки
            def sanitize_markdown(text):
                if not text:
                    return ""
                # Экранируем специальные символы Markdown
                chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                for char in chars_to_escape:
                    text = text.replace(char, '\\' + char)
                return text
            
            # Очищаем пользовательский ввод
            safe_topic = sanitize_markdown(topic)
            
            chapters = [
                "Истоки и предпосылки",
                "Ключевые события", 
                "Исторические личности",
                "Международный контекст",
                "Историческое значение"
            ]
            
            # Формируем запрос на получение структурированной информации по теме
            prompt = f"""Предоставь структурированную информацию по теме "{safe_topic}" из истории России.
            Раздели ответ на следующие главы:
            1. {chapters[0]}: предыстория, причины возникновения, контекст эпохи
            2. {chapters[1]}: хронология, основные этапы, ключевые даты
            3. {chapters[2]}: важные исторические фигуры, их роль и вклад
            4. {chapters[3]}: взаимосвязь с мировыми событиями, внешняя политика
            5. {chapters[4]}: последствия, влияние на дальнейшую историю

            Используй только проверенные исторические факты. Придерживайся нейтрального стиля изложения.
            Текст должен быть информативным и хорошо структурированным для образовательных целей.
            """
            
            if update_callback:
                update_callback(f"🔍 Собираю информацию по теме: *{topic}*...")
            
            response = self.api_client.ask_grok(prompt)
            
            if update_callback:
                update_callback(f"✏️ Форматирую материал по теме: *{topic}*...")
            
            # Разбиваем информацию по главам для отдельных сообщений
            chapter_messages = self._split_content_into_chapters(response, chapters, safe_topic)
            
            # Если не удалось разбить на главы, возвращаем один общий ответ
            if not chapter_messages:
                try:
                    sanitized_content = sanitize_markdown(response)
                    return [f"📚 *{safe_topic}*\n\n{sanitized_content}"]
                except Exception as sanitize_error:
                    self.logger.error(f"Ошибка при очистке контента: {sanitize_error}")
                    return [f"📚 *{safe_topic}*\n\n{response}"]
            
            # Возвращаем список сообщений
            return chapter_messages
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации по теме {topic}: {e}")
            return [f"⚠️ Не удалось получить информацию по теме: {topic}. Ошибка: {str(e)}"]
    
    def _format_content_with_chapters(self, content, chapters, topic):
        """
        Форматирует контент с разделением на главы
        
        Args:
            content (str): Исходный контент
            chapters (list): Список названий глав
            topic (str): Название темы
            
        Returns:
            str: Отформатированный контент
        """
        formatted_content = f"# {topic}\n\n"
        
        # Разбиваем контент на главы
        chapter_contents = {}
        current_chapter = None
        
        for line in content.split('\n'):
            # Проверяем, является ли строка заголовком главы
            for i, chapter in enumerate(chapters, 1):
                if chapter in line or f"{i}." in line or f"{i}:" in line:
                    current_chapter = chapter
                    chapter_contents[current_chapter] = []
                    break
            
            # Добавляем строку к текущей главе
            if current_chapter:
                chapter_contents[current_chapter].append(line)
        
        # Форматируем главы в Markdown
        for i, chapter in enumerate(chapters):
            if chapter in chapter_contents:
                chapter_text = '\n'.join(chapter_contents[chapter])
                # Удаляем номер главы из текста, если он есть
                chapter_text = re.sub(r'^\d+[\.\:\)]?\s*', '', chapter_text)
                # Удаляем название главы из текста, если оно есть
                chapter_text = re.sub(re.escape(chapter), '', chapter_text, flags=re.IGNORECASE)
                
                formatted_content += f"## {chapter}\n\n{chapter_text.strip()}\n\n"
            else:
                # Если глава не найдена, используем весь контент
                if i == 0 and not chapter_contents:
                    formatted_content += content
                    break
        
        return formatted_content
        
    def _split_content_into_chapters(self, content, chapters, topic):
        """
        Разбивает контент на отдельные сообщения по главам
        
        Args:
            content (str): Исходный контент
            chapters (list): Список названий глав
            topic (str): Название темы
            
        Returns:
            list: Список сообщений, по одному на каждую главу
        """
        # Разбиваем контент на главы
        chapter_contents = {}
        current_chapter = None
        
        # Специальные эмодзи для каждой главы
        chapter_emoji = {
            "Истоки и предпосылки": "🔍",
            "Ключевые события": "📅",
            "Исторические личности": "👥",
            "Международный контекст": "🌍",
            "Историческое значение": "⚖️"
        }
        
        # Если контент пустой или слишком короткий, возвращаем его как есть
        if not content or len(content) < 50:
            return [f"📚 *{topic}*\n\n{content}"]
        
        # Разбиваем контент по строкам и распределяем по главам
        lines = content.split('\n')
        current_chapter = None
        
        for line in lines:
            # Проверяем, является ли строка заголовком главы
            for i, chapter in enumerate(chapters, 1):
                # Улучшенное определение заголовка главы
                if (chapter.lower() in line.lower() or 
                    f"{i}." in line or 
                    f"{i}:" in line or 
                    (i == 1 and ("введение" in line.lower() or "истоки" in line.lower())) or
                    (i == 2 and ("события" in line.lower() or "хронология" in line.lower())) or
                    (i == 3 and ("личности" in line.lower() or "деятели" in line.lower())) or
                    (i == 4 and ("мир" in line.lower() or "международный" in line.lower())) or
                    (i == 5 and ("значение" in line.lower() or "влияние" in line.lower() or "итоги" in line.lower()))):
                    current_chapter = chapter
                    if current_chapter not in chapter_contents:
                        chapter_contents[current_chapter] = []
                    break
            
            # Добавляем строку к текущей главе
            if current_chapter:
                # Чистим строку от нумерации заголовка, если есть
                cleaned_line = line
                if current_chapter in line:
                    for i, chapter in enumerate(chapters, 1):
                        if chapter in line:
                            # Удаляем номер главы и название из строки
                            cleaned_line = re.sub(rf'\d+[\.\:\)]?\s*{re.escape(chapter)}', '', line, flags=re.IGNORECASE)
                            cleaned_line = cleaned_line.strip()
                
                if cleaned_line:  # Добавляем только непустые строки
                    chapter_contents[current_chapter].append(cleaned_line)
            # Если еще не определили главу, ищем упоминания тем в тексте
            elif line.strip():
                found_chapter = False
                for chapter in chapters:
                    if any(keyword in line.lower() for keyword in chapter.lower().split()):
                        current_chapter = chapter
                        if current_chapter not in chapter_contents:
                            chapter_contents[current_chapter] = []
                        chapter_contents[current_chapter].append(line)
                        found_chapter = True
                        break
                
                # Если не нашли подходящую главу, добавляем в первую
                if not found_chapter and chapters and chapters[0] not in chapter_contents:
                    current_chapter = chapters[0]
                    chapter_contents[current_chapter] = [line]
        
        # Если не удалось разбить на главы, значит формат ответа от API отличается
        # Попробуем распределить текст по главам эвристически
        if not chapter_contents and lines:
            # Разбиваем весь текст примерно на 5 равных частей
            chunk_size = max(5, len(lines) // 5)
            for i, chapter in enumerate(chapters):
                start_idx = i * chunk_size
                end_idx = (i + 1) * chunk_size if i < 4 else len(lines)
                if start_idx < len(lines):
                    chapter_contents[chapter] = lines[start_idx:end_idx]
        
        # Формируем сообщения для каждой главы
        messages = []
        
        # Сначала добавляем заголовок с темой
        title_message = f"📚 *{topic}*"
        
        # Затем добавляем оглавление
        toc = "\n\n*Оглавление:*\n"
        for i, chapter in enumerate(chapters, 1):
            emoji = chapter_emoji.get(chapter, "•")
            toc += f"{emoji} *Глава {i}:* {chapter}\n"
        
        title_message += toc
        messages.append(title_message)
        
        # Затем создаем отдельное сообщение для каждой главы
        for i, chapter in enumerate(chapters, 1):
            if chapter in chapter_contents and chapter_contents[chapter]:
                # Очищаем текст главы от повторяющихся заголовков
                chapter_text = '\n'.join(chapter_contents[chapter])
                
                # Удаляем номер главы из текста, если он есть
                chapter_text = re.sub(r'^\d+[\.\:\)]?\s*', '', chapter_text)
                
                # Удаляем название главы из текста, если оно есть
                chapter_text = re.sub(re.escape(chapter), '', chapter_text, flags=re.IGNORECASE)
                
                # Форматируем текст
                emoji = chapter_emoji.get(chapter, "•")
                chapter_message = f"{emoji} *Глава {i}: {chapter}*\n\n{chapter_text.strip()}"
                
                # Добавляем номера глав для удобной навигации
                if i < len(chapters):
                    chapter_message += f"\n\n*Далее:* Глава {i+1}: {chapters[i]}"
                
                messages.append(chapter_message)
            else:
                # Если глава не найдена, добавляем заголовок без содержания
                emoji = chapter_emoji.get(chapter, "•")
                messages.append(f"{emoji} *Глава {i}: {chapter}*\n\nИнформация по данной главе отсутствует.")
        
        return messages
