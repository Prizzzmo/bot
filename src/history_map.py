import os
import json
import random
import time
import threading
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
import concurrent.futures

class HistoryMap:
    """Класс для работы с картой исторических событий"""

    def __init__(self, logger):
        self.logger = logger
        self.events_file = "historical_events.json"
        self.events_data = self._load_events_data()
        self.map_cache = {}  # Кэш для сгенерированных карт
        self.cache_lock = threading.RLock()  # Блокировка для потокобезопасного доступа к кэшу
        self.max_cache_size = 10  # Максимальное количество элементов в кэше
        self.map_generation_lock = threading.Semaphore(2)  # Ограничиваем одновременную генерацию карт
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

    def _load_events_data(self):
        """Загружает данные о исторических событиях"""
        try:
            if os.path.exists(self.events_file):
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"events": [], "categories": []}
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке исторических событий: {e}")
            return {"events": [], "categories": []}

    def get_categories(self):
        """Возвращает список категорий исторических событий"""
        categories = self.events_data.get("categories", [])
        # Возвращаем копию для предотвращения изменений извне
        return categories.copy()

    def get_all_events(self):
        """Возвращает все исторические события"""
        events = self.events_data.get("events", [])
        return events.copy()

    def get_events_by_category(self, category):
        """Возвращает события по указанной категории"""
        events = self.get_all_events()
        if not events:
            return []

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
            # Обновляем данные в памяти
            self.events_data = data
            return new_id
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении события: {e}")
            return None

    def get_random_events(self, count=5):
        """Возвращает случайные исторические события"""
        events = self.get_all_events()
        return random.sample(events, min(count, len(events)))

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

            # Фильтрация по временному промежутку
            if timeframe and len(timeframe) == 2:
                start_year, end_year = timeframe
                filtered_events = []
                for event in display_events:
                    year_str = event.get('date', '').split('-')[0] if event.get('date') else ''
                    if year_str and year_str.isdigit():
                        year = int(year_str)
                        if start_year <= year <= end_year:
                            filtered_events.append(event)
                display_events = filtered_events

            return display_events
        except Exception as e:
            self.logger.error(f"Ошибка при получении событий: {e}")
            return []

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
        # Оптимизация: используем кэш для часто запрашиваемых карт
        cache_key = f"map_{category}_{hash(str(events))}"

        with self.cache_lock:
            # Проверяем кэш
            if cache_key in self.map_cache:
                cached_path, timestamp = self.map_cache[cache_key]
                # Проверяем существование файла и его возраст (не старше 30 минут)
                if os.path.exists(cached_path) and (time.time() - timestamp) < 1800:
                    self.logger.debug(f"Использую кэшированную карту: {cached_path}")
                    return cached_path

        # Ограничиваем количество одновременных генераций карт
        with self.map_generation_lock:
            try:
                # Получаем события для отображения
                display_events = self._get_display_events(category, events, timeframe)
                if not display_events:
                    self.logger.warning("Не найдено событий для отображения на карте")
                    # Возвращаем стандартную карту, если нет событий
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None

                # Создаем уникальное имя файла для изображения
                timestamp = int(time.time())
                map_image_path = f"generated_maps/map_{timestamp}.png"

                # Создаем карту с matplotlib с обработкой исключений
                try:
                    fig = Figure(figsize=(12, 10), dpi=150)
                    ax = fig.add_subplot(111)
                    
                    # Определяем границы карты России
                    ax.set_xlim(19, 190)  # Долгота от 19 до 190 градусов
                    ax.set_ylim(40, 83)   # Широта от 40 до 83 градусов
                    
                    # Устанавливаем заголовок
                    title = "Карта исторических событий России"
                    if category:
                        title += f" - {category}"
                    ax.set_title(title, fontsize=16, pad=20)
                    
                    # Устанавливаем подписи для осей
                    ax.set_xlabel('Долгота', fontsize=12)
                    ax.set_ylabel('Широта', fontsize=12)
                    
                    # Добавляем координатную сетку
                    ax.grid(True, alpha=0.3)
                except Exception as e:
                    self.logger.error(f"Ошибка при создании фигуры карты: {e}")
                    # Пробуем создать фигуру с более простыми параметрами
                    fig = Figure(figsize=(10, 8), dpi=100)
                    ax = fig.add_subplot(111)
                    ax.set_title("Карта исторических событий России", fontsize=14)
                    ax.grid(True)

                # Словарь для хранения цветов категорий
                category_colors = {}
                colors = list(mcolors.TABLEAU_COLORS)

                # Словарь для группировки событий по категориям для легенды
                categories_seen = set()

                # Список для хранения подписей событий
                footnotes = []

                # Отображаем события на карте
                for i, event in enumerate(display_events):
                    # Получаем координаты события
                    lat = event.get('location', {}).get('lat', 0)
                    lon = event.get('location', {}).get('lng', 0)
                    title = event.get('title', 'Неизвестное событие')
                    category = event.get('category', 'Прочее')
                    date = event.get('date', '').split('-')[0]  # Берем только год

                    # Определяем цвет для категории
                    if category not in category_colors:
                        color_idx = len(category_colors) % len(colors)
                        category_colors[category] = colors[color_idx]
                        categories_seen.add(category)

                    # Рисуем точку
                    ax.scatter(lon, lat, color=category_colors[category], s=100, 
                               edgecolor='white', linewidth=1, zorder=10)

                    # Добавляем номер события
                    ax.text(lon, lat+0.5, str(i+1), ha='center', va='center', fontsize=9,
                           color='white', fontweight='bold',
                           bbox=dict(facecolor=category_colors[category], alpha=0.8,
                                    boxstyle='round,pad=0.3', edgecolor='white'))

                    # Добавляем сноску с информацией о событии
                    footnotes.append(f"{i+1}. {title} ({date})")

                # Добавляем легенду с категориями
                if categories_seen:
                    from matplotlib.lines import Line2D
                    legend_elements = [
                        Line2D([0], [0], marker='o', color='w', markerfacecolor=category_colors[cat],
                              markersize=10, label=cat) for cat in categories_seen
                    ]
                    ax.legend(handles=legend_elements, loc='upper left', 
                             title="Категории событий", framealpha=0.7)

                # Определяем размер шрифта для сносок в зависимости от их количества
                footnote_fontsize = max(6, min(9, int(12 - 0.3 * len(footnotes))))

                # Добавляем сноски внизу изображения
                plt.figtext(0.5, 0.01, '\n'.join(footnotes), ha='center', 
                           fontsize=footnote_fontsize, wrap=True,
                           bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

                # Оптимизируем размеры для лучшего отображения
                plt.tight_layout(rect=[0, 0.1, 1, 0.95])

                # Сохраняем карту с расширенной обработкой ошибок
                try:
                    # Используем Fig.savefig вместо plt.savefig для большей надежности
                    fig.savefig(map_image_path, bbox_inches='tight', pad_inches=0.5)
                    
                    # Проверяем, что файл был успешно создан и имеет размер > 0
                    if os.path.exists(map_image_path) and os.path.getsize(map_image_path) > 0:
                        self.logger.info(f"Карта успешно сохранена в {map_image_path}")
                    else:
                        raise IOError("Файл карты создан, но имеет нулевой размер")
                except Exception as e:
                    self.logger.error(f"Ошибка при сохранении карты: {e}")
                    # Попытка создать карту с более низким разрешением
                    try:
                        fig.savefig(map_image_path, dpi=80, format='png')
                        if not os.path.exists(map_image_path):
                            raise IOError("Файл не создан после второй попытки")
                    except Exception as e2:
                        self.logger.error(f"Вторая попытка сохранения карты не удалась: {e2}")
                        return self._generate_simple_map(category, events, timeframe)
                finally:
                    # Всегда закрываем фигуру для освобождения ресурсов
                    plt.close(fig)

                # Сохраняем путь к карте в кэш
                with self.cache_lock:
                    # Удаляем старые элементы, если кэш переполнен
                    if len(self.map_cache) >= self.max_cache_size:
                        oldest_key = min(self.map_cache, key=lambda k: self.map_cache[k][1])
                        del self.map_cache[oldest_key]

                    self.map_cache[cache_key] = (map_image_path, time.time())

                self.logger.info(f"Карта успешно сгенерирована: {map_image_path}")
                return map_image_path

            except Exception as e:
                self.logger.error(f"Ошибка при генерации карты: {e}")
                # В случае ошибки, пробуем создать простую версию карты
                try:
                    return self._generate_simple_map(category, events, timeframe)
                except Exception as alt_error:
                    self.logger.error(f"Ошибка при генерации простой карты: {alt_error}")
                    # Возвращаем стандартную карту, если всё совсем плохо
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None

    def _generate_simple_map(self, category=None, events=None, timeframe=None):
        """
        Генерирует простую карту без использования сложных библиотек (резервный метод).

        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон

        Returns:
            str: Путь к сгенерированному изображению карты
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Получаем события для отображения
            display_events = self._get_display_events(category, events, timeframe)
            if not display_events:
                # Если нет событий, возвращаем стандартную карту
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None

            # Создаем уникальное имя файла
            timestamp = int(time.time())
            output_path = f"generated_maps/map_{timestamp}_simple.png"

            # Создаем базовое изображение светло-голубого цвета (цвет воды)
            width, height = 800, 600
            img = Image.new('RGB', (width, height), color=(224, 243, 255))
            draw = ImageDraw.Draw(img)

            # Рисуем приблизительные контуры России (упрощенные)
            # Создаем приблизительный контур суши (светло-бежевый цвет)
            land_color = (242, 242, 232)

            # Приблизительные координаты западной части России
            west_russia = [
                (100, 450), (200, 400), (300, 350), (350, 300), 
                (400, 250), (450, 200), (500, 150), (550, 150),
                (600, 200), (650, 250), (700, 300), (700, 400),
                (650, 450), (600, 500), (500, 550), (400, 560),
                (300, 550), (200, 520), (100, 500)
            ]

            # Рисуем контур суши
            draw.polygon(west_russia, fill=land_color, outline=(180, 180, 180))

            # Рисуем названия некоторых крупных городов
            cities = [
                ("Москва", 350, 350), 
                ("Санкт-Петербург", 300, 250),
                ("Новосибирск", 550, 350),
                ("Владивосток", 700, 350)
            ]

            # Пробуем загрузить шрифт
            try:
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                city_font = ImageFont.truetype(font_path, 12)
                title_font = ImageFont.truetype(font_path, 18)
                info_font = ImageFont.truetype(font_path, 10)
            except (OSError, IOError, Exception):
                self.logger.warning("Не удалось загрузить шрифт, используем стандартный")
                city_font = ImageFont.load_default()
                title_font = ImageFont.load_default()
                info_font = ImageFont.load_default()

            # Рисуем названия городов
            for city_name, x, y in cities:
                draw.text((x, y), city_name, fill=(100, 100, 100), font=city_font)

            # Преобразование географических координат в координаты изображения
            def geo_to_pixel(lat, lng):
                # Простое линейное преобразование
                x = int((lng - 19) / (190 - 19) * width)
                y = int(height - (lat - 40) / (83 - 40) * height)
                return x, y

            # Добавляем заголовок
            title = "Карта исторических событий России"
            if category:
                title += f" - {category}"

            # Центрируем текст заголовка
            title_width = len(title) * 10  # Приблизительная ширина текста
            title_x = (width - title_width) // 2
            draw.text((title_x, 20), title, fill=(0, 0, 0), font=title_font)

            # Рисуем события на карте
            colors = [
                (255, 0, 0), (0, 0, 255), (0, 128, 0), 
                (128, 0, 128), (255, 165, 0), (0, 128, 128)
            ]

            category_colors = {}
            footnotes = []

            for i, event in enumerate(display_events[:30]):  # Ограничиваем до 30 событий
                try:
                    lat = event.get('location', {}).get('lat', 0)
                    lng = event.get('location', {}).get('lng', 0)
                    title = event.get('title', 'Неизвестное событие')
                    category = event.get('category', 'Прочее')
                    date = event.get('date', '').split('-')[0]  # Берем только год

                    # Определяем цвет для категории
                    if category not in category_colors:
                        color_idx = len(category_colors) % len(colors)
                        category_colors[category] = colors[color_idx]

                    color = category_colors[category]

                    # Преобразуем координаты
                    x, y = geo_to_pixel(lat, lng)

                    # Рисуем точку
                    dot_radius = 6
                    draw.ellipse((x-dot_radius, y-dot_radius, x+dot_radius, y+dot_radius), 
                                fill=color, outline=(255, 255, 255))

                    # Рисуем номер события
                    draw.text((x, y-15), str(i+1), fill=(0, 0, 0), font=info_font)

                    # Добавляем сноску
                    footnotes.append(f"{i+1}. {title} ({date})")

                except Exception as e:
                    self.logger.warning(f"Ошибка при отображении события {event.get('title', '')}: {e}")

            # Добавляем легенду категорий
            legend_y = 60
            draw.text((20, legend_y), "Категории:", fill=(0, 0, 0), font=info_font)
            legend_y += 20

            for category, color in category_colors.items():
                draw.rectangle((20, legend_y, 30, legend_y+10), fill=color, outline=(0, 0, 0))
                draw.text((35, legend_y), category, fill=(0, 0, 0), font=info_font)
                legend_y += 15

            # Добавляем сноски
            footnote_y = height - 150

            # Создаем прямоугольник для сносок
            draw.rectangle((10, footnote_y-10, width-10, height-10), 
                          fill=(255, 255, 255, 220), outline=(0, 0, 0))

            # Определяем количество колонок в зависимости от числа сносок
            num_columns = 1
            if len(footnotes) > 15:
                num_columns = 2

            column_width = (width - 20) // num_columns
            lines_per_column = (height - footnote_y - 20) // 15

            for i, footnote in enumerate(footnotes):
                # Определяем, в какую колонку идет сноска
                column = i // lines_per_column
                if column >= num_columns:
                    break

                # Вычисляем позицию для сноски
                note_x = 20 + column * column_width
                note_y = footnote_y + (i % lines_per_column) * 15

                # Укорачиваем слишком длинные сноски
                max_length = column_width // 6
                if len(footnote) > max_length:
                    footnote = footnote[:max_length-3] + "..."

                draw.text((note_x, note_y), footnote, fill=(0, 0, 0), font=info_font)

            # Добавляем информацию о времени создания
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            draw.text((10, height-25), f"Сгенерировано: {timestamp_str}", 
                     fill=(100, 100, 100), font=info_font)

            # Сохраняем изображение
            img.save(output_path)
            self.logger.info(f"Создана простая карта: {output_path}")

            return output_path

        except Exception as e:
            self.logger.error(f"Ошибка при создании простой карты: {e}")
            # В случае полного провала возвращаем стандартную карту
            static_map_path = 'static/default_map.png'
            if os.path.exists(static_map_path):
                return static_map_path
            return None

    def generate_map_by_topic(self, topic):
        """
        Генерирует карту на основе пользовательского запроса/темы.

        Args:
            topic (str): Тема или запрос пользователя

        Returns:
            str: Путь к сгенерированному изображению карты или None в случае ошибки
        """
        try:
            self.logger.info(f"Генерация карты по запросу: {topic}")

            # Получаем все события
            all_events = self.get_all_events()
            if not all_events:
                self.logger.warning("Нет доступных событий для фильтрации")
                return None

            # Преобразуем тему в нижний регистр для поиска
            topic_lower = topic.lower()

            # Извлекаем ключевые слова из запроса
            keywords = [kw.strip() for kw in topic_lower.split() if len(kw.strip()) > 2]

            # Словарь для оценки релевантности событий
            relevance_scores = {}

            # Исторические периоды для поиска по временным рамкам
            historical_periods = {
                "древний": (800, 1200),
                "средневековый": (1200, 1500),
                "киевская русь": (862, 1240),
                "монгольское иго": (1237, 1480),
                "романовы": (1613, 1917),
                "российская империя": (1721, 1917),
                "советский": (1917, 1991),
                "современный": (1991, 2023)
            }

            # Проверяем на соответствие историческому периоду
            period_match = None
            for period, (start, end) in historical_periods.items():
                if period in topic_lower:
                    period_match = (start, end)
                    break

            # Оцениваем релевантность каждого события
            for event in all_events:
                event_id = event.get('id', 0)
                relevance_scores[event_id] = 0

                # Проверяем соответствие заголовка
                if 'title' in event:
                    title = event['title'].lower()
                    for keyword in keywords:
                        if keyword in title:
                            relevance_scores[event_id] += 10

                # Проверяем соответствие описания
                if 'description' in event:
                    description = event['description'].lower()
                    for keyword in keywords:
                        if keyword in description:
                            relevance_scores[event_id] += 5

                # Проверяем соответствие категории
                if 'category' in event:
                    category = event['category'].lower()
                    for keyword in keywords:
                        if keyword in category:
                            relevance_scores[event_id] += 8

                # Проверяем соответствие периоду
                if period_match and 'date' in event:
                    date_str = event['date'].split('-')[0] if '-' in event['date'] else event['date']
                    if date_str.isdigit():
                        year = int(date_str)
                        if period_match[0] <= year <= period_match[1]:
                            relevance_scores[event_id] += 15

            # Фильтруем события с ненулевой релевантностью
            relevant_events = [
                event for event in all_events 
                if relevance_scores.get(event.get('id', 0), 0) > 0
            ]

            # Сортируем по релевантности
            relevant_events.sort(
                key=lambda e: relevance_scores.get(e.get('id', 0), 0), 
                reverse=True
            )

            # Ограничиваем количество событий для лучшей читаемости
            max_events = 15
            display_events = relevant_events[:max_events]

            # Если релевантных событий недостаточно, добавляем случайные
            if len(display_events) < 5:
                remaining_events = [e for e in all_events if e not in display_events]
                random_events = random.sample(
                    remaining_events, 
                    min(max_events - len(display_events), len(remaining_events))
                )
                display_events.extend(random_events)

            # Генерируем карту
            self.logger.info(f"Найдено {len(display_events)} событий по запросу '{topic}'")
            return self.generate_map_image(events=display_events)

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

            deleted_count = 0
            for filename in os.listdir(map_directory):
                file_path = os.path.join(map_directory, filename)

                # Пропускаем директории
                if os.path.isdir(file_path):
                    continue

                # Проверяем возраст файла
                file_age = current_time - os.path.getmtime(file_path)
                max_age_seconds = max_age_hours * 3600

                # Проверяем, не используется ли файл в кэше
                is_cached = False
                with self.cache_lock:
                    is_cached = any(file_path == path for path, _ in self.map_cache.values())

                # Удаляем старые файлы, которые не в кэше
                if file_age > max_age_seconds and not is_cached:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        self.logger.debug(f"Не удалось удалить файл {file_path}: {e}")

            if deleted_count > 0:
                self.logger.info(f"Очищено {deleted_count} старых карт")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке старых карт: {e}")