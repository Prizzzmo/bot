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
            response = jsonify(categories)
            response.cache_control.max_age = 3600  # кэширование на 1 час
            return response
            
        @self.app.after_request
        def add_header(response):
            """Добавление заголовков кэширования для статических ресурсов"""
            if 'text/html' in response.headers.get('Content-Type', ''):
                response.cache_control.max_age = 600  # HTML-страницы - 10 минут
            elif 'text/css' in response.headers.get('Content-Type', ''):
                response.cache_control.max_age = 86400  # CSS - 1 день
            elif 'application/javascript' in response.headers.get('Content-Type', ''):
                response.cache_control.max_age = 86400  # JS - 1 день
            elif 'image/' in response.headers.get('Content-Type', ''):
                response.cache_control.max_age = 604800  # Изображения - 7 дней
            return response

    def run(self):
        """Запуск веб-сервера в отдельном потоке"""
        threading.Thread(target=self._run_server, daemon=True).start()

    def _run_server(self):
        """Внутренний метод для запуска сервера"""
        try:
            port = 8080  # Используем порт 8080, который по умолчанию открыт в Replit
            self.logger.info(f"Запуск веб-сервера интерактивной карты на порту {port}")
            self.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            self.logger.error(f"Ошибка при запуске веб-сервера карты: {e}")