import random
import json
import os
from datetime import datetime

class HistoryMap:
    """Класс для работы с интерактивной картой исторических событий"""

    def __init__(self, logger):
        self.logger = logger
        self.events_file = 'historical_events.json'
        self.events = None  # Ленивая загрузка данных
        self._events_loaded = False
        self._ensure_events_file_exists()

    def _ensure_events_file_exists(self):
        """Создает файл с историческими событиями, если он не существует"""
        if not os.path.exists(self.events_file):
            default_events = {
                "events": [
                    {
                        "id": 1,
                        "title": "Крещение Руси",
                        "date": "988",
                        "description": "Массовое крещение жителей Киева в водах Днепра князем Владимиром.",
                        "location": {"lat": 50.45, "lng": 30.52},
                        "category": "Культура и религия"
                    },
                    {
                        "id": 2,
                        "title": "Куликовская битва",
                        "date": "1380-09-08",
                        "description": "Сражение между русским войском во главе с московским князем Дмитрием Донским и войском Золотой Орды под командованием Мамая.",
                        "location": {"lat": 53.67, "lng": 38.67},
                        "category": "Войны и сражения"
                    },
                    {
                        "id": 3,
                        "title": "Основание Санкт-Петербурга",
                        "date": "1703-05-27",
                        "description": "Основание Петром I крепости Санкт-Питер-Бурх, ставшей впоследствии столицей Российской империи.",
                        "location": {"lat": 59.94, "lng": 30.31},
                        "category": "Становление государства"
                    },
                    {
                        "id": 4,
                        "title": "Бородинское сражение",
                        "date": "1812-09-07",
                        "description": "Крупнейшее сражение Отечественной войны 1812 года между русской армией под командованием М.И. Кутузова и французской армией Наполеона I.",
                        "location": {"lat": 55.52, "lng": 35.83},
                        "category": "Войны и сражения"
                    },
                    {
                        "id": 5,
                        "title": "Отмена крепостного права",
                        "date": "1861-03-03",
                        "description": "Манифест Александра II об отмене крепостного права, освободивший крестьян от крепостной зависимости.",
                        "location": {"lat": 55.75, "lng": 37.62},
                        "category": "Социальные реформы"
                    },
                    {
                        "id": 6,
                        "title": "Октябрьская революция",
                        "date": "1917-11-07",
                        "description": "Вооруженное восстание в Петрограде, в результате которого к власти пришли большевики.",
                        "location": {"lat": 59.94, "lng": 30.31},
                        "category": "Революции и перевороты"
                    },
                    {
                        "id": 7,
                        "title": "Начало Великой Отечественной войны",
                        "date": "1941-06-22",
                        "description": "Вторжение нацистской Германии на территорию СССР, начало Великой Отечественной войны.",
                        "location": {"lat": 52.1, "lng": 23.7},
                        "category": "Войны и сражения"
                    }
                ],
                "categories": [
                    "Войны и сражения", 
                    "Культура и религия", 
                    "Становление государства",
                    "Социальные реформы",
                    "Революции и перевороты",
                    "Научные достижения",
                    "Экономические события"
                ]
            }

            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(default_events, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Создан файл с историческими событиями: {self.events_file}")

    def _load_events(self):
        """Загружает события из JSON файла с отложенной загрузкой"""
        if self._events_loaded:
            return self.events

        try:
            with open('historical_events.json', 'r', encoding='utf-8') as f:
                self.events = json.load(f)
                self._events_loaded = True
                self.logger.info(f"Загружено {len(self.events)} исторических событий")
                return self.events
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке исторических событий: {e}")
            self.events = []
            self._events_loaded = True
            return self.events

    @property
    def events_data(self):
        """Свойство для получения данных событий с ленивой загрузкой"""
        if not self._events_loaded:
            return self._load_events()
        return self.events

    def get_all_events(self):
        """Возвращает все исторические события"""
        events_data = self.events_data
        if isinstance(events_data, dict) and 'events' in events_data:
            return events_data['events']
        return []

    def get_categories(self):
        """Возвращает список категорий событий"""
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('categories', [])
        except Exception as e:
            self.logger.error(f"Ошибка при чтении категорий: {e}")
            return []

    def get_events_by_category(self, category):
        """Возвращает события по указанной категории"""
        events = self.get_all_events()
        if not events:
            return []
            
        # Проверяем, что events - это список объектов, а не строк
        if all(isinstance(event, dict) for event in events):
            return [event for event in events if event.get('category') == category]
        else:
            self.logger.error(f"Неверный формат событий: получены не словари")
            return []

    def get_event_by_id(self, event_id):
        """Возвращает событие по ID"""
        events = self.get_all_events()
        for event in events:
            if event.get('id') == event_id:
                return event
        return None

    def add_event(self, title, date, description, location, category):
        """Добавляет новое историческое событие"""
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            events = data.get('events', [])

            # Генерируем новый ID
            new_id = max([event.get('id', 0) for event in events], default=0) + 1

            # Создаем новое событие
            new_event = {
                "id": new_id,
                "title": title,
                "date": date,
                "description": description,
                "location": location,
                "category": category
            }

            # Добавляем событие в список
            events.append(new_event)
            data['events'] = events

            # Сохраняем обновленные данные
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Добавлено новое историческое событие: {title}")
            self._events_loaded = False #Invalidate cache
            return new_id
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении события: {e}")
            return None

    def get_random_events(self, count=3):
        """Возвращает случайные исторические события"""
        events = self.get_all_events()
        if len(events) <= count:
            return events
        return random.sample(events, count)

    def generate_map_url(self, category=None, events=None, timeframe=None):
        """
        Генерирует URL для описания карты (веб-сервер удален).
        
        Данная функция сохранена для совместимости. В текущей версии 
        вместо URL следует использовать функцию generate_map_image.

        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы

        Returns:
            str: Информационное сообщение о карте
        """
        from src.web_server import get_base_url
        base_url = get_base_url()
        
        message = f"Карта исторических событий теперь доступна только в виде изображений."
        
        if category:
            return f"{message} Выбранная категория: {category}"
        if events:
            if isinstance(events, list):
                event_count = len(events)
            else:
                event_count = len(events.split(','))
            return f"{message} Выбрано событий: {event_count}"
        if timeframe:
            start, end = timeframe
            return f"{message} Временной диапазон: {start}-{end}"
            
        return message
        
    def generate_map_image(self, category=None, events=None, timeframe=None):
        """
        Генерирует изображение карты с отмеченными историческими событиями.
        
        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы
            
        Returns:
            str: Путь к сгенерированному изображению карты
        """
        import folium
        import tempfile
        import io
        import time
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from PIL import Image
        
        # Определяем события для отображения на карте
        if category:
            display_events = self.get_events_by_category(category)
        elif events:
            if isinstance(events, list):
                display_events = events
            else:
                try:
                    ids = [int(id_) for id_ in events.split(',')]
                    display_events = [self.get_event_by_id(id_) for id_ in ids]
                    display_events = [event for event in display_events if event]
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке параметра events: {e}")
                    display_events = self.get_all_events()
        else:
            display_events = self.get_all_events()
            
        # Создаем объект карты с центром на территории России
        map_obj = folium.Map(location=[65, 97], zoom_start=3, tiles='OpenStreetMap')
        
        # Добавляем маркеры для каждого события
        for event in display_events:
            if 'location' in event and 'lat' in event['location'] and 'lng' in event['location']:
                # Создаем всплывающее окно с информацией о событии
                popup_html = f"""
                <div style="width: 200px;">
                    <h3>{event['title']}</h3>
                    <p><strong>Дата:</strong> {event['date']}</p>
                    <p><strong>Категория:</strong> {event['category']}</p>
                    <p>{event['description']}</p>
                </div>
                """
                
                # Добавляем маркер на карту
                folium.Marker(
                    location=[event['location']['lat'], event['location']['lng']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=event['title']
                ).add_to(map_obj)
                
        # Создаем временный файл для сохранения HTML-карты
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            map_path = tmp.name
            map_obj.save(map_path)
        
        # Настраиваем опции запуска Chrome в headless-режиме
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1200,800")
        
        # Создаем driver для WebKit
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Открываем HTML-файл с картой
            driver.get(f"file://{map_path}")
            
            # Даем время для полной загрузки карты
            time.sleep(2)
            
            # Создаем директорию для сохранения карт, если она не существует
            os.makedirs('generated_maps', exist_ok=True)
            
            # Создаем уникальное имя файла для карты
            timestamp = int(time.time())
            map_image_path = f"generated_maps/map_{timestamp}.png"
            
            # Делаем скриншот карты
            driver.save_screenshot(map_image_path)
            
            # Обрезаем изображение для удаления ненужных элементов
            img = Image.open(map_image_path)
            img = img.crop((0, 0, 1200, 800))  # Обрезаем до размера 1200x800
            img.save(map_image_path)
            
            # Закрываем драйвер
            driver.quit()
            
            # Удаляем временный HTML-файл
            os.unlink(map_path)
            
            self.logger.info(f"Изображение карты успешно сгенерировано: {map_image_path}")
            return map_image_path
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации изображения карты: {e}")
            # В случае ошибки возвращаем None
            return None