
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
        
        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы
            
        Returns:
            str: Путь к сгенерированному изображению карты или None в случае ошибки
        """
        try:
            # Создаем изображение карты с помощью matplotlib
            image_path = self._generate_matplotlib_map(category, events, timeframe)
            if image_path:
                return image_path
            
            # Если не удалось создать изображение, возвращаем статичное изображение
            self.logger.warning("Не удалось создать изображение карты, возвращаем стандартную карту")
            
            # Возвращаем статичное изображение, если оно есть
            static_map_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                        'static', 'default_map.png')
            if os.path.exists(static_map_path):
                return static_map_path
            
            return None
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
        Генерирует карту с помощью библиотеки matplotlib с улучшенной детализацией.
        
        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы
            
        Returns:
            str: Путь к сгенерированному изображению карты или None в случае ошибки
        """
        try:
            # Импортируем и устанавливаем неинтерактивный бэкенд до импорта plt
            import matplotlib
            matplotlib.use('Agg')  # Используем Agg бэкенд, который не требует GUI
            
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure
            from mpl_toolkits.basemap import Basemap
            import numpy as np
            from matplotlib.patches import Polygon
            from matplotlib.collections import PatchCollection
            
            # Получаем события для отображения
            display_events = self._get_display_events(category, events, timeframe)
            
            # Создаем уникальное имя файла для изображения
            timestamp = int(time.time())
            map_image_path = f"generated_maps/map_{timestamp}.png"
            
            # Заголовок
            title = "Карта исторических событий России"
            if category:
                title += f" - {category}"
                
            # Создаем фигуру с большим размером для лучшей детализации
            fig = plt.figure(figsize=(16, 12), dpi=200)
            
            # Настраиваем проекцию карты России с повышенной детализацией
            m = Basemap(projection='merc', 
                      llcrnrlat=40.0, llcrnrlon=19.0,
                      urcrnrlat=83.0, urcrnrlon=190.0,
                      resolution='h')  # Высокое разрешение карты
            
            # Добавляем контуры стран с улучшенной видимостью
            m.drawcountries(linewidth=1.0, color='#444444')
            m.drawcoastlines(linewidth=1.0, color='#444444')
            
            # Добавляем больше географических деталей
            m.drawrivers(linewidth=0.5, color='#7EB2DD', linestyle='-')
            m.drawstates(linewidth=0.4, color='#999999', linestyle='--')
            
            # Добавляем подписи крупных городов
            major_cities = [
                ('Москва', 55.75, 37.62),
                ('Санкт-Петербург', 59.94, 30.31),
                ('Новосибирск', 55.01, 82.93),
                ('Екатеринбург', 56.84, 60.65),
                ('Нижний Новгород', 56.33, 44.00),
                ('Казань', 55.79, 49.12),
                ('Омск', 54.99, 73.37),
                ('Самара', 53.20, 50.15),
                ('Ростов-на-Дону', 47.23, 39.72),
                ('Уфа', 54.74, 55.97),
                ('Красноярск', 56.01, 92.87),
                ('Воронеж', 51.67, 39.18),
                ('Волгоград', 48.70, 44.51),
                ('Владивосток', 43.12, 131.89),
                ('Севастополь', 44.62, 33.53)
            ]
            
            for city_name, lat, lon in major_cities:
                x, y = m(lon, lat)
                # Отображаем только крупные города в пределах видимой области карты
                if (m.xmin <= x <= m.xmax) and (m.ymin <= y <= m.ymax):
                    plt.plot(x, y, 'ko', markersize=3, alpha=0.6)
                    plt.text(x, y, city_name, fontsize=7, ha='center', va='bottom', 
                            color='#444444', alpha=0.8, fontweight='light')
            
            # Заполняем сушу и воду более приятными цветами
            water_color = '#E0F3FF'  # Светло-голубой
            land_color = '#F2F2E8'   # Бежевый оттенок
            m.fillcontinents(color=land_color, lake_color=water_color)
            m.drawmapboundary(fill_color=water_color)
            
            # Добавляем более густую координатную сетку
            parallels = np.arange(40, 85, 5)
            meridians = np.arange(20, 190, 10)
            m.drawparallels(parallels, labels=[1,0,0,0], fontsize=8, linewidth=0.3, color='gray', alpha=0.5)
            m.drawmeridians(meridians, labels=[0,0,0,1], fontsize=8, linewidth=0.3, color='gray', alpha=0.5)
            
            # Расширенная палитра цветов с лучшей визуальной дифференциацией
            colors = ['#FF5252', '#448AFF', '#66BB6A', '#AB47BC', '#26C6DA', '#FFA726', '#78909C', 
                     '#EC407A', '#7E57C2', '#5C6BC0', '#42A5F5', '#26A69A', '#9CCC65', '#FFCA28']
            marker_styles = ['o', 's', '^', 'D', 'v', 'p', '*', 'h', '8', 'd']
            categories_seen = {}
            
            # Создаем словарь для сносок с обогащенным форматированием
            footnotes = []
            
            # Добавляем события на карту с улучшенным форматированием
            for i, event in enumerate(display_events, 1):
                lat = event.get('location', {}).get('lat', 0)
                lon = event.get('location', {}).get('lng', 0)
                title = event.get('title', 'Неизвестное событие')
                desc = event.get('description', '')
                event_category = event.get('category', 'Прочее')
                date = event.get('date', '')
                
                # Определяем цвет и маркер для категории
                if event_category not in categories_seen:
                    color_idx = len(categories_seen) % len(colors)
                    marker_idx = len(categories_seen) % len(marker_styles)
                    categories_seen[event_category] = {
                        'color': colors[color_idx],
                        'marker': marker_styles[marker_idx]
                    }
                style = categories_seen[event_category]
                
                x, y = m(lon, lat)
                
                # Рисуем точку события с улучшенной визуализацией
                plt.plot(x, y, marker=style['marker'], color=style['color'], 
                        markersize=9, markeredgewidth=1, markeredgecolor='white')
                
                # Добавляем номерную метку с улучшенным оформлением
                plt.text(x, y+70000, str(i), fontsize=9, ha='center', va='center',
                        color='white', fontweight='bold',
                        bbox=dict(facecolor=style['color'], alpha=0.8, boxstyle='round,pad=0.3', 
                                 edgecolor='white', linewidth=1))
                
                # Добавляем подробную информацию в сноску
                year = date.split('-')[0] if '-' in date else date
                footnote = f"{i}. {title} ({year}): {desc}"
                footnotes.append(footnote)
            
            # Добавляем заголовок с улучшенным форматированием
            plt.title(title, fontsize=16, pad=20, fontweight='bold')
            
            # Добавляем подзаголовок с количеством событий
            plt.figtext(0.5, 0.93, f"Показано событий: {len(display_events)}", 
                      fontsize=10, ha='center', color='#555555')
            
            # Добавляем улучшенную легенду категорий
            legend_elements = []
            import matplotlib.lines as mlines
            for cat, style in categories_seen.items():
                legend_elements.append(mlines.Line2D([0], [0], marker=style['marker'], color=style['color'], 
                                                   markersize=8, markeredgecolor='white', markeredgewidth=1,
                                                   label=cat, linestyle='None'))
            
            if legend_elements:
                legend = plt.legend(handles=legend_elements, loc='lower left', fontsize=8, 
                                   title="Категории событий", framealpha=0.9, edgecolor='#CCCCCC')
                legend.get_title().set_fontweight('bold')
            
            # Создаем рамку для пояснений внизу карты
            footnote_text = '\n'.join(footnotes)
            
            # Регулируем размер шрифта и формат сносок
            footnote_fontsize = max(4, min(10, int(15 - 0.5 * len(footnotes))))
            
            # Добавляем текстовое поле с примечаниями в рамке
            plt.figtext(0.5, 0.01, footnote_text, wrap=True, horizontalalignment='center', 
                      fontsize=footnote_fontsize, bbox=dict(facecolor='white', alpha=0.9, 
                                                          boxstyle='round,pad=0.4',
                                                          edgecolor='#CCCCCC', linewidth=1))
            
            # Добавляем авторскую подпись и дату создания
            current_date = datetime.now().strftime("%d.%m.%Y")
            plt.figtext(0.01, 0.01, f"Создано: {current_date}", fontsize=6, color='#888888')
            
            # Сохраняем изображение с повышенным разрешением и сжатием
            plt.tight_layout(rect=[0, 0.08, 1, 0.92])  # Настраиваем отступы для лучшего отображения
            plt.savefig(map_image_path, dpi=300, bbox_inches='tight', pad_inches=0.5, 
                       facecolor='white', edgecolor='none', transparent=False,
                       optimize=True, quality=90)
            plt.close()
            
            self.logger.info(f"Изображение карты с повышенной детализацией сгенерировано: {map_image_path}")
            return map_image_path
        except (ImportError, Exception) as e:
            self.logger.error(f"Не удалось сгенерировать изображение с помощью matplotlib: {e}")
            return None
            
    def generate_map_by_topic(self, topic):
        """
        Генерирует карту на основе пользовательского запроса/темы с улучшенным алгоритмом поиска.
        
        Args:
            topic (str): Тема или запрос пользователя
            
        Returns:
            str: Путь к сгенерированному изображению карты или None в случае ошибки
        """
        try:
            self.logger.info(f"Генерация детализированной карты по пользовательскому запросу: {topic}")
            
            # Получаем все события
            all_events = self.get_all_events()
            if not all_events:
                self.logger.warning("Нет доступных событий для фильтрации")
                return None
                
            # Преобразуем тему в нижний регистр для поиска
            topic_lower = topic.lower()
            
            # Извлекаем ключевые слова и выражения для более точного поиска
            keywords = [kw.strip() for kw in topic_lower.split() if len(kw.strip()) > 2]
            
            # Добавляем полную фразу для поиска точных совпадений
            if len(topic_lower.split()) > 1:
                keywords.append(topic_lower)
            
            # Словарь весов для разных типов совпадений
            weights = {
                'exact_title': 10,    # Точное совпадение в заголовке
                'partial_title': 5,   # Частичное совпадение в заголовке
                'exact_desc': 3,      # Точное совпадение в описании
                'partial_desc': 1,    # Частичное совпадение в описании
                'category': 4,        # Совпадение категории
                'date': 2             # Совпадение даты или периода
            }
            
            # Дополнительные словари для обработки синонимов, периодов и т.д.
            historical_periods = {
                "древний": ["862", "900", "1000"],
                "средневековый": ["1000", "1200", "1400", "1500"],
                "киевская русь": ["862", "1100", "1200"],
                "монгольское иго": ["1237", "1240", "1300", "1400"],
                "московское княжество": ["1300", "1400", "1500"],
                "романовы": ["1613", "1700", "1800", "1900", "1917"],
                "российская империя": ["1721", "1800", "1900", "1917"],
                "петр": ["1682", "1725"],
                "екатерина": ["1762", "1796"],
                "александр i": ["1801", "1825"],
                "николай i": ["1825", "1855"],
                "александр ii": ["1855", "1881"],
                "советский": ["1917", "1922", "1930", "1940", "1950", "1960", "1970", "1980", "1991"],
                "современный": ["1991", "2000", "2010", "2020"]
            }
            
            # Фильтруем события с улучшенным алгоритмом ранжирования
            relevant_events = []
            for event in all_events:
                event_title = event.get('title', '').lower()
                event_desc = event.get('description', '').lower()
                event_category = event.get('category', '').lower()
                event_date = event.get('date', '').lower()
                
                # Инициализируем счётчик релевантности
                relevance_score = 0
                match_details = []
                
                # Проверяем каждое ключевое слово
                for keyword in keywords:
                    # Проверка точного совпадения в заголовке
                    if keyword == event_title or keyword in event_title.split():
                        relevance_score += weights['exact_title']
                        match_details.append(f"Точное совпадение в заголовке: {keyword}")
                    # Проверка частичного совпадения в заголовке
                    elif keyword in event_title:
                        relevance_score += weights['partial_title']
                        match_details.append(f"Частичное совпадение в заголовке: {keyword}")
                    
                    # Проверка точного совпадения в описании
                    if keyword in event_desc.split():
                        relevance_score += weights['exact_desc']
                        match_details.append(f"Точное совпадение в описании: {keyword}")
                    # Проверка частичного совпадения в описании
                    elif keyword in event_desc:
                        relevance_score += weights['partial_desc']
                        match_details.append(f"Частичное совпадение в описании: {keyword}")
                    
                    # Проверка категории
                    if keyword == event_category or keyword in event_category:
                        relevance_score += weights['category']
                        match_details.append(f"Совпадение категории: {keyword}")
                    
                    # Проверка даты или периода
                    if keyword in event_date:
                        relevance_score += weights['date'] * 2  # Удваиваем вес для точной даты
                        match_details.append(f"Точное совпадение даты: {keyword}")
                    
                    # Проверка периодов
                    for period, years in historical_periods.items():
                        if keyword in period:
                            # Если год события попадает в указанный период
                            event_year = event_date.split('-')[0] if '-' in event_date else event_date
                            if event_year and event_year.isdigit():
                                for year in years:
                                    if int(year) - 50 <= int(event_year) <= int(year) + 50:
                                        relevance_score += weights['date']
                                        match_details.append(f"Событие из периода {period} ({event_year})")
                                        break
                
                # Если событие имеет ненулевую релевантность, добавляем его в список
                if relevance_score > 0:
                    event_copy = event.copy()  # Создаём копию события
                    event_copy['relevance'] = relevance_score
                    event_copy['match_details'] = match_details
                    relevant_events.append(event_copy)
            
            # Сортируем события по релевантности (от высшей к низшей)
            relevant_events.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            
            # Ограничиваем количество событий для лучшей читаемости карты
            max_events = 15  # Оптимальное количество для детализированной карты
            display_events = relevant_events[:max_events]
            
            # Если нет релевантных событий, используем случайные события
            if not display_events:
                self.logger.warning(f"Не найдено событий для темы: {topic}. Используем случайные события.")
                display_events = self.get_random_events(8)  # Увеличиваем до 8 для лучшей детализации
            
            # Добавляем информацию о запросе к событиям для заголовка карты
            for event in display_events:
                event['search_topic'] = topic
            
            # Генерируем изображение карты с найденными событиями
            map_image_path = self.generate_map_image(events=display_events)
            if map_image_path:
                self.logger.info(f"Сгенерирована детализированная карта по теме '{topic}' с {len(display_events)} событиями")
                return map_image_path
            else:
                self.logger.error(f"Не удалось сгенерировать карту по теме: {topic}")
                return None
        except Exception as e:
            self.logger.error(f"Ошибка при генерации карты по теме {topic}: {e}")
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
