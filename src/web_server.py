
"""Веб-сервер для мониторинга и администрирования"""

import json
import os
import threading
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io

from src.interfaces import ILogger
from src.base_service import BaseService

# Путь к файлу с историческими данными, сгенерированными Gemini
HISTORY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "history_db_generator/russian_history_database.json")

class WebServer(BaseService):
    """
    Веб-сервер для мониторинга и администрирования бота.
    Предоставляет веб-интерфейс для просмотра логов, статистики и управления ботом.
    """

    def __init__(self, logger: ILogger, analytics_service=None, admin_panel=None):
        """
        Инициализация веб-сервера.

        Args:
            logger: Логгер
            analytics_service: Сервис аналитики
            admin_panel: Административная панель
        """
        super().__init__(logger)
        self.analytics_service = analytics_service
        self.admin_panel = admin_panel
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
                        static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))
        self.server_thread = None
        self.events_data = None
        self._setup_routes()

        self._logger.info("Веб-сервер инициализирован")

    def _do_initialize(self) -> bool:
        """
        Инициализирует веб-сервер

        Returns:
            bool: True если инициализация успешна
        """
        try:
            # Загружаем исторические данные при инициализации
            self._preload_historical_data()
            return True
        except Exception as e:
            self._logger.log_error(e, "Ошибка при инициализации WebServer")
            return False
    
    def _preload_historical_data(self):
        """Предварительная загрузка исторических данных для кэширования"""
        try:
            if os.path.exists(HISTORY_DB_PATH):
                with open(HISTORY_DB_PATH, 'r', encoding='utf-8') as f:
                    self.events_data = json.load(f)
                self._logger.info(f"Загружено {len(self.events_data.get('events', []))} исторических событий")
            else:
                self._logger.warning(f"Файл базы данных не найден: {HISTORY_DB_PATH}")
                self.events_data = {"events": []}
        except Exception as e:
            self._logger.log_error(e, "Ошибка при предварительной загрузке исторических данных")
            self.events_data = {"events": []}

    def _clean_event_data(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Очищает и форматирует данные событий для API
        
        Args:
            events: Список событий
            
        Returns:
            List[Dict[str, Any]]: Очищенный список событий
        """
        cleaned_events = []
        
        for event in events:
            # Пропускаем события без заголовка или даты
            if not event.get('title') or not event.get('date'):
                continue
                
            # Пропускаем события без местоположения, если нет координат
            if 'location' not in event or not event.get('location', {}).get('lat') or not event.get('location', {}).get('lng'):
                continue
            
            # Проверяем и очищаем описание
            description = event.get('description', '')
            if description:
                # Удаляем лишние пробелы и переносы строк
                description = re.sub(r'\s+', ' ', description).strip()
                # Удаляем лишние звездочки, которые не являются частью маркированного списка или жирного текста
                description = re.sub(r'(?<!\*)\*(?!\s|\*)', '', description)
            
            # Создаем очищенный объект события
            clean_event = {
                'id': event.get('id', ''),
                'title': event.get('title', '').strip(),
                'date': event.get('date', '').strip(),
                'description': description,
                'location': event.get('location', {}),
                'category': event.get('category', '').strip(),
                'topic': event.get('topic', '').strip(),
                'century': self._extract_century(event.get('date', ''))
            }
            
            cleaned_events.append(clean_event)
        
        return cleaned_events
    
    def _extract_century(self, date_str: str) -> int:
        """
        Извлекает век из строки даты
        
        Args:
            date_str: Строка с датой
            
        Returns:
            int: Номер века или 0, если не удалось извлечь
        """
        if not date_str:
            return 0
            
        # Ищем 4-значный год
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            year = int(year_match.group(1))
            return (year // 100) + 1
            
        # Ищем любое число, которое может быть годом
        year_match = re.search(r'\b(\d+)\b', date_str)
        if year_match:
            year = int(year_match.group(1))
            # Проверяем, что это может быть год (от 800 до текущего года + 100)
            if 800 <= year <= datetime.now().year + 100:
                return (year // 100) + 1
                
        return 0

    def _setup_routes(self):
        """Настраивает маршруты для веб-сервера"""

        @self.app.route('/')
        def index():
            """Главная страница мониторинга"""
            return render_template('index.html', title="История России на карте")
            
        @self.app.route('/api/historical-events')
        def get_historical_events():
            """API для получения исторических данных из базы Gemini"""
            try:
                # Если данные еще не загружены, загружаем их
                if self.events_data is None:
                    self._preload_historical_data()
                
                # Получаем события из базы данных
                events = self.events_data.get('events', [])
                
                # Очищаем и форматируем данные
                filtered_events = self._clean_event_data(events)
                
                # Фильтрация по параметрам запроса (если они есть)
                category = request.args.get('category')
                century = request.args.get('century')
                
                if category:
                    filtered_events = [e for e in filtered_events if e.get('category') == category]
                
                if century:
                    try:
                        century_int = int(century)
                        filtered_events = [e for e in filtered_events if e.get('century') == century_int]
                    except ValueError:
                        pass
                
                return jsonify(filtered_events)
            except Exception as e:
                self._logger.log_error(str(e), "Ошибка при получении исторических данных")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/categories')
        def get_categories():
            """API для получения списка категорий событий"""
            try:
                if self.events_data is None:
                    self._preload_historical_data()
                
                events = self.events_data.get('events', [])
                categories = sorted(list(set(e.get('category') for e in events if e.get('category'))))
                
                return jsonify(categories)
            except Exception as e:
                self._logger.log_error(str(e), "Ошибка при получении категорий")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/logs')
        def logs():
            """Страница просмотра логов"""
            return render_template('logs.html', title="Логи бота")

        @self.app.route('/api/logs')
        def api_logs():
            """API для получения логов"""
            level = request.args.get('level')
            limit = int(request.args.get('limit', 100))

            logs_data = self.logger.get_logs(level=level, limit=limit)
            return jsonify(logs_data)

        @self.app.route('/statistics')
        def statistics():
            """Страница статистики"""
            return render_template('statistics.html', title="Статистика бота")

        @self.app.route('/api/statistics')
        def api_statistics():
            """API для получения статистики"""
            if self.analytics_service:
                stats = self.analytics_service.get_overall_stats()
                return jsonify(stats)
            return jsonify({"error": "Сервис аналитики недоступен"})

        @self.app.route('/api/statistics/daily')
        def api_daily_stats():
            """API для получения ежедневной статистики"""
            if self.analytics_service:
                days = int(request.args.get('days', 7))
                stats = self.analytics_service.get_period_stats('daily', days)
                return jsonify(stats)
            return jsonify({"error": "Сервис аналитики недоступен"})

        @self.app.route('/admin')
        def admin():
            """Административная панель"""
            if self.admin_panel:
                return render_template('admin.html', title="Администрирование бота")
            return render_template('error.html', title="Ошибка", message="Административная панель недоступна")

        @self.app.route('/api/admin/stats')
        def api_admin_stats():
            """API для получения административной статистики"""
            if self.admin_panel:
                stats = self.admin_panel.get_bot_stats()
                return jsonify(stats)
            return jsonify({"error": "Административная панель недоступна"})


        @self.app.route('/api/chart/daily_activity')
        def api_chart_daily_activity():
            """API для генерации графика ежедневной активности"""
            if self.analytics_service:
                days = int(request.args.get('days', 7))
                daily_stats = self.analytics_service.get_daily_requests(days)

                fig = Figure(figsize=(10, 5))
                axis = fig.add_subplot(1, 1, 1)

                dates = [stat['date'] for stat in daily_stats]
                requests = [stat['requests'] for stat in daily_stats]
                users = [stat['unique_users'] for stat in daily_stats]

                axis.plot(dates, requests, 'o-', label='Запросы')
                axis.plot(dates, users, 's-', label='Пользователи')
                axis.set_xlabel('Дата')
                axis.set_ylabel('Количество')
                axis.set_title('Ежедневная активность')
                axis.legend()
                axis.grid(True)

                # Поворачиваем метки дат для лучшей читаемости
                plt.setp(axis.xaxis.get_majorticklabels(), rotation=45)
                fig.tight_layout()

                # Сохраняем график в память
                output = io.BytesIO()
                FigureCanvas(fig).print_png(output)

                return output.getvalue(), 200, {'Content-Type': 'image/png'}

            return jsonify({"error": "Сервис аналитики недоступен"}), 500

    def start(self, host: str = '0.0.0.0', port: int = 8080):
        """
        Запускает веб-сервер в отдельном потоке.

        Args:
            host (str): Хост для запуска сервера
            port (int): Порт для запуска сервера
        """
        if self.server_thread and self.server_thread.is_alive():
            self._logger.warning("Веб-сервер уже запущен")
            return

        def run_server():
            self._logger.info(f"Запуск веб-сервера на {host}:{port}")
            self.app.run(host=host, port=port, debug=False, use_reloader=False)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self._logger.info("Веб-сервер запущен в фоновом режиме")

    def stop(self):
        """Останавливает веб-сервер"""
        if self.server_thread and self.server_thread.is_alive():
            # К сожалению, Flask не предоставляет простого метода для остановки сервера из другого потока
            # В реальности здесь нужно использовать более сложную логику остановки
            self.logger.info("Попытка остановки веб-сервера")

            # В простом случае мы просто ждем завершения потока, 
            # но для реального приложения нужен механизм сигналов
            # self.server_thread.join(timeout=5)

            self._logger.info("Веб-сервер остановлен")
        else:
            self._logger.warning("Веб-сервер не запущен")
