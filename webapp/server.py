
"""
Сервер веб-приложения для визуализации исторических данных
"""

import os
import json
import logging
from flask import Flask, render_template, jsonify, request, send_file

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
    """API для получения информации о событии через Gemini API"""
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
        is_brief = data.get('isBrief', True)
        
        if is_brief:
            prompt = f"""
            Предоставь краткую историческую информацию о следующем событии из истории России:
            
            Название: {event_title}
            Дата: {event_date}
            Категория: {event_category}
            Место: {event_location}
            
            Ответ должен быть кратким (не более 200 слов), но содержательным. 
            Выдели 3-4 ключевых факта о событии и его значении. 
            Используй маркированный список для лучшей читаемости.
            """
        else:
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
            
            Используй только проверенные исторические факты. Ответ должен быть информативным и подробным.
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

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """API для генерации подробного реферата в формате Word"""
    try:
        # Получаем данные из запроса
        data = request.json
        
        if not data or not data.get('title'):
            return jsonify({'error': 'Недостаточно данных о событии'}), 400
        
        # Импортируем необходимые библиотеки
        import sys
        import os
        from io import BytesIO
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
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
            return jsonify({'error': 'API ключ не найден'}), 500
        
        # Создаем объекты для работы с API
        api_cache = APICache(logger)
        api_client = APIClient(api_key, api_cache, logger)
        
        # Формируем промпт для Gemini для получения подробной информации
        event_title = data.get('title', '')
        event_date = data.get('date', '')
        event_category = data.get('category', '')
        event_location = data.get('location', '')
        
        prompt = f"""
        Напиши подробный исторический реферат о следующем событии из истории России:
        
        Название: {event_title}
        Дата: {event_date}
        Категория: {event_category}
        Место: {event_location}
        
        Реферат должен содержать следующие разделы:
        1. Введение и исторический контекст (что происходило в России в это время)
        2. Хронология и детальное описание события
        3. Ключевые исторические личности, их роли и биографические данные
        4. Причины и предпосылки события
        5. Непосредственные последствия
        6. Историческое значение и влияние на дальнейший ход истории России
        7. Историографический анализ и различные точки зрения историков
        8. Заключение
        
        Реферат должен быть максимально подробным, академическим и опираться на исторические источники.
        """
        
        try:
            # Инициализация API клиента если нужно
            if not api_client.is_initialized():
                api_client.initialize()
                
            # Запрос к Gemini API
            detailed_content = api_client.ask_grok(prompt, use_cache=True)
            
            # Создаем документ Word
            doc = Document()
            
            # Устанавливаем стили
            title_style = doc.styles['Title']
            title_style.font.size = Pt(16)
            title_style.font.bold = True
            
            heading_style = doc.styles['Heading 1']
            heading_style.font.size = Pt(14)
            heading_style.font.bold = True
            
            # Заголовок документа
            doc.add_heading(event_title, 0)
            
            # Информация о событии
            info_paragraph = doc.add_paragraph()
            info_paragraph.add_run(f"Дата: {event_date}\n").bold = True
            info_paragraph.add_run(f"Категория: {event_category}\n").bold = True
            info_paragraph.add_run(f"Место: {event_location}").bold = True
            
            # Добавляем разделительную линию
            doc.add_paragraph("_" * 50)
            
            # Парсим и добавляем содержимое
            content_lines = detailed_content.split('\n')
            current_heading_level = 0
            
            for i, line in enumerate(content_lines):
                line = line.strip()
                
                if not line:
                    doc.add_paragraph()
                    continue
                
                # Определяем, является ли строка заголовком
                heading_level = 0
                if line.startswith('# '):
                    heading_level = 1
                    heading_text = line[2:].strip()
                elif line.startswith('## '):
                    heading_level = 2
                    heading_text = line[3:].strip()
                elif line.startswith('### '):
                    heading_level = 3
                    heading_text = line[4:].strip()
                elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
                    heading_level = 2
                    heading_text = line[3:].strip()
                
                # Обрабатываем заголовки
                if heading_level > 0:
                    if heading_level == 1:
                        doc.add_heading(heading_text, level=1)
                    elif heading_level == 2:
                        doc.add_heading(heading_text, level=2)
                    elif heading_level == 3:
                        doc.add_heading(heading_text, level=3)
                    
                    current_heading_level = heading_level
                    continue
                
                # Обрабатываем обычный текст
                if line.startswith('- ') or line.startswith('* '):
                    # Маркированный список
                    p = doc.add_paragraph(line[2:], style='List Bullet')
                else:
                    # Обычный текст
                    p = doc.add_paragraph(line)
            
            # Сохраняем документ в память
            file_buffer = BytesIO()
            doc.save(file_buffer)
            file_buffer.seek(0)
            
            # Возвращаем файл
            return send_file(
                file_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                as_attachment=True,
                download_name=f"{event_title.replace('/', '_')}_реферат.docx"
            )
            
        except Exception as api_error:
            logger.error(f"Ошибка при генерации реферата: {api_error}")
            return jsonify({'error': str(api_error)}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на генерацию реферата: {e}")
        return jsonify({'error': str(e)}), 500

def run_server(host='0.0.0.0', port=8080):
    """Запуск веб-сервера"""
    logger.info(f"Запуск веб-сервера на {host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    run_server()
