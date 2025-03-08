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
from src.base_service import BaseService

class HistoryMap(BaseService):
    """Класс для работы с картой исторических событий"""

    def __init__(self, logger):
        super().__init__(logger)
        self.events_file = "historical_events.json"
        self.events_data = self._load_events_data()
        self.map_cache = {}  # Кэш для сгенерированных карт
        self.cache_lock = threading.RLock()  # Блокировка для потокобезопасного доступа к кэшу
        self.max_cache_size = 10  # Максимальное количество элементов в кэше
        self.map_generation_lock = threading.Semaphore(2)  # Ограничиваем одновременную генерацию карт
        self._ensure_events_file_exists()

        # Создаем директорию для сохранения карт, если она не существует
        os.makedirs('generated_maps', exist_ok=True)

    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.

        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            # Проверяем доступность файла исторических событий и создаем его, если необходимо
            self._ensure_events_file_exists()

            # Проверяем, что данные событий загружены
            if not self.events_data or not self.events_data.get("events"):
                self.events_data = self._load_events_data()
                if not self.events_data or not self.events_data.get("events"):
                    self._logger.warning("Не удалось загрузить данные о исторических событиях")
                    # Продолжаем работу, т.к. метод _ensure_events_file_exists создаст файл с дефолтными данными

            # Проверяем доступность директории для карт
            if not os.path.exists('generated_maps'):
                os.makedirs('generated_maps', exist_ok=True)
                self._logger.info("Создана директория для карт: generated_maps")

            # Создаем директорию для статических ресурсов, если она не существует
            if not os.path.exists('static'):
                os.makedirs('static', exist_ok=True)
                self._logger.info("Создана директория для статических ресурсов: static")

            return True
        except Exception as e:
            self._logger.error(f"Ошибка при инициализации HistoryMap: {e}")
            return False

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

            self._logger.info(f"Создан файл с историческими событиями: {self.events_file}")

    def _load_events_data(self):
        """Загружает данные о исторических событиях"""
        try:
            if os.path.exists(self.events_file):
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"events": [], "categories": []}
        except Exception as e:
            self._logger.error(f"Ошибка при загрузке исторических событий: {e}")
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

            self._logger.info(f"Добавлено новое историческое событие: {title}")
            # Обновляем данные в памяти
            self.events_data = data
            return new_id
        except Exception as e:
            self._logger.error(f"Ошибка при добавлении события: {e}")
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
                self._logger.info(f"Получено {len(display_events)} событий для категории {category}")
            elif events:
                if isinstance(events, list):
                    display_events = events
                else:
                    try:
                        ids = [int(id_) for id_ in str(events).split(',')]
                        display_events = [self.get_event_by_id(id_) for id_ in ids]
                        display_events = [event for event in display_events if event]
                    except Exception as e:
                        self._logger.error(f"Ошибка при обработке параметра events: {e}")
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
            self._logger.error(f"Ошибка при получении событий: {e}")
            return []

    def generate_map_image(self, category=None, events=None, timeframe=None):
        """
        Генерирует изображение карты с историческими событиями с расширенными проверками.

        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон в формате (начало, конец) - годы

        Returns:
            str: Путь к сгенерированному изображению карты или None в случае ошибки
        """
        # Создаем директорию для карт, если она не существует
        if not os.path.exists('generated_maps'):
            try:
                os.makedirs('generated_maps', exist_ok=True)
                self._logger.info("Создана директория для карт: generated_maps")
            except Exception as e:
                self._logger.error(f"Ошибка при создании директории для карт: {e}")
                # Если не удалось создать директорию, сразу возвращаем стандартную карту
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None

        # Оптимизация: используем кэш для часто запрашиваемых карт
        cache_key = f"map_{category}_{hash(str(events))}"

        with self.cache_lock:
            # Проверяем кэш
            if cache_key in self.map_cache:
                cached_path, timestamp = self.map_cache[cache_key]
                # Проверяем существование файла и его возраст (не старше 30 минут)
                if os.path.exists(cached_path) and (time.time() - timestamp) < 1800:
                    # Дополнительная проверка целостности файла
                    try:
                        if os.path.getsize(cached_path) > 0:
                            with open(cached_path, 'rb') as test_file:
                                # Проверяем первые байты файла
                                header = test_file.read(8)
                                # Проверка формата PNG (начинается с ‰PNG)
                                if header.startswith(b'\x89PNG'):
                                    self._logger.debug(f"Использую кэшированную карту: {cached_path}")
                                    return cached_path
                                else:
                                    self._logger.warning(f"Кэшированная карта повреждена: {cached_path}")
                    except Exception as e:
                        self._logger.warning(f"Ошибка при проверке кэшированной карты: {e}")
                    # Если карта повреждена, продолжаем генерацию новой

        # Ограничиваем количество одновременных генераций карт
        try:
            # Устанавливаем таймаут для получения семафора
            acquired = self.map_generation_lock.acquire(timeout=10)
            if not acquired:
                self._logger.warning("Превышен лимит одновременных генераций карт, используем стандартную карту")
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None
        except Exception as e:
            self._logger.error(f"Ошибка при ожидании очереди генерации карты: {e}")
            static_map_path = 'static/default_map.png'
            if os.path.exists(static_map_path):
                return static_map_path
            return None

        try:
            # Получаем события для отображения с проверкой результата
            try:
                display_events = self._get_display_events(category, events, timeframe)
                if not display_events:
                    self._logger.warning(f"Не найдено событий для категории: {category}")
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None
            except Exception as event_error:
                self._logger.error(f"Ошибка при получении событий: {event_error}")
                # Пытаемся использовать случайные события вместо запрошенных
                try:
                    display_events = self.get_random_events(8)
                    if not display_events:
                        raise ValueError("Не удалось получить случайные события")
                except Exception as random_error:
                    self._logger.error(f"Не удалось получить случайные события: {random_error}")
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None

            # Создаем уникальное имя файла для изображения с проверкой на доступность
                timestamp = int(time.time())
                map_image_path = f"generated_maps/map_{timestamp}.png"

            # Проверяем, что директория существует и доступна для записи
            if not os.access('generated_maps', os.W_OK):
                self._logger.error("Директория generated_maps недоступна для записи")
                # Пробуем создать директорию с другим именем
                try:
                    os.makedirs('temp_maps', exist_ok=True)
                    map_image_path = f"temp_maps/map_{timestamp}.png"
                except Exception as dir_error:
                    self._logger.error(f"Ошибка при создании альтернативной директории: {dir_error}")
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None

            # Проверяем доступность модулей для работы с изображениями
            matplotlib_available = True
            try:
                import matplotlib.pyplot as plt
                from matplotlib.figure import Figure
                import matplotlib.colors as mcolors
            except ImportError as imp_error:
                self._logger.error(f"Не удалось импортировать модули matplotlib: {imp_error}")
                matplotlib_available = False

            # Если matplotlib не доступен, сразу переходим к простой версии
            if not matplotlib_available:
                return self._generate_simple_map(category, events, timeframe)

            # Создаем карту с matplotlib с детальной обработкой исключений
            try:
                # Устанавливаем параметры фигуры с защитой от исключений
                fig_params = {}
                try:
                    fig_params = {'figsize': (12, 10), 'dpi': 150}
                    fig = Figure(**fig_params)
                except Exception as fig_error:
                    self._logger.warning(f"Ошибка при создании фигуры с параметрами {fig_params}: {fig_error}")
                    fig_params = {'figsize': (10, 8), 'dpi': 100}
                    fig = Figure(**fig_params)

                ax = fig.add_subplot(111)

                # Определяем границы карты России с защитой от некорректных данных
                try:
                    ax.set_xlim(19, 190)  # Долгота от 19 до 190 градусов
                    ax.set_ylim(40, 83)   # Широта от 40 до 83 градусов
                except Exception as e:
                    self._logger.warning(f"Ошибка при установке границ карты: {e}")
                    # Устанавливаем более стандартные границы
                    ax.set_xlim(0, 200)
                    ax.set_ylim(0, 100)

                # Устанавливаем заголовок с защитой от длинных строк
                title = "Карта исторических событий России"
                if category:
                    # Обрезаем слишком длинную категорию
                    if len(category) > 50:
                        category = category[:47] + "..."
                    title += f" - {category}"

                try:
                    ax.set_title(title, fontsize=16, pad=20)
                    ax.set_xlabel('Долгота', fontsize=12)
                    ax.set_ylabel('Широта', fontsize=12)
                    ax.grid(True, alpha=0.3)
                except Exception as e:
                    self._logger.warning(f"Ошибка при настройке осей и заголовка: {e}")
                    # Устанавливаем минимальные настройки
                    ax.set_title("Карта исторических событий")
                    ax.grid(True)
            except Exception as e:
                self._logger.error(f"Критическая ошибка при создании фигуры карты: {e}")
                # Пробуем создать фигуру с минимальными параметрами
                try:
                    fig = Figure(figsize=(8, 6), dpi=80)
                    ax = fig.add_subplot(111)
                    ax.set_title("Карта исторических событий России")
                    ax.grid(True)
                except Exception as fallback_error:
                    self._logger.error(f"Не удалось создать даже упрощенную фигуру: {fallback_error}")
                    return self._generate_simple_map(category, events, timeframe)

            # Словарь для хранения цветов категорий
            category_colors = {}
            # Безопасное получение списка цветов
            try:
                colors = list(mcolors.TABLEAU_COLORS)
                if not colors:
                    raise ValueError("Пустой список цветов")
            except Exception as color_error:
                self._logger.warning(f"Ошибка при получении цветов: {color_error}")
                # Создаем базовые цвета в формате RGB
                colors = [(1, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 1), (1, 1, 0), (0, 1, 1)]

            # Словарь для группировки событий по категориям для легенды
            categories_seen = set()

            # Список для хранения подписей событий
            footnotes = []

            # Ограничиваем количество событий для предотвращения переполнения
            max_events = min(len(display_events), 30)
            if len(display_events) > max_events:
                self._logger.info(f"Ограничиваем количество событий с {len(display_events)} до {max_events}")
                display_events = display_events[:max_events]

            # Отображаем события на карте с защитой от ошибок координат
            for i, event in enumerate(display_events):
                try:
                    # Получаем координаты события с проверкой
                    location = event.get('location', {})
                    if not isinstance(location, dict):
                        self._logger.warning(f"Некорректный формат местоположения для события {event.get('id', '?')}")
                        continue

                    lat = location.get('lat', 0)
                    lon = location.get('lng', 0)

                    # Пропускаем точки с некорректными координатами
                    if not (40 <= lat <= 83 and 19 <= lon <= 190):
                        self._logger.warning(f"Координаты события {event.get('id', '?')} вне допустимого диапазона: lat={lat}, lon={lon}")
                        continue

                    title = event.get('title', 'Неизвестное событие')
                    # Обрезаем слишком длинные заголовки
                    if len(title) > 60:
                        title = title[:57] + "..."

                    category = event.get('category', 'Прочее')
                    date = ""

                    # Безопасное извлечение даты
                    try:
                        date_str = event.get('date', '')
                        if date_str:
                            date = date_str.split('-')[0]  # Берем только год
                    except Exception as date_error:
                        self._logger.warning(f"Ошибка при обработке даты события {event.get('id', '?')}: {date_error}")
                        date = "?"

                    # Определяем цвет для категории
                    if category not in category_colors:
                        color_idx = len(category_colors) % len(colors)
                        category_colors[category] = colors[color_idx]
                        categories_seen.add(category)

                    # Рисуем точку с защитой от ошибок
                    try:
                        ax.scatter(lon, lat, color=category_colors[category], s=100, 
                                  edgecolor='white', linewidth=1, zorder=10)

                        # Добавляем номер события
                        ax.text(lon, lat+0.5, str(i+1), ha='center', va='center', fontsize=9,
                              color='white', fontweight='bold',
                              bbox=dict(facecolor=category_colors[category], alpha=0.8,
                                       boxstyle='round,pad=0.3', edgecolor='white'))
                    except Exception as plot_error:
                        self._logger.warning(f"Ошибка при отрисовке события {event.get('id', '?')}: {plot_error}")
                        continue

                    # Добавляем сноску с информацией о событии
                    footnote_text = f"{i+1}. {title}"
                    if date:
                        footnote_text += f" ({date})"
                    footnotes.append(footnote_text)
                except Exception as event_plot_error:
                    self._logger.warning(f"Ошибка при обработке события {i}: {event_plot_error}")
                    continue

            # Проверяем, есть ли успешно обработанные события
            if not footnotes:
                self._logger.warning("Не удалось обработать ни одно событие")
                return self._generate_simple_map(category, events, timeframe)

            # Добавляем легенду с категориями
            if categories_seen:
                try:
                    from matplotlib.lines import Line2D
                    legend_elements = [
                        Line2D([0], [0], marker='o', color='w', markerfacecolor=category_colors[cat],
                              markersize=10, label=cat) for cat in categories_seen
                    ]
                    ax.legend(handles=legend_elements, loc='upper left', 
                             title="Категории событий", framealpha=0.7)
                except Exception as legend_error:
                    self._logger.warning(f"Ошибка при создании легенды: {legend_error}")

            # Определяем размер шрифта для сносок в зависимости от их количества
            try:
                footnote_fontsize = max(6, min(9, int(12 - 0.3 * len(footnotes))))

                # Добавляем сноски внизу изображения с более надежным методом
                if hasattr(fig, 'text'):
                    fig.text(0.5, 0.01, '\n'.join(footnotes), ha='center', 
                            fontsize=footnote_fontsize,
                            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
                else:
                    # Альтернативный метод
                    plt.figtext(0.5, 0.01, '\n'.join(footnotes), ha='center', 
                               fontsize=footnote_fontsize,
                               bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
            except Exception as footnote_error:
                self._logger.warning(f"Ошибка при добавлении сносок: {footnote_error}")

            # Оптимизируем размеры для лучшего отображения
            try:
                fig.tight_layout(rect=[0, 0.1, 1, 0.95])
            except Exception as layout_error:
                self._logger.warning(f"Ошибка при оптимизации размеров: {layout_error}")

            # Защищенная система сохранения карты с множественными резервными методами
            save_success = False
            for attempt, dpi in enumerate([150, 100, 80, 60], 1):
                if save_success:
                    break

                try:
                    self._logger.info(f"Попытка {attempt} сохранения карты с DPI={dpi}")
                    # Используем Fig.savefig вместо plt.savefig для большей надежности
                    fig.savefig(map_image_path, bbox_inches='tight', pad_inches=0.5, dpi=dpi, format='png')

                    # Проверяем, что файл был успешно создан и имеет размер > 0
                    if os.path.exists(map_image_path) and os.path.getsize(map_image_path) > 0:
                        # Проверяем валидность PNG файла
                        try:
                            with open(map_image_path, 'rb') as test_file:
                                header = test_file.read(8)
                                if header.startswith(b'\x89PNG'):
                                    self._logger.info(f"Карта успешно сохранена в {map_image_path} (попытка {attempt})")
                                    save_success = True
                                else:
                                    self._logger.warning(f"Созданный файл не является валидным PNG (попытка {attempt})")
                                    os.remove(map_image_path)  # Удаляем поврежденный файл
                        except Exception as validate_error:
                            self._logger.warning(f"Ошибка при валидации файла карты: {validate_error}")
                    else:
                        self._logger.warning(f"Файл карты не создан или имеет нулевой размер (попытка {attempt})")
                except Exception as save_error:
                    self._logger.warning(f"Ошибка при сохранении карты (попытка {attempt}): {save_error}")

            # Освобождаем ресурсы matplotlib для предотвращения утечек памяти
            try:
                plt.close(fig)
            except Exception as close_error:
                self._logger.warning(f"Ошибка при закрытии фигуры: {close_error}")

            # Если не удалось сохранить, переходим к простой версии
            if not save_success:
                self._logger.warning("Не удалось сохранить карту используя matplotlib, переходим к резервному методу")
                return self._generate_simple_map(category, events, timeframe)

            # Сохраняем путь к карте в кэш только если успешно создали файл
            if save_success:
                with self.cache_lock:
                    # Удаляем старые элементы, если кэш переполнен
                    if len(self.map_cache) >= self.max_cache_size:
                        oldest_key = min(self.map_cache, key=lambda k: self.map_cache[k][1])
                        del self.map_cache[oldest_key]

                    self.map_cache[cache_key] = (map_image_path, time.time())

                self._logger.info(f"Карта успешно сгенерирована и сохранена в кэш: {map_image_path}")
                return map_image_path
            else:
                self._logger.error("Не удалось сохранить карту после всех попыток")
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None

        except Exception as e:
            self._logger.error(f"Критическая ошибка при генерации карты: {e}")
            # В случае ошибки, пробуем создать простую версию карты
            try:
                return self._generate_simple_map(category, events, timeframe)
            except Exception as alt_error:
                self._logger.error(f"Ошибка при генерации простой карты: {alt_error}")
                # Возвращаем стандартную карту, если всё совсем плохо
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None
        finally:
            # Важно всегда освобождать семафор
            try:
                self.map_generation_lock.release()
            except Exception as release_error:
                self._logger.error(f"Ошибка при освобождении блокировки: {release_error}")
                # Критическую ошибку здесь игнорируем, так как это финальная операция

    def _generate_simple_map(self, category=None, events=None, timeframe=None):
        """
        Генерирует простую карту без использования сложных библиотек (резервный метод).
        Улучшенная версия с дополнительными проверками и обработкой ошибок.

        Args:
            category (str, optional): Категория событий
            events (list, optional): Список конкретных событий
            timeframe (tuple, optional): Временной диапазон

        Returns:
            str: Путь к сгенерированному изображению карты
        """
        # Проверяем наличие директории для карт
        if not os.path.exists('generated_maps'):
            try:
                os.makedirs('generated_maps', exist_ok=True)
                self._logger.info("Создана директория для карт: generated_maps")
            except Exception as e:
                self._logger.error(f"Ошибка при создании директории для карт: {e}")
                # Пробуем создать альтернативную директорию
                try:
                    os.makedirs('temp_maps', exist_ok=True)
                except Exception:
                    # Если все попытки неуспешны, возвращаем стандартную карту
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None

        try:
            # Проверяем наличие PIL
            try:
                from PIL import Image, ImageDraw, ImageFont
            except ImportError as imp_error:
                self._logger.error(f"Не удалось импортировать модули PIL: {imp_error}")
                # Если PIL недоступен, возвращаем стандартную карту
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None

            # Получаем события для отображения с отловом ошибок
            try:
                display_events = self._get_display_events(category, events, timeframe)
                if not display_events:
                    # Пробуем получить случайные события вместо отсутствующих
                    display_events = self.get_random_events(5)
                    if not display_events:
                        self._logger.warning("Не удалось получить ни запрошенные, ни случайные события")
                        static_map_path = 'static/default_map.png'
                        if os.path.exists(static_map_path):
                            return static_map_path
                        return None

            # Создаем уникальное имя файла с проверкой доступности директории
            timestamp = int(time.time())
            if os.access('generated_maps', os.W_OK):
                output_path = f"generated_maps/map_{timestamp}_simple.png"
            elif os.path.exists('temp_maps') and os.access('temp_maps', os.W_OK):
                output_path = f"temp_maps/map_{timestamp}_simple.png"
            else:
                try:
                    # Пробуем создать временную директорию
                    os.makedirs('temp_maps', exist_ok=True)
                    output_path = f"temp_maps/map_{timestamp}_simple.png"
                except Exception as dir_error:
                    self._logger.error(f"Невозможно создать директорию для сохранения: {dir_error}")
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None

            # Создаем базовое изображение с защитой от ошибок
            try:
                width, height = 800, 600
                try:
                    img = Image.new('RGB', (width, height), color=(224, 243, 255))
                except Exception as img_error:
                    self._logger.warning(f"Ошибка при создании изображения: {img_error}")
                    # Пробуем создать изображение с другими параметрами
                    width, height = 640, 480
                    img = Image.new('RGB', (width, height), color=(224, 243, 255))

                draw = ImageDraw.Draw(img)
            except Exception as create_error:
                self._logger.error(f"Критическая ошибка при создании базового изображения: {create_error}")
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None

            # Рисуем приблизительные контуры России (упрощенные)
            try:
                # Создаем приблизительный контур суши (светло-бежевый цвет)
                land_color = (242, 242, 232)

                # Приблизительные координаты западной части России с масштабированием
                # относительно текущих размеров изображения
                scale_x = width / 800
                scale_y = height / 600

                # Масштабируем координаты
                west_russia = [
                    (int(100 * scale_x), int(450 * scale_y)), 
                    (int(200 * scale_x), int(400 * scale_y)),
                    (int(300 * scale_x), int(350 * scale_y)), 
                    (int(350 * scale_x), int(300 * scale_y)),
                    (int(400 * scale_x), int(250 * scale_y)), 
                    (int(450 * scale_x), int(200 * scale_y)),
                    (int(500 * scale_x), int(150 * scale_y)), 
                    (int(550 * scale_x), int(150 * scale_y)),
                    (int(600 * scale_x), int(200 * scale_y)), 
                    (int(650 * scale_x), int(250 * scale_y)),
                    (int(700 * scale_x), int(300 * scale_y)), 
                    (int(700 * scale_x), int(400 * scale_y)),
                    (int(650 * scale_x), int(450 * scale_y)), 
                    (int(600 * scale_x), int(500 * scale_y)),
                    (int(500 * scale_x), int(550 * scale_y)), 
                    (int(400 * scale_x), int(560 * scale_y)),
                    (int(300 * scale_x), int(550 * scale_y)), 
                    (int(200 * scale_x), int(520 * scale_y)),
                    (int(100 * scale_x), int(500 * scale_y))
                ]

                # Рисуем контур суши
                draw.polygon(west_russia, fill=land_color, outline=(180, 180, 180))
            except Exception as polygon_error:
                self._logger.warning(f"Ошибка при рисовании контура России: {polygon_error}")
                # В случае ошибки рисуем простой прямоугольник вместо контура
                try:
                    draw.rectangle([width//4, height//4, width*3//4, height*3//4], 
                                 fill=land_color, outline=(180, 180, 180))
                except Exception:
                    pass  # Игнорируем ошибку - карта будет без контура

            # Рисуем названия некоторых крупных городов с масштабированием координат
            cities = [
                ("Москва", int(350 * scale_x), int(350 * scale_y)), 
                ("Санкт-Петербург", int(300 * scale_x), int(250 * scale_y)),
                ("Новосибирск", int(550 * scale_x), int(350 * scale_y)),
                ("Владивосток", int(700 * scale_x), int(350 * scale_y))
            ]

            # Пробуем загрузить шрифт с несколькими альтернативными путями
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans.ttf"
            ]

            # Устанавливаем шрифты по умолчанию на случай ошибок
            city_font = None
            title_font = None
            info_font = None

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        city_font = ImageFont.truetype(font_path, 12)
                        title_font = ImageFont.truetype(font_path, 18)
                        info_font = ImageFont.truetype(font_path, 10)
                        self._logger.info(f"Успешно загружен шрифт: {font_path}")
                        break
                    except Exception as font_error:
                        self._logger.warning(f"Не удалось загрузить шрифт {font_path}: {font_error}")

            # Если не удалось загрузить шрифты, используем стандартный
            if city_font is None:
                self._logger.warning("Используем стандартный шрифт")
                city_font = ImageFont.load_default()
                title_font = ImageFont.load_default()
                info_font = ImageFont.load_default()

            # Рисуем названия городов с защитой от ошибок
            for city_name, x, y in cities:
                try:
                    draw.text((x, y), city_name, fill=(100, 100, 100), font=city_font)
                except Exception as city_error:
                    self._logger.warning(f"Ошибка при отрисовке города {city_name}: {city_error}")

            # Преобразование географических координат в координаты изображения
            # с защитой от деления на ноль и некорректных входных данных
            def geo_to_pixel(lat, lng):
                try:
                    # Проверяем входные данные
                    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                        return width // 2, height // 2  # Центр карты по умолчанию

                    # Простое линейное преобразование с защитой от деления на ноль
                    if 190 - 19 == 0:
                        x_ratio = 0
                    else:
                        x_ratio = (lng - 19) / (190 - 19)

                    if 83 - 40 == 0:
                        y_ratio = 0
                    else:
                        y_ratio = (lat - 40) / (83 - 40)

                    # Ограничиваем значения диапазоном 0-1
                    x_ratio = max(0, min(1, x_ratio))
                    y_ratio = max(0, min(1, y_ratio))

                    x = int(x_ratio * width)
                    y = int(height - y_ratio * height)

                    # Проверяем, что координаты находятся в пределах изображения
                    x = max(0, min(width-1, x))
                    y = max(0, min(height-1, y))

                    return x, y
                except Exception as coord_error:
                    self._logger.warning(f"Ошибка при преобразовании координат ({lat}, {lng}): {coord_error}")
                    return width // 2, height // 2  # Центр карты по умолчанию

            # Добавляем заголовок с защитой от ошибок
            try:
                title = "Карта исторических событий России"
                if category:
                    # Ограничиваем длину категории
                    if len(category) > 30:
                        category = category[:27] + "..."
                    title += f" - {category}"

                # Безопасное центрирование текста заголовка
                title_width = len(title) * 10  # Приблизительная ширина текста
                title_x = max(10, (width - title_width) // 2)

                # Если расчет центрирования дал некорректное значение
                if title_x < 0 or title_x > width:
                    title_x = 10

                draw.text((title_x, 20), title, fill=(0, 0, 0), font=title_font)
            except Exception as title_error:
                self._logger.warning(f"Ошибка при отрисовке заголовка: {title_error}")
                # Пробуем отрисовать упрощенный заголовок
                try:
                    draw.text((10, 10), "Карта исторических событий", fill=(0, 0, 0), font=title_font)
                except Exception:
                    pass  # Игнорируем ошибку - карта будет без заголовка

            # Создаем базовые цвета для категорий
            colors = [
                (255, 0, 0), (0, 0, 255), (0, 128, 0), 
                (128, 0, 128), (255, 165, 0), (0, 128, 128),
                (192, 192, 0), (128, 0, 0), (0, 0, 128)
            ]

            category_colors = {}
            footnotes = []

            # Ограничиваем количество событий для предотвращения переполнения
            max_events = min(len(display_events), 30)
            if len(display_events) > max_events:
                self._logger.info(f"Ограничиваем количество событий с {len(display_events)} до {max_events}")
                display_events = display_events[:max_events]

            # Отображаем события на карте с защитой от ошибок
            for i, event in enumerate(display_events):
                try:
                    # Извлекаем и проверяем данные события
                    location = event.get('location', {})
                    if not isinstance(location, dict):
                        self._logger.warning(f"Некорректный формат местоположения для события {event.get('id', '?')}")
                        continue

                    lat = location.get('lat', 0)
                    lng = location.get('lng', 0)

                    # Проверяем корректность координат
                    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                        self._logger.warning(f"Некорректные координаты события {event.get('id', '?')}: lat={lat}, lng={lng}")
                        continue

                    title = event.get('title', 'Неизвестное событие')
                    # Ограничиваем длину заголовка
                    if len(title) > 50:
                        title = title[:47] + "..."

                    category = event.get('category', 'Прочее')

                    # Безопасное извлечение даты
                    date = ""
                    try:
                        date_str = event.get('date', '')
                        if date_str:
                            if '-' in date_str:
                                date = date_str.split('-')[0]  # Берем только год
                            else:
                                date = date_str
                    except Exception as date_error:
                        self._logger.warning(f"Ошибка при обработке даты события {event.get('id', '?')}: {date_error}")
                        date = "?"

                    # Определяем цвет для категории
                    if category not in category_colors:
                        color_idx = len(category_colors) % len(colors)
                        category_colors[category] = colors[color_idx]

                    color = category_colors[category]

                    # Преобразуем координаты
                    x, y = geo_to_pixel(lat, lng)

                    # Рисуем точку
                    dot_radius = 6
                    try:
                        draw.ellipse((x-dot_radius, y-dot_radius, x+dot_radius, y+dot_radius), 
                                    fill=color, outline=(255, 255, 255))
                    except Exception as ellipse_error:
                        self._logger.warning(f"Ошибка при рисовании точки для события {event.get('id', '?')}: {ellipse_error}")
                        # Пробуем нарисовать прямоугольник вместо эллипса
                        try:
                            draw.rectangle((x-dot_radius, y-dot_radius, x+dot_radius, y+dot_radius), 
                                         fill=color, outline=(255, 255, 255))
                        except Exception:
                            continue  # Если и это не удалось, пропускаем точку

                    # Рисуем номер события
                    try:
                        draw.text((x, y-15), str(i+1), fill=(0, 0, 0), font=info_font)
                    except Exception as text_error:
                        self._logger.warning(f"Ошибка при добавлении номера события: {text_error}")

                    # Формируем текст сноски
                    footnote_text = f"{i+1}. {title}"
                    if date:
                        footnote_text += f" ({date})"
                    footnotes.append(footnote_text)

                except Exception as event_error:
                    self._logger.warning(f"Ошибка при обработке события {i}: {event_error}")
                    continue

            # Проверяем, обработали ли мы какие-либо события
            if not footnotes:
                self._logger.warning("Не удалось обработать ни одно событие")
                # Создаем сообщение об ошибке
                try:
                    draw.text((width//2-100, height//2), 
                             "Ошибка обработки событий", 
                             fill=(255, 0, 0), 
                             font=title_font)
                except Exception:
                    pass

                # Всё равно пытаемся сохранить карту
                try:
                    img.save(output_path)
                    self._logger.info(f"Создана пустая карта: {output_path}")
                    return output_path
                except Exception as save_error:
                    self._logger.error(f"Ошибка при сохранении пустой карты: {save_error}")
                    static_map_path = 'static/default_map.png'
                    if os.path.exists(static_map_path):
                        return static_map_path
                    return None

            # Добавляем легенду категорий
            try:
                legend_y = 60
                draw.text((20, legend_y), "Категории:", fill=(0, 0, 0), font=info_font)
                legend_y += 20

                # Ограничиваем количество категорий для отображения
                max_categories = min(len(category_colors), 8)
                category_items = list(category_colors.items())[:max_categories]

                for category, color in category_items:
                    # Ограничиваем длину названия категории
                    display_category = category
                    if len(display_category) > 25:
                        display_category = display_category[:22] + "..."

                    try:
                        draw.rectangle((20, legend_y, 30, legend_y+10), fill=color, outline=(0, 0, 0))
                        draw.text((35, legend_y), display_category, fill=(0, 0, 0), font=info_font)
                    except Exception as legend_item_error:
                        self._logger.warning(f"Ошибка при отрисовке элемента легенды '{display_category}': {legend_item_error}")

                    legend_y += 15

                    # Проверяем, не вышли ли мы за границы изображения
                    if legend_y > height - 200:
                        break

            except Exception as legend_error:
                self._logger.warning(f"Ошибка при создании легенды: {legend_error}")

            # Добавляем сноски
            try:
                footnote_y = height - 150

                # Создаем прямоугольник для сносок
                try:
                    draw.rectangle((10, footnote_y-10, width-10, height-10), 
                                 fill=(255, 255, 255, 220), outline=(0, 0, 0))
                except Exception as bg_error:
                    self._logger.warning(f"Ошибка при создании фона для сносок: {bg_error}")

                # Определяем количество колонок в зависимости от числа сносок
                num_columns = 1
                if len(footnotes) > 15:
                    num_columns = 2

                column_width = (width - 20) // num_columns
                lines_per_column = (height - footnote_y - 20) // 15

                # Защита от деления на ноль
                if lines_per_column <= 0:
                    lines_per_column = 1

                for i, footnote in enumerate(footnotes):
                    if i >= lines_per_column * num_columns:
                        # Достигли максимального количества отображаемых сносок
                        break

                    # Определяем, в какую колонку идет сноска
                    column = i // lines_per_column
                    if column >= num_columns:
                        break

                    # Вычисляем позицию для сноски
                    note_x = 20 + column * column_width
                    note_y = footnote_y + (i % lines_per_column) * 15

                    # Укорачиваем слишком длинные сноски
                    max_length = max(10, column_width // 6)  # Минимум 10 символов
                    if len(footnote) > max_length:
                        footnote = footnote[:max_length-3] + "..."

                    try:
                        draw.text((note_x, note_y), footnote, fill=(0, 0, 0), font=info_font)
                    except Exception as footnote_error:
                        self._logger.warning(f"Ошибка при добавлении сноски {i}: {footnote_error}")
            except Exception as footnotes_error:
                self._logger.warning(f"Ошибка при обработке сносок: {footnotes_error}")

            # Добавляем информацию о времени создания
            try:
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                draw.text((10, height-25), f"Сгенерировано: {timestamp_str}", 
                         fill=(100, 100, 100), font=info_font)
            except Exception as timestamp_error:
                self._logger.warning(f"Ошибка при добавлении временной метки: {timestamp_error}")

            # Сохраняем изображение с защитой от ошибок
            save_success = False
            try:
                # Сохраняем с разными форматами для надежности
                try:
                    img.save(output_path, format='PNG')
                    save_success = True
                except Exception as png_error:
                    self._logger.warning(f"Ошибка при сохранении PNG: {png_error}")
                    # Пробуем JPEG
                    try:
                        jpeg_path = output_path.replace('.png', '.jpg')
                        img.convert('RGB').save(jpeg_path, format='JPEG')
                        output_path = jpeg_path
                        save_success = True
                    except Exception as jpg_error:
                        self._logger.warning(f"Ошибка при сохранении JPEG: {jpg_error}")

                # Проверяем, что файл был успешно создан
                if save_success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    self._logger.info(f"Простая карта успешно создана: {output_path}")
                    return output_path
                else:
                    raise IOError("Файл карты не создан или имеет нулевой размер")
            except Exception as e:
                self._logger.error(f"Не удалось сохранить простую карту: {e}")
                static_map_path = 'static/default_map.png'
                if os.path.exists(static_map_path):
                    return static_map_path
                return None

        except Exception as e:
            self._logger.error(f"Критическая ошибка при создании простой карты: {e}")
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
            self._logger.info(f"Генерация карты по запросу: {topic}")

            # Получаем все события
            all_events = self.get_all_events()
            if not all_events:
                self._logger.warning("Нет доступных событий для фильтрации")
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
            self._logger.info(f"Найдено {len(display_events)} событий по запросу '{topic}'")
            return self.generate_map_image(events=display_events)

        except Exception as e:
            self._logger.error(f"Ошибка при генерации карты по теме {topic}: {e}")
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
                        self._logger.debug(f"Не удалось удалить файл {file_path}: {e}")

            if deleted_count > 0:
                self._logger.info(f"Очищено {deleted_count} старых карт")
        except Exception as e:
            self._logger.error(f"Ошибка при очистке старых карт: {e}")