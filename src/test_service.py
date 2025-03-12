
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
        Генерирует логически релевантные варианты ответов на основе правильного ответа и типа вопроса.
        
        Args:
            topic (str): Тема теста
            correct_answer (str): Правильный ответ
            question_type (str): Тип вопроса (дата, личность, место, причина, результат, общий)
            question_context (str): Контекст вопроса
            
        Returns:
            list: Список из 4 вариантов ответов (включая правильный)
        """
        all_options = [correct_answer]
        
        # Определяем характер правильного ответа для генерации похожих вариантов
        is_year = bool(re.search(r'\b\d{3,4}\s*(?:год|г\.)\b', correct_answer, re.IGNORECASE))
        is_person = bool(re.search(r'[А-Я][а-я]+\s+[А-Я][а-я]+(?:\s+[А-Я][а-я]+)?', correct_answer))
        has_numbers = bool(re.search(r'\d+', correct_answer))
        
        # Запрашиваем релевантные варианты от API для конкретного типа вопроса
        # Это даст нам контекстно-зависимые варианты ответов
        try:
            if len(all_options) < 4:
                prompt = self._generate_options_prompt(topic, correct_answer, question_type, question_context)
                response = self.api_client.ask_grok(prompt, use_cache=True)
                
                # Извлекаем варианты из ответа API
                api_options = self._extract_options_from_response(response, correct_answer)
                
                # Добавляем уникальные варианты
                for option in api_options:
                    if option and option not in all_options and len(all_options) < 4:
                        all_options.append(option)
        except Exception as e:
            self._logger.warning(f"Ошибка при получении вариантов ответа от API: {e}")
        
        # Если после запроса API у нас все еще меньше 4 вариантов, используем запасные стратегии
        if len(all_options) < 4:
            # Специализированные опции по типу вопроса
            if is_year or question_type == "дата":
                self._add_year_options(all_options, correct_answer)
            elif is_person or question_type == "личность":
                self._add_person_options(all_options, correct_answer, topic)
            elif question_type == "место":
                self._add_place_options(all_options, correct_answer, topic)
            elif "битва" in question_context.lower() or "сражение" in question_context.lower():
                self._add_battle_options(all_options, correct_answer, topic)
            elif "договор" in question_context.lower() or "соглашение" in question_context.lower():
                self._add_treaty_options(all_options, correct_answer, topic)
            elif "реформа" in question_context.lower():
                self._add_reform_options(all_options, correct_answer, topic)
            else:
                self._add_general_options(all_options, topic, question_context)
        
        # Если все еще не хватает вариантов, используем факты по теме
        if len(all_options) < 4:
            self._add_fact_based_options(all_options, topic)
        
        # Если все предыдущие методы не дали достаточно вариантов, 
        # добавляем общие исторические термины
        if len(all_options) < 4:
            self._add_fallback_options(all_options, topic)
        
        # Перемешиваем варианты ответов, чтобы правильный был не всегда первым
        random.shuffle(all_options)
        
        # Убеждаемся, что у нас ровно 4 варианта
        return all_options[:4]
        
    def _generate_options_prompt(self, topic, correct_answer, question_type, question_context):
        """
        Генерирует промпт для получения вариантов ответов от API.
        
        Args:
            topic (str): Тема теста
            correct_answer (str): Правильный ответ
            question_type (str): Тип вопроса
            question_context (str): Контекст вопроса
            
        Returns:
            str: Промпт для API
        """
        return f"""Для исторического вопроса по теме "{topic}": "{question_context}"
Правильный ответ: "{correct_answer}"
Тип вопроса: {question_type}

Предложи 3 логически обоснованных, но неправильных варианта ответа. 
Варианты должны быть похожими по формату и стилю на правильный ответ, 
подходить по смыслу к вопросу, но быть фактически неверными.

Ответь строго в формате списка:
1. [Вариант 1]
2. [Вариант 2]
3. [Вариант 3]

Не указывай дополнительной информации.
"""

    def _extract_options_from_response(self, response, correct_answer):
        """
        Извлекает варианты ответов из текстового ответа API.
        
        Args:
            response (str): Ответ API
            correct_answer (str): Правильный ответ
            
        Returns:
            list: Список вариантов ответов
        """
        options = []
        
        # Ищем строки с форматом "1. Вариант" или "- Вариант"
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Убираем числа, точки и прочие маркеры в начале строки
            option = re.sub(r'^[\d\.\-\*]+\s*', '', line).strip()
            
            # Если вариант не пустой и не совпадает с правильным ответом
            if option and option != correct_answer and len(option) > 1:
                options.append(option)
        
        return options
    
    def _add_year_options(self, all_options, correct_answer):
        """
        Добавляет логичные варианты годов.
        
        Args:
            all_options (list): Текущий список вариантов
            correct_answer (str): Правильный ответ
        """
        match = re.search(r'(\d{3,4})', correct_answer)
        if match:
            year = int(match.group(1))
            possible_offsets = [5, 10, 15, 20, 25, 50, 100]
            wrong_years = []
            
            # Генерируем более "округлые" и исторически вероятные даты
            for offset in possible_offsets:
                # Попробуем даты до правильного ответа
                wrong_year_before = year - offset
                if 800 <= wrong_year_before <= 2023:
                    year_str = f"{wrong_year_before} год"
                    if year_str not in all_options:
                        wrong_years.append(year_str)
                        
                # Попробуем даты после правильного ответа
                wrong_year_after = year + offset
                if 800 <= wrong_year_after <= 2023:
                    year_str = f"{wrong_year_after} год"
                    if year_str not in all_options:
                        wrong_years.append(year_str)
            
            # Перемешиваем и берем нужное количество
            random.shuffle(wrong_years)
            for wrong_year in wrong_years:
                if len(all_options) < 4:
                    all_options.append(wrong_year)
    
    def _add_person_options(self, all_options, correct_answer, topic):
        """
        Добавляет логичные варианты исторических личностей.
        
        Args:
            all_options (list): Текущий список вариантов
            correct_answer (str): Правильный ответ
            topic (str): Тема вопроса
        """
        # Определяем эпоху по правильному ответу
        era = self._determine_historical_era(correct_answer, topic)
        
        # Выбираем исторических деятелей соответствующей эпохи
        if era == "древняя":
            historical_figures = [
                "Рюрик", "Олег Вещий", "Игорь Рюрикович", "Ольга", "Святослав Игоревич",
                "Владимир Святославич", "Ярослав Мудрый", "Владимир Мономах", "Юрий Долгорукий",
                "Андрей Боголюбский", "Александр Невский", "Даниил Московский"
            ]
        elif era == "московская":
            historical_figures = [
                "Иван Калита", "Дмитрий Донской", "Василий I", "Василий II Тёмный",
                "Иван III", "Василий III", "Иван IV Грозный", "Борис Годунов",
                "Лжедмитрий I", "Василий Шуйский", "Михаил Фёдорович Романов"
            ]
        elif era == "имперская":
            historical_figures = [
                "Алексей Михайлович", "Фёдор Алексеевич", "Софья Алексеевна", "Пётр I",
                "Екатерина I", "Пётр II", "Анна Иоанновна", "Иван VI", "Елизавета Петровна",
                "Пётр III", "Екатерина II", "Павел I", "Александр I", "Николай I",
                "Александр II", "Александр III", "Николай II"
            ]
        elif era == "советская":
            historical_figures = [
                "В.И. Ленин", "И.В. Сталин", "Н.С. Хрущёв", "Л.И. Брежнев",
                "Ю.В. Андропов", "К.У. Черненко", "М.С. Горбачёв", "Г.К. Жуков",
                "К.К. Рокоссовский", "А.М. Василевский", "И.С. Конев", "Л.Д. Троцкий",
                "М.В. Фрунзе", "М.И. Калинин", "В.М. Молотов", "Л.П. Берия"
            ]
        elif era == "современная":
            historical_figures = [
                "Б.Н. Ельцин", "В.В. Путин", "Д.А. Медведев", "Е.Т. Гайдар",
                "А.Б. Чубайс", "В.С. Черномырдин", "Г.А. Явлинский", "Ю.М. Лужков",
                "А.А. Собчак", "Р.А. Хасбулатов", "А.В. Руцкой", "С.В. Лавров"
            ]
        else:
            # Если эру определить не удалось, используем общий список
            historical_figures = [
                "Пётр I", "Екатерина II", "Александр I", "Николай II", 
                "Иван Грозный", "Александр II", "Елизавета Петровна", "Александр III",
                "А.В. Суворов", "М.И. Кутузов", "Г.К. Жуков", "К.К. Рокоссовский",
                "П.А. Румянцев", "М.Д. Скобелев", "А.М. Василевский", "И.С. Конев",
                "П.А. Столыпин", "С.Ю. Витте", "В.И. Ленин", "И.В. Сталин",
                "Н.С. Хрущёв", "Л.И. Брежнев", "М.С. Горбачёв", "Б.Н. Ельцин"
            ]
        
        # Исключаем правильный ответ из списка
        historical_figures = [figure for figure in historical_figures if figure != correct_answer]
        
        # Перемешиваем и добавляем нужное количество вариантов
        random.shuffle(historical_figures)
        for figure in historical_figures:
            if len(all_options) < 4:
                all_options.append(figure)
    
    def _add_place_options(self, all_options, correct_answer, topic):
        """
        Добавляет логичные варианты мест.
        
        Args:
            all_options (list): Текущий список вариантов
            correct_answer (str): Правильный ответ
            topic (str): Тема вопроса
        """
        # Группируем места по историческому значению и географии
        if "битва" in topic.lower() or "сражение" in topic.lower():
            places = [
                "Куликово поле", "Бородино", "Полтава", "Сталинград", "Курская дуга",
                "Нева", "Чудское озеро", "Нарва", "Севастополь", "Измаил",
                "Синоп", "Нахимов", "Цусима", "Порт-Артур", "Ленинград"
            ]
        elif "восток" in topic.lower() or "азия" in topic.lower():
            places = [
                "Владивосток", "Хабаровск", "Порт-Артур", "Харбин", "Манчжурия",
                "Сахалин", "Курилы", "Китай", "Япония", "Монголия",
                "Амур", "Уссури", "Байкал", "Иркутск", "Чита"
            ]
        elif "запад" in topic.lower() or "европ" in topic.lower():
            places = [
                "Варшава", "Кёнигсберг", "Берлин", "Париж", "Вена",
                "Прага", "Будапешт", "Бухарест", "София", "Белград",
                "Киев", "Минск", "Вильнюс", "Рига", "Таллин"
            ]
        elif "юг" in topic.lower() or "кавказ" in topic.lower():
            places = [
                "Крым", "Севастополь", "Одесса", "Ростов", "Краснодар",
                "Тбилиси", "Баку", "Ереван", "Ялта", "Симферополь",
                "Чёрное море", "Азовское море", "Кавказ", "Эльбрус", "Сочи"
            ]
        elif "север" in topic.lower():
            places = [
                "Архангельск", "Мурманск", "Петрозаводск", "Вологда", "Новгород",
                "Псков", "Белое море", "Онежское озеро", "Ладожское озеро", "Кольский полуостров",
                "Соловки", "Карелия", "Финляндия", "Выборг", "Северная Двина"
            ]
        else:
            # Общий список исторически значимых мест
            places = [
                "Москва", "Санкт-Петербург", "Новгород", "Киев", "Казань", 
                "Севастополь", "Владивосток", "Архангельск", "Смоленск", 
                "Бородино", "Полтава", "Сталинград", "Куликово поле",
                "Ленинград", "Нижний Новгород", "Владимир", "Ярославль", 
                "Астрахань", "Азов", "Курск", "Псков", "Рязань"
            ]
        
        # Исключаем правильный ответ
        places = [place for place in places if place != correct_answer]
        
        # Перемешиваем и добавляем нужное количество вариантов
        random.shuffle(places)
        for place in places:
            if len(all_options) < 4:
                all_options.append(place)
                
    def _add_battle_options(self, all_options, correct_answer, topic):
        """
        Добавляет варианты для вопросов о битвах и сражениях.
        
        Args:
            all_options (list): Текущий список вариантов
            correct_answer (str): Правильный ответ
            topic (str): Тема вопроса
        """
        battles = [
            "Ледовое побоище", "Куликовская битва", "Стояние на реке Угре",
            "Битва при Молодях", "Полтавская битва", "Бородинское сражение", 
            "Синопское сражение", "Оборона Севастополя", "Брусиловский прорыв",
            "Битва за Москву", "Сталинградская битва", "Курская битва",
            "Битва за Ленинград", "Битва за Берлин", "Сражение под Нарвой", 
            "Сражение при Аустерлице", "Сражение под Бородино"
        ]
        
        # Исключаем правильный ответ
        battles = [battle for battle in battles if battle != correct_answer]
        
        # Перемешиваем и добавляем
        random.shuffle(battles)
        for battle in battles:
            if len(all_options) < 4:
                all_options.append(battle)
    
    def _add_treaty_options(self, all_options, correct_answer, topic):
        """
        Добавляет варианты для вопросов о договорах и соглашениях.
        
        Args:
            all_options (list): Текущий список вариантов
            correct_answer (str): Правильный ответ
            topic (str): Тема вопроса
        """
        treaties = [
            "Вечный мир с Польшей", "Ништадтский мир", "Турецко-русский мирный договор",
            "Бухарестский мирный договор", "Парижский мирный договор", 
            "Сан-Стефанский мирный договор", "Берлинский трактат",
            "Портсмутский мирный договор", "Брест-Литовский мирный договор",
            "Рапалльский договор", "Договор о ненападении между Германией и СССР",
            "Ялтинские соглашения", "Потсдамские соглашения", 
            "Хельсинкские соглашения", "Беловежские соглашения"
        ]
        
        # Исключаем правильный ответ
        treaties = [treaty for treaty in treaties if treaty != correct_answer]
        
        # Перемешиваем и добавляем
        random.shuffle(treaties)
        for treaty in treaties:
            if len(all_options) < 4:
                all_options.append(treaty)
    
    def _add_reform_options(self, all_options, correct_answer, topic):
        """
        Добавляет варианты для вопросов о реформах.
        
        Args:
            all_options (list): Текущий список вариантов
            correct_answer (str): Правильный ответ
            topic (str): Тема вопроса
        """
        reforms = [
            "Земская реформа", "Судебная реформа", "Военная реформа", 
            "Крестьянская реформа", "Отмена крепостного права", "Денежная реформа Витте",
            "Столыпинская аграрная реформа", "Реформы Александра II",
            "Финансовая реформа Канкрина", "Великие реформы 1860-х годов",
            "НЭП", "Коллективизация", "Индустриализация",
            "Косыгинская реформа", "Перестройка", "Приватизация 1990-х"
        ]
        
        # Исключаем правильный ответ
        reforms = [reform for reform in reforms if reform != correct_answer]
        
        # Перемешиваем и добавляем
        random.shuffle(reforms)
        for reform in reforms:
            if len(all_options) < 4:
                all_options.append(reform)
        
    def _add_general_options(self, all_options, topic, question_context):
        """
        Добавляет общие варианты, релевантные вопросу.
        
        Args:
            all_options (list): Текущий список вариантов
            topic (str): Тема вопроса
            question_context (str): Контекст вопроса
        """
        # Определяем ключевые слова из вопроса для создания тематических вариантов
        question_lower = question_context.lower()
        
        # Варианты на основе контекста вопроса
        context_options = []
        
        if "кто" in question_lower or "какой" in question_lower:
            if "император" in question_lower or "царь" in question_lower:
                context_options.extend([
                    "Предыдущий правитель", 
                    "Наследник престола", 
                    "Регент при малолетнем правителе",
                    "Фаворит императора/императрицы"
                ])
            elif "полководец" in question_lower or "генерал" in question_lower:
                context_options.extend([
                    "Главнокомандующий войсками", 
                    "Военный министр", 
                    "Начальник штаба",
                    "Герой предыдущей войны"
                ])
            elif "министр" in question_lower or "чиновник" in question_lower:
                context_options.extend([
                    "Председатель правительства", 
                    "Глава министерства", 
                    "Государственный секретарь",
                    "Реформатор государственного управления"
                ])
        
        elif "где" in question_lower or "место" in question_lower:
            if "сражение" in question_lower or "битва" in question_lower:
                context_options.extend([
                    "Место предыдущего крупного сражения", 
                    "Стратегически важная крепость", 
                    "Приграничный город",
                    "Место подписания мирного договора"
                ])
        
        # Общие варианты для истории России
        general_options = [
            f"Ключевое событие {topic}",
            f"Противоположный аспект {topic}",
            f"Предпосылка основных событий {topic}",
            f"Закономерный результат {topic}"
        ]
        
        # Объединяем и перемешиваем
        all_context_options = context_options + general_options
        random.shuffle(all_context_options)
        
        for option in all_context_options:
            if option not in all_options and len(all_options) < 4:
                all_options.append(option)
    
    def _add_fact_based_options(self, all_options, topic):
        """
        Добавляет варианты на основе исторических фактов.
        
        Args:
            all_options (list): Текущий список вариантов
            topic (str): Тема вопроса
        """
        facts = self._get_topic_facts(topic)
        
        if facts:
            # Перемешиваем факты
            random.shuffle(facts)
            
            for fact in facts:
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
                
                if fact and fact not in all_options and len(all_options) < 4:
                    all_options.append(fact)
    
    def _add_fallback_options(self, all_options, topic):
        """
        Добавляет запасные варианты, если все предыдущие методы не сработали.
        
        Args:
            all_options (list): Текущий список вариантов
            topic (str): Тема вопроса
        """
        fallback_options = [
            f"Событие раннего периода {topic}",
            f"Событие позднего периода {topic}",
            f"Ключевой этап {topic}",
            f"Переломный момент в истории {topic}",
            f"Начальная фаза {topic}",
            f"Завершающий этап {topic}",
            f"Период расцвета {topic}",
            f"Период упадка {topic}",
            f"Незначительный аспект {topic}",
            f"Локальное событие в рамках {topic}"
        ]
        
        random.shuffle(fallback_options)
        for option in fallback_options:
            if option not in all_options and len(all_options) < 4:
                all_options.append(option)
    
    def _determine_historical_era(self, person_name, topic):
        """
        Определяет историческую эпоху по имени исторической личности или теме.
        
        Args:
            person_name (str): Имя исторической личности
            topic (str): Тема вопроса
            
        Returns:
            str: Определенная эпоха
        """
        # Ключевые слова для определения эпохи
        ancient_keywords = ["древн", "рюрик", "киевск", "князь", "ярослав", "владимир", "невский", "вещий", "игорь", "ольга"]
        moscow_keywords = ["московск", "калита", "донской", "иван iii", "иван грозный", "годунов", "лжедмитрий", "смута", "михаил романов"]
        imperial_keywords = ["импер", "петр", "екатерина", "александр i", "николай i", "александр ii", "александр iii", "николай ii", "романов"]
        soviet_keywords = ["советск", "ленин", "сталин", "хрущев", "брежнев", "горбачев", "ссср", "революц", "вов", "великая отечественная"]
        modern_keywords = ["соврем", "ельцин", "путин", "медведев", "российск", "россия", "постсоветск", "федерац"]
        
        # Проверяем ключевые слова в имени и теме
        combined_text = (person_name + " " + topic).lower()
        
        if any(keyword in combined_text for keyword in ancient_keywords):
            return "древняя"
        elif any(keyword in combined_text for keyword in moscow_keywords):
            return "московская"
        elif any(keyword in combined_text for keyword in imperial_keywords):
            return "имперская"
        elif any(keyword in combined_text for keyword in soviet_keywords):
            return "советская"
        elif any(keyword in combined_text for keyword in modern_keywords):
            return "современная"
        else:
            # Если не удалось определить эпоху по ключевым словам,
            # пробуем определить по годам в теме
            year_match = re.search(r'(\d{3,4})\s*(?:год|г\.)?', combined_text)
            if year_match:
                year = int(year_match.group(1))
                if year < 1300:
                    return "древняя"
                elif 1300 <= year < 1700:
                    return "московская"
                elif 1700 <= year < 1917:
                    return "имперская"
                elif 1917 <= year < 1991:
                    return "советская"
                elif year >= 1991:
                    return "современная"
        
        # Если не удалось определить эпоху, возвращаем общую
        return "общая"

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
