
from flask import Flask, render_template, request, jsonify
import threading
import os

class MapServer:
    """Класс для обслуживания веб-сервера с интерактивной картой"""
    
    def __init__(self, history_map, logger):
        self.app = Flask(__name__, 
                         template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                         static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
        self.history_map = history_map
        self.logger = logger
        self.setup_routes()
        
    def setup_routes(self):
        """Настройка маршрутов веб-сервера"""
        
        @self.app.route('/map')
        def map_page():
            """Отображение страницы с интерактивной картой"""
            category = request.args.get('category')
            event_ids = request.args.get('events')
            
            # Получаем все категории для фильтра
            categories = self.history_map.get_categories()
            
            # Получаем события в зависимости от параметров запроса
            if category:
                events = self.history_map.get_events_by_category(category)
            elif event_ids:
                try:
                    ids = [int(id_) for id_ in event_ids.split(',')]
                    events = [self.history_map.get_event_by_id(id_) for id_ in ids]
                    events = [event for event in events if event]  # Фильтруем None значения
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке параметра events: {e}")
                    events = self.history_map.get_all_events()
            else:
                events = self.history_map.get_all_events()
            
            return render_template('map.html', events=events, categories=categories)
        
        @self.app.route('/api/events')
        def get_events():
            """API для получения событий"""
            category = request.args.get('category')
            
            if category:
                events = self.history_map.get_events_by_category(category)
            else:
                events = self.history_map.get_all_events()
                
            return jsonify(events)
        
        @self.app.route('/api/categories')
        def get_categories():
            """API для получения категорий"""
            categories = self.history_map.get_categories()
            return jsonify(categories)
    
    def run(self):
        """Запуск веб-сервера в отдельном потоке"""
        threading.Thread(target=self._run_server, daemon=True).start()
        self.logger.info("Веб-сервер с интерактивной картой запущен на порту 8081")
    
    def _run_server(self):
        """Внутренний метод для запуска сервера"""
        try:
            port = 8080  # Используем порт 8080, который по умолчанию открыт в Replit
            self.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
            self.logger.info(f"Веб-сервер запущен на порту {port}")
        except Exception as e:
            self.logger.error(f"Ошибка при запуске веб-сервера: {e}")
