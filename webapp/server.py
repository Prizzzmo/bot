
"""
Сервер веб-приложения для визуализации исторических данных
"""

import os
import json
import logging
from flask import Flask, render_template, jsonify, request

# Путь к файлу с историческими данными
HISTORY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "history_db_generator/russian_history_database.json")

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_historical_data():
    """Загрузка исторических данных из файла"""
    try:
        if os.path.exists(HISTORY_DB_PATH):
            with open(HISTORY_DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Загружено {len(data.get('events', []))} исторических событий")
            return data
        else:
            logger.warning(f"Файл базы данных не найден: {HISTORY_DB_PATH}")
            return {"events": []}
    except Exception as e:
        logger.error(f"Ошибка при загрузке исторических данных: {e}")
        return {"events": []}

# Загрузка данных при старте сервера
historical_data = load_historical_data()

@app.route('/')
def index():
    """Главная страница"""
    # Получаем статистику для приветственного баннера
    events_count = len(historical_data.get('events', [])) if historical_data else 0
    
    # Получаем уникальные категории
    categories = set()
    if historical_data and 'events' in historical_data:
        for event in historical_data['events']:
            if event.get('category'):
                categories.add(event.get('category'))
    
    categories_count = len(categories)
    
    return render_template('index.html', 
                          events_count=events_count,
                          categories_count=categories_count)

@app.route('/api/historical-events')
def get_historical_events():
    """API для получения исторических данных"""
    try:
        # Проверяем, загружены ли данные
        global historical_data
        if not historical_data:
            historical_data = load_historical_data()
        
        # Получаем события из базы данных
        events = historical_data.get('events', [])
        logger.info(f"Всего событий в базе: {len(events)}")
        
        # Фильтруем события, у которых есть координаты местоположения
        filtered_events = []
        for event in events:
            # Проверка на наличие координат
            has_coords = False
            if isinstance(event.get('location'), dict):
                has_coords = event.get('location', {}).get('lat') and event.get('location', {}).get('lng')
            
            if not has_coords:
                continue
                
            filtered_event = {
                'id': event.get('id', ''),
                'title': event.get('title', ''),
                'date': event.get('date', ''),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'category': event.get('category', ''),
                'topic': event.get('topic', '')
            }
            filtered_events.append(filtered_event)
        
        logger.info(f"Отправляется {len(filtered_events)} событий с координатами")
        return jsonify(filtered_events)
    except Exception as e:
        logger.error(f"Ошибка при получении исторических данных: {e}")
        return jsonify([]), 200  # Возвращаем пустой массив вместо ошибки

@app.route('/api/categories')
def get_categories():
    """API для получения списка категорий событий"""
    try:
        events = historical_data.get('events', [])
        categories = sorted(list(set(e.get('category') for e in events if e.get('category'))))
        
        return jsonify(categories)
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/event-details', methods=['POST'])
def get_event_details():
    """API для получения подробной информации о событии через Gemini API"""
    try:
        # Получаем данные из запроса
        data = request.json
        
        if not data or not data.get('title'):
            return jsonify({'error': 'Недостаточно данных о событии'}), 400
        
        # Формируем запрос к Gemini API
        # Импортируем здесь для избежания циклических импортов
        import sys
        import os
        # Добавляем корневую директорию проекта в путь для импорта
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root_dir not in sys.path:
            sys.path.append(root_dir)
            
        from src.api_client import APIClient
        from src.api_cache import APICache
        from src.logger import Logger
        
        # Получаем API ключ
        api_key = None
        try:
            from gemini_api_keys import GEMINI_API_KEYS
            if GEMINI_API_KEYS:
                api_key = GEMINI_API_KEYS[0]
        except ImportError:
            logger.error("Не удалось импортировать GEMINI_API_KEYS")
        
        if not api_key:
            try:
                import os
                api_key = os.environ.get('GEMINI_API_KEY')
            except:
                pass
        
        if not api_key:
            return jsonify({
                'content': 'Не удалось получить доступ к API Gemini. Пожалуйста, проверьте настройки API ключей.'
            }), 200
        
        # Создаем объекты для работы с API
        api_cache = APICache(logger)
        api_client = APIClient(api_key, api_cache, logger)
        
        # Формируем промпт для Gemini
        event_title = data.get('title', '')
        event_date = data.get('date', '')
        event_category = data.get('category', '')
        event_location = data.get('location', '')
        
        prompt = f"""
        Предоставь подробную историческую информацию о следующем событии из истории России:
        
        Название: {event_title}
        Дата: {event_date}
        Категория: {event_category}
        Место: {event_location}
        
        Пожалуйста, структурируй ответ следующим образом:
        1. Исторический контекст (что происходило в России в это время)
        2. Подробное описание события
        3. Ключевые участники
        4. Причины и предпосылки
        5. Последствия и историческое значение
        
        Используй только проверенные исторические факты. Ответ должен быть информативным, подробным, но лаконичным.
        """
        
        try:
            # Инициализация API клиента если нужно
            if not api_client.is_initialized():
                api_client.initialize()
                
            # Запрос к Gemini API
            response = api_client.ask_grok(prompt, use_cache=True)
            
            return jsonify({
                'content': response
            })
        except Exception as api_error:
            logger.error(f"Ошибка при запросе к Gemini API: {api_error}")
            return jsonify({
                'content': f"Произошла ошибка при получении информации: {str(api_error)}"
            }), 200
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса о деталях события: {e}")
        return jsonify({
            'content': 'Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.'
        }), 200

def run_server(host='0.0.0.0', port=5000):
    """Запуск веб-сервера"""
    logger.info(f"Запуск веб-сервера на {host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    run_server()
