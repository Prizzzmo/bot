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
        return self.events_data

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
        return [event for event in events if event.get('category') == category]

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
        Генерирует URL для интерактивной карты с дополнительными опциями.

        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы

        Returns:
            str: URL для просмотра карты
        """
        base_url = "https://" + os.environ.get("REPL_SLUG", "history-map") + "." + os.environ.get("REPL_OWNER", "repl") + ".repl.co:8080/map"

        if category:
            return f"{base_url}?category={category}"

        if events:
            event_ids = ','.join(str(event['id']) for event in events)
            return f"{base_url}?events={event_ids}"

        if timeframe:
            start, end = timeframe
            return f"{base_url}?timeframe={start}-{end}"

        return base_url