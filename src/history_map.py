
"""
Модуль для создания и управления интерактивной исторической картой
"""

import os
import folium
import json
from src.logger import Logger

class HistoryMap:
    """
    Класс для создания и управления интерактивной исторической картой
    """
    
    def __init__(self, logger=None):
        """
        Инициализирует объект карты истории
        
        Args:
            logger (Logger, optional): Объект логгера для записи событий
        """
        self.logger = logger or Logger('history_map')
        self.base_map = None
        self.events_data = None
        self.output_dir = "generated_maps"
        self.ensure_output_dir()
        
    def ensure_output_dir(self):
        """Создает директорию для сохранения карт, если она не существует"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Создана директория для хранения карт: {self.output_dir}")
    
    def load_events(self, filepath="history_db_generator/russian_history_database.json"):
        """
        Загружает исторические события из JSON файла
        
        Args:
            filepath (str): Путь к файлу с историческими данными
            
        Returns:
            bool: True если данные успешно загружены, иначе False
        """
        try:
            if not os.path.exists(filepath):
                self.logger.error(f"Файл с историческими данными не найден: {filepath}")
                return False
                
            with open(filepath, 'r', encoding='utf-8') as file:
                self.events_data = json.load(file)
                
            event_count = len(self.events_data.get('events', []))
            self.logger.info(f"Загружено {event_count} исторических событий из {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке исторических данных: {e}")
            return False
    
    def create_base_map(self, center=[61.5240, 105.3188], zoom=4):
        """
        Создает базовую карту России
        
        Args:
            center (list): Координаты центра карты [широта, долгота]
            zoom (int): Начальный уровень масштабирования
            
        Returns:
            folium.Map: Объект карты
        """
        self.base_map = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles="CartoDB positron"
        )
        return self.base_map
    
    def filter_events_with_coordinates(self, events):
        """
        Фильтрует события, оставляя только те, которые имеют координаты
        
        Args:
            events (list): Список событий для фильтрации
            
        Returns:
            list: Отфильтрованный список событий с координатами
        """
        filtered = []
        for event in events:
            if 'location' in event and isinstance(event['location'], dict):
                if 'lat' in event['location'] and 'lng' in event['location']:
                    if event['location']['lat'] and event['location']['lng']:
                        filtered.append(event)
        
        self.logger.info(f"Отфильтровано {len(filtered)} событий с координатами из {len(events)}")
        return filtered
    
    def add_events_to_map(self, events_list=None, max_events=500):
        """
        Добавляет исторические события на карту
        
        Args:
            events_list (list, optional): Список событий для добавления на карту
            max_events (int): Максимальное количество событий для отображения
            
        Returns:
            folium.Map: Карта с добавленными событиями
        """
        if self.base_map is None:
            self.create_base_map()
            
        if events_list is None and self.events_data:
            events_list = self.events_data.get('events', [])
        
        if not events_list:
            self.logger.warning("Нет данных для отображения на карте")
            return self.base_map
        
        # Кластеризация маркеров для улучшения производительности
        marker_cluster = folium.plugins.MarkerCluster().add_to(self.base_map)
        
        # Фильтруем события с координатами
        events_with_coords = self.filter_events_with_coordinates(events_list)
        
        # Ограничиваем количество событий для отображения
        if len(events_with_coords) > max_events:
            self.logger.info(f"Ограничение количества отображаемых событий до {max_events}")
            events_with_coords = events_with_coords[:max_events]
        
        # Добавляем события на карту
        for event in events_with_coords:
            try:
                lat = float(event['location']['lat'])
                lng = float(event['location']['lng'])
                
                # Пропускаем события с невалидными координатами
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    continue
                
                # Создаем всплывающее окно с информацией о событии
                popup_html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 300px;">
                    <h3>{event['title']}</h3>
                    <p><strong>Дата:</strong> {event.get('date', 'Неизвестно')}</p>
                    <p><strong>Категория:</strong> {event.get('category', 'Неизвестно')}</p>
                    <p>{event.get('description', '')[:200]}...</p>
                </div>
                """
                
                # Определяем цвет маркера в зависимости от категории
                category_colors = {
                    'Война': 'red',
                    'Политика': 'blue',
                    'Культура': 'green',
                    'Наука': 'purple',
                    'Экономика': 'orange',
                    'Религия': 'darkblue'
                }
                
                color = category_colors.get(event.get('category', ''), 'gray')
                
                # Добавляем маркер на карту
                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=350),
                    tooltip=event['title'],
                    icon=folium.Icon(color=color)
                ).add_to(marker_cluster)
                
            except Exception as e:
                self.logger.error(f"Ошибка при добавлении события на карту: {e}")
                continue
                
        return self.base_map
    
    def save_map(self, filename="history_map.html"):
        """
        Сохраняет карту в HTML файл
        
        Args:
            filename (str): Имя файла для сохранения
            
        Returns:
            str: Путь к сохраненному файлу
        """
        if self.base_map is None:
            self.logger.error("Карта не была создана")
            return None
            
        filepath = os.path.join(self.output_dir, filename)
        try:
            self.base_map.save(filepath)
            self.logger.info(f"Карта успешно сохранена в {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении карты: {e}")
            return None
    
    def generate_full_map(self, output_filename="history_map.html"):
        """
        Создает и сохраняет полную карту с историческими событиями
        
        Args:
            output_filename (str): Имя файла для сохранения
            
        Returns:
            str: Путь к сохраненному файлу или None в случае ошибки
        """
        try:
            # Загружаем данные, если они еще не загружены
            if self.events_data is None:
                success = self.load_events()
                if not success:
                    return None
            
            # Создаем базовую карту
            self.create_base_map()
            
            # Добавляем события на карту
            self.add_events_to_map()
            
            # Сохраняем карту
            return self.save_map(output_filename)
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации карты: {e}")
            return None
    
    def generate_filtered_map(self, category=None, start_year=None, end_year=None, output_filename="filtered_map.html"):
        """
        Создает и сохраняет карту с отфильтрованными историческими событиями
        
        Args:
            category (str, optional): Категория событий для фильтрации
            start_year (int, optional): Начальный год для фильтрации
            end_year (int, optional): Конечный год для фильтрации
            output_filename (str): Имя файла для сохранения
            
        Returns:
            str: Путь к сохраненному файлу или None в случае ошибки
        """
        try:
            # Загружаем данные, если они еще не загружены
            if self.events_data is None:
                success = self.load_events()
                if not success:
                    return None
            
            # Получаем все события
            all_events = self.events_data.get('events', [])
            
            # Фильтруем события
            filtered_events = []
            for event in all_events:
                # Фильтрация по категории
                if category and event.get('category') != category:
                    continue
                
                # Фильтрация по году (если указан)
                if start_year or end_year:
                    event_year = self._extract_year_from_date(event.get('date', ''))
                    if not event_year:
                        continue
                    
                    if start_year and event_year < start_year:
                        continue
                    
                    if end_year and event_year > end_year:
                        continue
                
                filtered_events.append(event)
            
            # Создаем базовую карту
            self.create_base_map()
            
            # Добавляем отфильтрованные события на карту
            self.add_events_to_map(filtered_events)
            
            # Сохраняем карту
            return self.save_map(output_filename)
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации отфильтрованной карты: {e}")
            return None
    
    def _extract_year_from_date(self, date_str):
        """
        Извлекает год из строки с датой
        
        Args:
            date_str (str): Строка с датой
            
        Returns:
            int: Год или None, если год не удалось извлечь
        """
        if not date_str:
            return None
            
        # Пытаемся извлечь 3-4-значный год из строки
        import re
        year_match = re.search(r'\b(\d{3,4})\b', date_str)
        if year_match:
            return int(year_match.group(1))
            
        return None
