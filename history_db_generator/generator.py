
import os
import json
import time
import re
import hashlib
import random
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

# Создаем директорию для скрипта если она не существует
os.makedirs("history_db_generator", exist_ok=True)

# Загружаем переменные окружения из .env файла
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("API ключ Gemini не найден. Проверьте файл .env.")

# Настраиваем клиент Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Путь к файлу базы данных
DB_FILE = "history_db_generator/russian_history_database.json"
TEMP_FOLDER = "history_db_generator/temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Словарь с основными категориями событий
EVENT_CATEGORIES = [
    "Войны и сражения",
    "Культура и религия",
    "Становление государства",
    "Социальные реформы",
    "Революции и перевороты",
    "Научные достижения",
    "Экономические события",
    "Изменения границ",
    "Военные кампании",
    "Дипломатические события",
    "Территориальные приобретения",
    "Основание городов",
    "Восстания и бунты",
    "Политические реформы"
]

def hash_string(text):
    """Создает хеш строки для использования в идентификаторах."""
    return hashlib.md5(text.encode()).hexdigest()[:8]

def call_gemini_api(prompt, temperature=0.3, max_output_tokens=1024, retry_count=3, retry_delay=5):
    """
    Отправляет запрос к API Gemini с механизмом повторных попыток.
    
    Args:
        prompt: Текст запроса
        temperature: Параметр креативности (0.0-1.0)
        max_output_tokens: Максимальная длина ответа
        retry_count: Количество попыток в случае ошибки
        retry_delay: Задержка между попытками в секундах
        
    Returns:
        str: Ответ от модели
    """
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "top_p": 0.95,
        "top_k": 40,
    }
    
    for attempt in range(retry_count):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            print(f"Ошибка при запросе к API (попытка {attempt+1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                delay = retry_delay * (2 ** attempt)  # Экспоненциальная задержка
                print(f"Повторная попытка через {delay} секунд...")
                time.sleep(delay)
            else:
                print(f"Не удалось получить ответ после {retry_count} попыток.")
                return ""

def save_json(data, filename):
    """Сохраняет данные в JSON файл."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Данные сохранены в {filename}")

def load_json(filename):
    """Загружает данные из JSON файла."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def generate_historical_topics():
    """
    Генерирует максимально полный список исторических тем России.
    
    Returns:
        list: Список исторических тем
    """
    print("Генерация списка исторических тем России...")
    
    # Файл для кэширования тем
    topics_cache_file = f"{TEMP_FOLDER}/historical_topics_cache.json"
    
    # Проверяем, есть ли кэшированные данные
    cached_topics = load_json(topics_cache_file)
    if cached_topics:
        print(f"Загружено {len(cached_topics)} тем из кэша.")
        return cached_topics
    
    # Создаем максимально детальный запрос для получения всеобъемлющего списка тем
    prompt = """
    Составь максимально полный список тем по истории России с древней Руси до 2025 года. 
    
    Обязательно включи темы по следующим историческим периодам:
    1. Древняя Русь (от возникновения славянских поселений до монгольского нашествия)
    2. Период татаро-монгольского ига
    3. Возвышение Москвы и становление единого государства
    4. Правление каждого из русских царей и императоров (подробно по каждому)
    5. Смутное время
    6. Петровские реформы
    7. Дворцовые перевороты XVIII века
    8. Российская империя в XIX веке (все ключевые реформы, войны и события)
    9. Революционное движение
    10. Первая мировая война
    11. Революция 1917 года и Гражданская война
    12. СССР в 1920-е и 1930-е годы
    13. Великая Отечественная война (подробно по ключевым сражениям)
    14. Послевоенное восстановление и холодная война
    15. Хрущевская оттепель
    16. Период застоя
    17. Перестройка
    18. Распад СССР
    19. Россия в 1990-е годы
    20. Россия в XXI веке до 2025 года
    
    Добавь также темы, касающиеся:
    - Культуры и искусства в разные исторические периоды
    - Экономического развития
    - Социальной структуры общества
    - Внешней политики России
    - Национальной политики
    - Религии и церкви
    - Науки и техники
    - Военной истории
    
    Список должен быть максимально полным. Каждая тема должна быть сформулирована четко и конкретно (не более 10 слов в названии).
    Представь результат в виде нумерованного списка, НЕ группируя темы по разделам.
    """
    
    # Делаем несколько запросов для получения максимального количества тем
    all_topics = []
    batch_count = 5  # Количество разных запросов для максимального охвата
    
    for i in range(batch_count):
        # Добавляем случайное число к запросу, чтобы получить разные результаты
        batch_prompt = prompt + f"\n\nДополнительная инструкция для уникальности результата: seed={random.randint(1000, 9999)}"
        
        print(f"Выполняется запрос тем (часть {i+1}/{batch_count})...")
        response = call_gemini_api(batch_prompt, temperature=0.6, max_output_tokens=2048)
        
        # Парсим темы из ответа
        lines = response.strip().split('\n')
        for line in lines:
            # Ищем строки, начинающиеся с цифры и точки/скобки
            match = re.match(r'^\s*\d+[\.\)]\s*(.*?)$', line)
            if match:
                topic = match.group(1).strip()
                if topic and topic not in all_topics:
                    all_topics.append(topic)
    
    # Добавляем запрос для конкретных исторических периодов, которые могли быть пропущены
    specific_periods = [
        "Киевская Русь", "Монгольское нашествие", "Ордынское иго", 
        "Возвышение Московского княжества", "Правление Ивана Грозного",
        "Смутное время", "Реформы Петра I", "Дворцовые перевороты",
        "Правление Екатерины II", "Отечественная война 1812 года",
        "Крымская война", "Отмена крепостного права", "Революция 1905 года",
        "Февральская революция", "Октябрьская революция", "Гражданская война",
        "Индустриализация и коллективизация", "Сталинские репрессии",
        "Великая Отечественная война", "Холодная война", "Перестройка",
        "Распад СССР", "Экономические реформы 1990-х", "Правление Путина",
        "Присоединение Крыма", "Специальная военная операция"
    ]
    
    for period in specific_periods:
        if period not in all_topics:
            all_topics.append(period)
    
    print(f"Сгенерировано {len(all_topics)} уникальных исторических тем.")
    
    # Сохраняем темы в кэш
    save_json(all_topics, topics_cache_file)
    
    return all_topics

def extract_events_from_text(text):
    """
    Извлекает события из текстового ответа API.
    
    Args:
        text: Текстовый ответ от API
        
    Returns:
        list: Список извлеченных событий
    """
    events = []
    
    # Ищем события с датами в различных форматах
    # 1. Год или диапазон лет: "1703 г.", "988-989 гг.", "в 1812 году"
    year_pattern = r'(\b(?:в\s+)?(?:1[0-9]{3}|20[0-2][0-9]|[5-9][0-9]{2})(?:-(?:1[0-9]{3}|20[0-2][0-9]))?\s*(?:г(?:од)?\.?|гг\.?)?\b)'
    
    # 2. Дата с месяцем: "27 июня 1709 г.", "Сентябрь 1380"
    date_pattern = r'(\b(?:[1-3]?[0-9]\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)|(?:январ[ья]|феврал[ья]|март[а]|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|август[а]|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])\s+[1-3]?[0-9]?)\s+(?:1[0-9]{3}|20[0-2][0-9]|[5-9][0-9]{2})(?:\s*г(?:од)?\.?)?)'
    
    # Разбиваем текст на абзацы
    paragraphs = re.split(r'\n+', text)
    
    for paragraph in paragraphs:
        # Пропускаем короткие абзацы
        if len(paragraph) < 20:
            continue
            
        # Ищем года и даты
        year_matches = re.finditer(year_pattern, paragraph)
        date_matches = re.finditer(date_pattern, paragraph)
        
        all_matches = list(year_matches) + list(date_matches)
        if not all_matches:
            continue
            
        # Для каждого найденного совпадения с датой
        for match in all_matches:
            date_str = match.group(0)
            
            # Определяем положение даты в тексте
            date_pos = match.start()
            
            # Берем часть предложения до и после даты
            pre_text = paragraph[:date_pos].strip()
            post_text = paragraph[date_pos + len(date_str):].strip()
            
            # Определяем границы предложения с событием
            sentence_start = max(0, pre_text.rfind('.') + 1) if pre_text and '.' in pre_text else 0
            sentence_end = post_text.find('.') if post_text and '.' in post_text else len(post_text)
            
            event_text = (pre_text[sentence_start:] + ' ' + date_str + ' ' + post_text[:sentence_end]).strip()
            
            # Если текст события слишком короткий, вероятно это не событие
            if len(event_text) < 15:
                continue
                
            # Очищаем текст от лишних пробелов и знаков
            event_text = re.sub(r'\s+', ' ', event_text)
            
            # Извлекаем возможное название события (ключевой элемент перед датой)
            title_candidates = [
                "битва", "сражение", "договор", "мир", "восстание", 
                "революция", "война", "реформа", "переворот", "основание",
                "создание", "смерть", "рождение", "указ", "манифест",
                "открытие", "принятие", "крещение", "коронация", "отмена"
            ]
            
            # Ищем кандидатов на название в событии
            title = None
            for candidate in title_candidates:
                if candidate in event_text.lower():
                    # Находим полное словосочетание с этим ключевым словом
                    match = re.search(f"([\w\s\-]+{candidate}[\w\s\-]+)", event_text.lower())
                    if match:
                        title = match.group(1).strip().capitalize()
                        break
            
            # Если не нашли конкретное название, используем начало события
            if not title:
                title = re.sub(r'^[^а-яА-Я]+', '', event_text)
                title = re.sub(r'\s+', ' ', title)
                words = title.split()
                title = ' '.join(words[:min(7, len(words))])
                title = title.strip('.,;:() ').capitalize()
            
            # Добавляем найденное событие
            if title and date_str:
                event = {
                    "title": title,
                    "date": date_str.strip(),
                    "description": event_text,
                }
                events.append(event)
    
    # Фильтруем дубликаты и короткие описания
    unique_events = []
    seen_titles = set()
    
    for event in events:
        title_key = event["title"].lower()
        if title_key not in seen_titles and len(event["description"]) > 30:
            seen_titles.add(title_key)
            unique_events.append(event)
    
    return unique_events

def get_events_for_topic(topic):
    """
    Получает список исторических событий для указанной темы.
    
    Args:
        topic: Историческая тема
        
    Returns:
        list: Список событий с датами, описаниями и местами
    """
    print(f"Получение событий для темы: {topic}")
    
    # Создаем кэш-файл для темы
    topic_hash = hash_string(topic)
    cache_file = f"{TEMP_FOLDER}/events_{topic_hash}.json"
    
    # Проверяем, есть ли кэшированные данные
    cached_events = load_json(cache_file)
    if cached_events:
        print(f"Загружено {len(cached_events)} событий из кэша для темы '{topic}'.")
        return cached_events
    
    # Формируем запрос для получения событий по теме
    events_prompt = f"""
    Составь максимально полный хронологический список важных исторических событий по теме "{topic}" из истории России.
    
    Для каждого события обязательно укажи:
    1. Точную дату (день, месяц, год, если известны, или хотя бы год)
    2. Название события
    3. Краткое описание события (1-2 предложения)
    4. Место, где происходило событие (город, регион или конкретное место, если известно)
    
    События должны быть представлены в хронологическом порядке. Для каждого события используй следующий формат:
    
    [Дата] - [Название события] - [Место события]
    [Описание события]
    
    Приведи не менее 20-30 событий, если это возможно для данной темы. Включай не только крупные, но и менее известные события.
    Будь максимально точным в датах и местах. Если место неизвестно точно, укажи наиболее вероятное.
    """
    
    # Выполняем запрос к API
    response = call_gemini_api(events_prompt, temperature=0.2, max_output_tokens=2048)
    
    # Если ответ слишком короткий, пробуем еще раз с другой формулировкой
    if len(response) < 500:
        print(f"Получен слишком короткий ответ ({len(response)} символов). Повторный запрос...")
        alternative_prompt = f"""
        Пожалуйста, составь подробный и исчерпывающий ХРОНОЛОГИЧЕСКИЙ список всех основных событий, связанных с темой "{topic}" в истории России.
        
        Для каждого события обязательно укажи:
        - Точную дату (год или день/месяц/год)
        - Название события
        - Географическое место (город, регион, и т.д.)
        - Краткое описание (2-3 предложения)
        
        Примеры формата:
        
        1. 27 мая 1703 г. - Основание Санкт-Петербурга - Устье реки Невы
        Петр I заложил Петропавловскую крепость на Заячьем острове. Это событие считается датой основания города Санкт-Петербурга, будущей столицы Российской империи.
        
        2. 8 сентября 1380 г. - Куликовская битва - Куликово поле (современная Тульская область)
        Сражение между объединённым русским войском во главе с московским князем Дмитрием Донским и войском Золотой Орды под командованием темника Мамая. Закончилось победой русского войска и стало важным шагом к независимости от Орды.
        
        Постарайся включить не менее 25-30 событий, охватывающих весь хронологический период темы. Указывай самые точные даты и конкретные места, насколько это возможно.
        """
        response = call_gemini_api(alternative_prompt, temperature=0.3, max_output_tokens=2048)
    
    # Еще один запрос для получения максимального числа событий
    additional_prompt = f"""
    Продолжи предыдущий список. Составь еще 15-20 исторических событий по теме "{topic}", которые не были упомянуты ранее.
    
    Используй тот же формат:
    [Дата] - [Название события] - [Место события]
    [Описание события]
    
    Постарайся включить менее известные, но важные события. Будь предельно точен в датах и местах.
    """
    
    additional_response = call_gemini_api(additional_prompt, temperature=0.4, max_output_tokens=2048)
    
    # Объединяем ответы
    combined_response = response + "\n\n" + additional_response
    
    # Парсим события из ответа
    events = []
    
    # Паттерн для поиска событий в формате "Дата - Название - Место"
    pattern = r'([0-9]{1,2}(?:\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря))?\s+[0-9]{3,4}(?:\s*г\.?)?|[0-9]{3,4}(?:-[0-9]{3,4})?\s*(?:г\.?|гг\.?))\s*(?:-|–|—)\s*([^-–—]+)(?:\s*(?:-|–|—)\s*([^-–—\n]+))?(?:\n|\r\n?)(.*?)(?=\n\s*(?:[0-9]|$)|\Z)'
    
    matches = re.finditer(pattern, combined_response, re.DOTALL)
    
    for match in matches:
        date = match.group(1).strip()
        title = match.group(2).strip() if match.group(2) else ""
        location = match.group(3).strip() if match.group(3) else "Не указано"
        description = match.group(4).strip() if match.group(4) else ""
        
        # Нормализуем дату
        date = re.sub(r'\s+', ' ', date)
        
        # Создаем событие
        event = {
            "title": title,
            "date": date,
            "description": description,
            "location": location,
            "category": get_category_for_event(title, description)
        }
        
        # Добавляем географические координаты, если возможно
        coordinates = get_coordinates_for_location(location)
        if coordinates:
            event["location"] = {
                "name": location,
                "lat": coordinates["lat"],
                "lng": coordinates["lng"]
            }
        
        events.append(event)
    
    # Если не удалось извлечь события через регулярные выражения,
    # попробуем альтернативный метод
    if not events:
        print(f"Не удалось извлечь события через регулярные выражения. Используем альтернативный метод...")
        events = extract_events_from_text(combined_response)
        
        # Добавляем местоположения для событий
        for event in events:
            if "location" not in event:
                location_prompt = f"""
                Укажи наиболее вероятное географическое место (город, регион или конкретную локацию), 
                где произошло следующее историческое событие из истории России:
                
                Событие: {event["title"]}
                Дата: {event["date"]}
                Описание: {event["description"]}
                
                Ответь только названием места без дополнительных комментариев.
                """
                
                location = call_gemini_api(location_prompt, temperature=0.1, max_output_tokens=100)
                
                # Очищаем ответ от возможных мусорных слов
                location = re.sub(r'^(местоположение|место|локация|ответ|это):\s*', '', location, flags=re.IGNORECASE)
                location = location.strip('.,;: \n')
                
                if location and len(location) < 100:
                    # Добавляем географические координаты, если возможно
                    coordinates = get_coordinates_for_location(location)
                    if coordinates:
                        event["location"] = {
                            "name": location,
                            "lat": coordinates["lat"],
                            "lng": coordinates["lng"]
                        }
                    else:
                        event["location"] = location
    
    # Определяем категории для событий, если они еще не определены
    for event in events:
        if "category" not in event:
            event["category"] = get_category_for_event(event["title"], event["description"])
    
    print(f"Найдено {len(events)} событий для темы '{topic}'")
    
    # Сохраняем события в кэш
    save_json(events, cache_file)
    
    return events

def get_category_for_event(title, description):
    """
    Определяет категорию события на основе его названия и описания.
    
    Args:
        title: Название события
        description: Описание события
        
    Returns:
        str: Категория события
    """
    text = (title + " " + description).lower()
    
    category_keywords = {
        "Войны и сражения": ["война", "битва", "сражение", "штурм", "осада", "военн", "бой", "наступлен", "оборон"],
        "Культура и религия": ["культур", "искусств", "литератур", "живопис", "театр", "музык", "религи", "церков", "храм", "собор", "монастыр", "христиан", "православ", "патриарх"],
        "Становление государства": ["государств", "княжеств", "образован", "объединен", "централизац", "суверенитет", "независимост"],
        "Социальные реформы": ["реформ", "изменен", "преобразован", "закон", "кодекс", "устав", "социальн"],
        "Революции и перевороты": ["революц", "переворот", "восстан", "бунт", "смут", "свержен"],
        "Научные достижения": ["наук", "изобретен", "открыт", "исследован", "экспедиц", "техник", "конструкц"],
        "Экономические события": ["экономи", "финанс", "денеж", "торгов", "промышлен", "хозяйств", "индустр", "кризис"],
        "Изменения границ": ["границ", "территор", "присоедин", "аннекс", "раздел", "присоедин", "экспансия"],
        "Дипломатические события": ["договор", "соглашен", "альянс", "союз", "мир", "перемир", "дипломат", "визит"]
    }
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text:
                return category
    
    # Если не нашли соответствия, возвращаем общую категорию
    return random.choice(EVENT_CATEGORIES)

def get_coordinates_for_location(location_name):
    """
    Возвращает приблизительные координаты для указанного местоположения.
    
    Args:
        location_name: Название местоположения
        
    Returns:
        dict: Словарь с координатами (lat, lng) или None, если не удалось определить
    """
    # Словарь с координатами популярных российских городов и регионов
    location_coords = {
        "москва": {"lat": 55.75, "lng": 37.62},
        "санкт-петербург": {"lat": 59.94, "lng": 30.31},
        "петербург": {"lat": 59.94, "lng": 30.31},
        "петроград": {"lat": 59.94, "lng": 30.31},
        "ленинград": {"lat": 59.94, "lng": 30.31},
        "киев": {"lat": 50.45, "lng": 30.52},
        "новгород": {"lat": 58.52, "lng": 31.27},
        "псков": {"lat": 57.82, "lng": 28.33},
        "владимир": {"lat": 56.13, "lng": 40.42},
        "суздаль": {"lat": 56.42, "lng": 40.44},
        "казань": {"lat": 55.79, "lng": 49.12},
        "нижний новгород": {"lat": 56.32, "lng": 44.00},
        "екатеринбург": {"lat": 56.84, "lng": 60.65},
        "севастополь": {"lat": 44.62, "lng": 33.53},
        "ялта": {"lat": 44.50, "lng": 34.17},
        "крым": {"lat": 45.30, "lng": 34.20},
        "сталинград": {"lat": 48.70, "lng": 44.52},
        "волгоград": {"lat": 48.70, "lng": 44.52},
        "куликово поле": {"lat": 53.67, "lng": 38.67},
        "берлин": {"lat": 52.52, "lng": 13.40},
        "бородино": {"lat": 55.52, "lng": 35.83},
        "полтава": {"lat": 49.59, "lng": 34.55},
        "смоленск": {"lat": 54.78, "lng": 32.05},
        "архангельск": {"lat": 64.54, "lng": 40.54},
        "мурманск": {"lat": 68.97, "lng": 33.07},
        "новосибирск": {"lat": 55.03, "lng": 82.92},
        "владивосток": {"lat": 43.12, "lng": 131.89},
        "хабаровск": {"lat": 48.48, "lng": 135.08},
        "ростов-на-дону": {"lat": 47.23, "lng": 39.72},
        "краснодар": {"lat": 45.03, "lng": 38.98},
        "ярославль": {"lat": 57.63, "lng": 39.87},
        "самара": {"lat": 53.20, "lng": 50.15},
        "астрахань": {"lat": 46.35, "lng": 48.04},
        "тула": {"lat": 54.19, "lng": 37.62},
        "крымский полуостров": {"lat": 45.30, "lng": 34.20},
        "калининград": {"lat": 54.71, "lng": 20.51},
        "кенигсберг": {"lat": 54.71, "lng": 20.51},
        "урал": {"lat": 58.00, "lng": 60.00},
        "сибирь": {"lat": 60.00, "lng": 90.00},
        "кавказ": {"lat": 43.00, "lng": 44.00},
        "дальний восток": {"lat": 50.00, "lng": 135.00},
        "балтийское море": {"lat": 57.00, "lng": 20.00},
        "черное море": {"lat": 44.00, "lng": 35.00},
        "каспийское море": {"lat": 42.00, "lng": 50.00},
        "финский залив": {"lat": 60.00, "lng": 28.00},
        "беларусь": {"lat": 53.90, "lng": 27.57},
        "минск": {"lat": 53.90, "lng": 27.57},
        "украина": {"lat": 50.45, "lng": 30.52},
        "грузия": {"lat": 41.69, "lng": 44.80},
        "тбилиси": {"lat": 41.69, "lng": 44.80},
        "армения": {"lat": 40.18, "lng": 44.51},
        "ереван": {"lat": 40.18, "lng": 44.51},
        "литва": {"lat": 54.69, "lng": 25.27},
        "вильнюс": {"lat": 54.69, "lng": 25.27},
        "латвия": {"lat": 56.95, "lng": 24.11},
        "рига": {"lat": 56.95, "lng": 24.11},
        "эстония": {"lat": 59.44, "lng": 24.75},
        "таллин": {"lat": 59.44, "lng": 24.75},
        "молдавия": {"lat": 47.01, "lng": 28.86},
        "кишинев": {"lat": 47.01, "lng": 28.86},
        "азербайджан": {"lat": 40.41, "lng": 49.87},
        "баку": {"lat": 40.41, "lng": 49.87},
        "казахстан": {"lat": 51.17, "lng": 71.44},
        "астана": {"lat": 51.17, "lng": 71.44},
        "узбекистан": {"lat": 41.31, "lng": 69.24},
        "ташкент": {"lat": 41.31, "lng": 69.24},
        "туркменистан": {"lat": 37.95, "lng": 58.38},
        "ашхабад": {"lat": 37.95, "lng": 58.38},
        "таджикистан": {"lat": 38.56, "lng": 68.77},
        "душанбе": {"lat": 38.56, "lng": 68.77},
        "киргизия": {"lat": 42.87, "lng": 74.60},
        "бишкек": {"lat": 42.87, "lng": 74.60},
        "константинополь": {"lat": 41.01, "lng": 28.97},
        "стамбул": {"lat": 41.01, "lng": 28.97},
        "париж": {"lat": 48.86, "lng": 2.35},
        "лондон": {"lat": 51.51, "lng": -0.13},
        "вена": {"lat": 48.21, "lng": 16.37},
        "европа": {"lat": 50.00, "lng": 10.00},
        "россия": {"lat": 55.75, "lng": 37.62},
        "московская область": {"lat": 55.75, "lng": 37.00},
        "ленинградская область": {"lat": 59.50, "lng": 30.00},
        "река нева": {"lat": 59.94, "lng": 30.31},
        "река волга": {"lat": 55.00, "lng": 46.00},
        "река днепр": {"lat": 50.45, "lng": 30.52},
        "река дон": {"lat": 47.23, "lng": 39.72}
    }
    
    if not location_name or location_name.lower() == "не указано":
        return None
        
    location_key = location_name.lower()
    
    # Прямое совпадение
    if location_key in location_coords:
        return location_coords[location_key]
    
    # Поиск частичного совпадения
    for key in location_coords:
        if key in location_key:
            return location_coords[key]
    
    # Поиск обратного частичного совпадения
    for key in location_coords:
        if location_key in key:
            return location_coords[key]
    
    # Возвращаем случайные координаты в пределах европейской части России
    return {
        "lat": 55.0 + random.uniform(-10, 10),
        "lng": 37.0 + random.uniform(-10, 15)
    }

def generate_database():
    """
    Генерирует полную базу данных исторических событий России.
    """
    print("Начало генерации базы данных исторических событий России...")
    
    # Проверяем наличие существующей базы данных
    existing_data = load_json(DB_FILE)
    if existing_data:
        print(f"Найдена существующая база данных с {len(existing_data.get('events', []))} событиями.")
        user_input = input("Хотите продолжить с существующей базой данных? (y/n): ")
        if user_input.lower() == 'y':
            print("Продолжаем с существующей базой данных.")
            database = existing_data
        else:
            print("Создаем новую базу данных.")
            database = {"events": [], "categories": EVENT_CATEGORIES}
    else:
        database = {"events": [], "categories": EVENT_CATEGORIES}
    
    # Получаем максимально полный список исторических тем России
    topics = generate_historical_topics()
    
    # Обрабатываем каждую тему
    total_events = 0
    for i, topic in enumerate(topics):
        try:
            print(f"Обработка темы {i+1}/{len(topics)}: {topic}")
            
            # Получаем события для текущей темы
            events = get_events_for_topic(topic)
            
            # Добавляем уникальный идентификатор каждому событию
            for event in events:
                # Пропускаем события без названия или даты
                if not event.get("title") or not event.get("date"):
                    continue
                
                # Создаем идентификатор на основе названия и даты
                event_id = hash_string(f"{event['title']}_{event['date']}")
                
                # Проверяем, нет ли уже такого события в базе данных
                is_duplicate = False
                for existing_event in database["events"]:
                    if "id" in existing_event and existing_event["id"] == event_id:
                        is_duplicate = True
                        break
                
                # Если это не дубликат, добавляем событие
                if not is_duplicate:
                    event["id"] = event_id
                    database["events"].append(event)
                    total_events += 1
            
            # Сохраняем промежуточные результаты
            if i % 5 == 0 or i == len(topics) - 1:
                print(f"Промежуточное сохранение базы данных: {total_events} событий.")
                save_json(database, DB_FILE)
            
        except Exception as e:
            print(f"Ошибка при обработке темы '{topic}': {e}")
            # Сохраняем то, что успели собрать
            save_json(database, DB_FILE)
    
    # Финальное сохранение
    print(f"Генерация базы данных завершена. Всего добавлено {total_events} событий.")
    save_json(database, DB_FILE)
    
    # Создаем резервную копию
    backup_file = f"history_db_generator/russian_history_database_backup_{int(time.time())}.json"
    save_json(database, backup_file)
    print(f"Создана резервная копия базы данных: {backup_file}")
    
    return database

if __name__ == "__main__":
    print("=== Генератор базы данных исторических событий России ===")
    print(f"Используется API ключ: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:]}")
    print(f"Файл базы данных: {DB_FILE}")
    
    try:
        # Проверяем работу API
        test_response = call_gemini_api("Тестовый запрос: ответь коротко 'API работает'")
        if "работает" in test_response.lower():
            print("API Gemini работает корректно.")
        else:
            print(f"Внимание: API вернул неожиданный ответ: {test_response}")
        
        # Запускаем генерацию базы данных
        generate_database()
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
