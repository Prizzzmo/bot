"""Веб-сервер для мониторинга и администрирования"""

import json
import os
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io

from src.interfaces import ILogger
from src.base_service import BaseService

class WebServer(BaseService):
    """
    Веб-сервер для мониторинга и администрирования бота.
    Предоставляет веб-интерфейс для просмотра логов, статистики и управления ботом.
    """

    def __init__(self, logger: ILogger, analytics_service=None, admin_panel=None, history_map_service=None):
        """
        Инициализация веб-сервера.

        Args:
            logger (ILogger): Логгер для записи информации
            analytics_service: Сервис аналитики
            admin_panel: Административная панель
            history_map_service: Сервис исторических карт
        """
        super().__init__(logger)
        self.analytics_service = analytics_service
        self.admin_panel = admin_panel
        self.history_map_service = history_map_service
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
                        static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))
        self.server_thread = None
        self._setup_routes()

        self.logger.info("Веб-сервер инициализирован")

    def _do_initialize(self) -> bool:
        """
        Инициализирует веб-сервер

        Returns:
            bool: True если инициализация успешна
        """
        try:
            # Здесь можно добавить код инициализации, если необходимо
            return True
        except Exception as e:
            self._logger.log_error(e, "Ошибка при инициализации WebServer")
            return False

    def _setup_routes(self):
        """Настраивает маршруты для веб-сервера"""

        @self.app.route('/')
        def index():
            """Главная страница мониторинга"""
            return render_template('index.html', title="Мониторинг бота")

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

        @self.app.route('/map')
        def map_page():
            """Страница с исторической картой"""
            return render_template('map.html', title="Историческая карта")

        @self.app.route('/api/map/generate', methods=['POST'])
        def api_generate_map():
            """API для генерации исторической карты"""
            if self.history_map_service:
                data = request.json
                category = data.get('category')
                events = data.get('events')
                timeframe = data.get('timeframe')

                map_path = self.history_map_service.generate_map(category, events, timeframe)

                if map_path:
                    return jsonify({"status": "success", "map_url": f"/api/map/view?path={map_path}"})
                return jsonify({"status": "error", "message": "Не удалось сгенерировать карту"})
            return jsonify({"error": "Сервис исторических карт недоступен"})

        @self.app.route('/api/map/view')
        def api_view_map():
            """API для просмотра исторической карты"""
            map_path = request.args.get('path')

            if not map_path or not os.path.exists(map_path):
                return jsonify({"error": "Карта не найдена"}), 404

            return send_file(map_path, mimetype='image/png')

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
            self.logger.warning("Веб-сервер уже запущен")
            return

        def run_server():
            self.logger.info(f"Запуск веб-сервера на {host}:{port}")
            self.app.run(host=host, port=port, debug=False, use_reloader=False)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.logger.info("Веб-сервер запущен в фоновом режиме")

    def stop(self):
        """Останавливает веб-сервер"""
        if self.server_thread and self.server_thread.is_alive():
            # К сожалению, Flask не предоставляет простого метода для остановки сервера из другого потока
            # В реальности здесь нужно использовать более сложную логику остановки
            self.logger.info("Попытка остановки веб-сервера")

            # В простом случае мы просто ждем завершения потока, 
            # но для реального приложения нужен механизм сигналов
            # self.server_thread.join(timeout=5)

            self.logger.info("Веб-сервер остановлен")
        else:
            self.logger.warning("Веб-сервер не запущен")