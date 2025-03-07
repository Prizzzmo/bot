
import random
import json
import os
import time
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

class HistoryMap:
    """Класс для работы с интерактивной картой исторических событий"""

    def __init__(self, logger):
        self.logger = logger
        self.events_file = 'historical_events.json'
        self.events = None  # Ленивая загрузка данных
        self._events_loaded = False
        self._ensure_events_file_exists()
        
        # Создаем директорию для сохранения карт, если она не существует
        os.makedirs('generated_maps', exist_ok=True)

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

    def _get_display_events(self, category=None, events=None, timeframe=None):
        """Получает события для отображения на карте исходя из заданных параметров"""
        try:
            if category and isinstance(category, str):
                display_events = self.get_events_by_category(category)
                self.logger.info(f"Получено {len(display_events)} событий для категории {category}")
            elif events:
                if isinstance(events, list):
                    display_events = events
                else:
                    try:
                        ids = [int(id_) for id_ in str(events).split(',')]
                        display_events = [self.get_event_by_id(id_) for id_ in ids]
                        display_events = [event for event in display_events if event]
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке параметра events: {e}")
                        display_events = self.get_all_events()
            else:
                display_events = self.get_all_events()
            
            return display_events
        except Exception as e:
            self.logger.error(f"Ошибка при получении событий: {e}")
            return []

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
    
    def _create_html_template(self, title, display_events, category=None):
        """Создает HTML с картой на основе шаблона"""
        try:
            # Получаем категории
            categories = self.get_categories()
            
            # Настраиваем окружение Jinja2 с абсолютным путем к шаблонам
            templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
            env = Environment(loader=FileSystemLoader(templates_dir))
            template = env.get_template('map.html')
            
            self.logger.info(f"Использую директорию шаблонов: {templates_dir}")
            
            # Рендерим шаблон
            html_content = template.render(
                title=title,
                events=display_events,
                categories=categories,
                selected_category=category
            )
            
            return html_content
        except Exception as e:
            self.logger.error(f"Ошибка при создании HTML-шаблона: {e}")
            return None

    def generate_map_html(self, category=None, events=None, timeframe=None):
        """
        Генерирует HTML-файл карты с отмеченными историческими событиями.
        
        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы
            
        Returns:
            str: Путь к сгенерированному HTML-файлу карты или None в случае ошибки
        """
        # Получаем события для отображения
        display_events = self._get_display_events(category, events, timeframe)
        if not display_events:
            self.logger.warning("Не найдено событий для отображения на карте")
        
        # Создаем уникальное имя файла для карты
        timestamp = int(time.time())
        map_html_path = f"generated_maps/map_{timestamp}.html"
        
        # Заголовок
        title = "Карта исторических событий России"
        if category:
            title += f" - {category}"
        
        # Создаем HTML-контент
        html_content = self._create_html_template(title, display_events, category)
        if not html_content:
            return None
        
        try:
            # Сохраняем HTML-файл
            with open(map_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML-карта с событиями сгенерирована: {map_html_path}")
            return map_html_path
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении HTML-карты: {e}")
            return None

    def generate_map_image(self, category=None, events=None, timeframe=None):
        """
        Генерирует изображение карты с историческими событиями.
        
        В текущей версии использует статичное изображение или HTML-карту.
        
        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы
            
        Returns:
            str: Путь к сгенерированному изображению карты или None в случае ошибки
        """
        try:
            # В первую очередь пробуем создать изображение с помощью matplotlib
            image_path = self._generate_matplotlib_map(category, events, timeframe)
            if image_path:
                return image_path
                
            # Если не удалось создать изображение, возвращаем HTML-файл
            self.logger.warning("Не удалось создать изображение карты, возвращаем HTML-файл")
            return self.generate_map_html(category, events, timeframe)
        except Exception as e:
            self.logger.error(f"Ошибка при генерации изображения карты: {e}")
            
            # В случае ошибки возвращаем статичное изображение, если оно есть
            static_map_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                         'static', 'default_map.png')
            if os.path.exists(static_map_path):
                return static_map_path
                
            return None

    def _generate_matplotlib_map(self, category=None, events=None, timeframe=None):
        """
        Генерирует карту с помощью библиотеки matplotlib.
        
        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы
            
        Returns:
            str: Путь к сгенерированному изображению карты или None в случае ошибки
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure
            from mpl_toolkits.basemap import Basemap
            
            # Если библиотек нет, просто возвращаем None
            # Остальной код будет пытаться использовать другие методы
            
            # Получаем события для отображения
            display_events = self._get_display_events(category, events, timeframe)
            
            # Создаем уникальное имя файла для изображения
            timestamp = int(time.time())
            map_image_path = f"generated_maps/map_{timestamp}.png"
            
            # Заголовок
            title = "Карта исторических событий России"
            if category:
                title += f" - {category}"
                
            # Создаем фигуру
            fig = plt.figure(figsize=(12, 8))
            
            # Настраиваем проекцию карты России
            m = Basemap(projection='merc', 
                      llcrnrlat=41.0, llcrnrlon=19.0,
                      urcrnrlat=82.0, urcrnrlon=180.0,
                      resolution='l')
            
            # Добавляем контуры стран
            m.drawcountries(linewidth=0.5)
            m.drawcoastlines(linewidth=0.5)
            
            # Заполняем сушу и воду
            m.fillcontinents(color='#EEEEEE', lake_color='#CCCCFF')
            m.drawmapboundary(fill_color='#CCCCFF')
            
            # Добавляем события на карту
            for event in display_events:
                lat = event.get('location', {}).get('lat', 0)
                lon = event.get('location', {}).get('lng', 0)
                title = event.get('title', 'Неизвестное событие')
                
                x, y = m(lon, lat)
                plt.plot(x, y, 'ro', markersize=5)
                plt.text(x, y, title, fontsize=8, ha='right', va='bottom')
            
            # Добавляем заголовок
            plt.title(title)
            
            # Сохраняем изображение
            plt.savefig(map_image_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Изображение карты сгенерировано: {map_image_path}")
            return map_image_path
        except (ImportError, Exception) as e:
            self.logger.error(f"Не удалось сгенерировать изображение с помощью matplotlib: {e}")
            return None
            
    def clean_old_maps(self, max_age_hours=24):
        """
        Очищает старые файлы карт, созданные более указанного времени назад.
        
        Args:
            max_age_hours (int): Максимальный возраст файлов в часах
        """
        try:
            current_time = time.time()
            map_directory = 'generated_maps'
            
            if not os.path.exists(map_directory):
                return
                
            for filename in os.listdir(map_directory):
                file_path = os.path.join(map_directory, filename)
                
                # Пропускаем директории
                if os.path.isdir(file_path):
                    continue
                    
                # Проверяем возраст файла
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > (max_age_hours * 3600):  # Переводим часы в секунды
                    try:
                        os.remove(file_path)
                        self.logger.info(f"Удален старый файл карты: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Не удалось удалить старый файл карты {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке старых файлов карт: {e}")
