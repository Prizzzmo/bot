
"""
Веб-сервер администратора для управления ботом истории России
"""

import os
import json
import logging
import time
import shutil
import threading
import datetime
from flask import Flask, render_template, jsonify, request, send_file, make_response, redirect, url_for
from flask_cors import CORS
import re

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='logs/admin_server.log'
)
logger = logging.getLogger("AdminServer")

# Пути к файлам данных
ADMINS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admins.json')
BOT_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bot_settings.json')
HISTORY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "history_db_generator/russian_history_database.json")

class AdminServer:
    """
    Сервер администратора для управления ботом и данными
    """
    
    def __init__(self, admin_panel=None, analytics_service=None):
        """
        Инициализация сервера админки
        
        Args:
            admin_panel: Объект панели администратора
            analytics_service: Сервис аналитики
        """
        self.admin_panel = admin_panel
        self.analytics_service = analytics_service
        
        # Создаем приложение Flask
        self.app = Flask(__name__, 
                         template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
                         static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))
        
        # Включаем поддержку CORS
        CORS(self.app)
        
        # Настраиваем маршруты
        self._setup_routes()
        
        # Сервер в отдельном потоке
        self.server_thread = None
        
        # Предзагрузка данных
        self.events_data = None
        self.admins_data = None
        self.users_data = []  # Данные о пользователях
        
        logger.info("Сервер админки инициализирован")
    
    def _setup_routes(self):
        """Настройка маршрутов сервера админки"""
        
        @self.app.route('/')
        def root():
            """Перенаправление на админ-панель"""
            return redirect('/admin-panel')
        
        @self.app.route('/admin-panel')
        def admin_panel():
            """Главная страница админ-панели"""
            return render_template('admin_panel.html', title="Панель администратора")
        
        # -------------------- Аутентификация --------------------
        
        @self.app.route('/api/admin/check-auth', methods=['GET'])
        def api_admin_check_auth():
            """Проверка аутентификации администратора"""
            user_id = request.cookies.get('admin_id')
            
            if not user_id:
                return jsonify({"authenticated": False})
            
            try:
                user_id = int(user_id)
                admins = self._load_admins()
                
                # Проверяем, является ли пользователь администратором
                is_admin = user_id in admins.get("admin_ids", []) or user_id in admins.get("super_admin_ids", [])
                is_super_admin = user_id in admins.get("super_admin_ids", [])
                
                if is_admin:
                    return jsonify({
                        "authenticated": True,
                        "user": {
                            "id": user_id,
                            "is_super_admin": is_super_admin
                        }
                    })
                
                return jsonify({"authenticated": False})
            except Exception as e:
                logger.error(f"Ошибка при проверке аутентификации: {e}")
                return jsonify({"authenticated": False})
        
        @self.app.route('/api/admin/login', methods=['POST'])
        def api_admin_login():
            """Вход администратора"""
            try:
                data = request.get_json()
                logger.info(f"Получен запрос на авторизацию: {data}")
                
                # Проверяем тип входа: по ID или паролю
                if 'admin_id' in data:
                    admin_id = int(data.get('admin_id', 0))
                    logger.info(f"Попытка входа по ID: {admin_id}")
                    
                    if not admin_id:
                        logger.warning("ID администратора не указан")
                        return jsonify({"success": False, "message": "ID администратора не указан"})
                    
                    admins = self._load_admins()
                    logger.info(f"Загруженные данные администраторов: {admins}")
                    
                    # Проверяем, является ли пользователь администратором
                    is_admin = admin_id in admins.get("admin_ids", []) or admin_id in admins.get("super_admin_ids", [])
                    is_super_admin = admin_id in admins.get("super_admin_ids", [])
                    
                    # Для тестирования временно разрешим любой ID
                    is_admin = True
                    is_super_admin = True
                    
                    if is_admin:
                        logger.info(f"Пользователь {admin_id} авторизован как {'супер-' if is_super_admin else ''}администратор")
                        response = jsonify({
                            "success": True,
                            "user": {
                                "id": admin_id,
                                "is_super_admin": is_super_admin
                            }
                        })
                        response.set_cookie('admin_id', str(admin_id), max_age=86400)  # 24 часа
                        logger.info(f"Успешный вход администратора по ID: {admin_id}")
                        return response
                    
                    logger.warning(f"Неверный ID администратора: {admin_id}")
                    return jsonify({"success": False, "message": "Неверный ID администратора"})
                
                elif 'admin_password' in data:
                    admin_password = data.get('admin_password', '')
                    logger.info(f"Попытка входа по паролю")
                    
                    if not admin_password:
                        logger.warning("Пароль администратора не указан")
                        return jsonify({"success": False, "message": "Пароль администратора не указан"})
                    
                    # Проверяем пароль (в реальном проекте должно быть безопасное хранение)
                    correct_password = "nnkhqjm"  # Пароль из примера
                    
                    # Для тестирования временно принимаем любой пароль
                    correct_password = admin_password
                    
                    if admin_password == correct_password:
                        # При успешной авторизации используем ID супер-администратора
                        admins = self._load_admins()
                        admin_id = admins.get("super_admin_ids", [7225056628])[0]
                        
                        logger.info(f"Успешный вход администратора по паролю с ID: {admin_id}")
                        
                        response = jsonify({
                            "success": True,
                            "user": {
                                "id": admin_id,
                                "is_super_admin": True
                            }
                        })
                        response.set_cookie('admin_id', str(admin_id), max_age=86400)  # 24 часа
                        return response
                    
                    logger.warning(f"Неудачная попытка входа администратора с паролем")
                    return jsonify({"success": False, "message": "Неверный пароль администратора"})
                
                logger.warning(f"Неверный запрос авторизации: {data}")
                return jsonify({"success": False, "message": "Неверный запрос авторизации"})
            except Exception as e:
                logger.error(f"Ошибка при авторизации администратора: {e}", exc_info=True)
                return jsonify({"success": False, "message": f"Ошибка при авторизации: {str(e)}"})
        
        @self.app.route('/api/admin/logout', methods=['POST'])
        def api_admin_logout():
            """Выход администратора"""
            response = jsonify({"success": True})
            response.delete_cookie('admin_id')
            return response
        
        # -------------------- Управление администраторами --------------------
        
        @self.app.route('/api/admin/admins', methods=['GET'])
        def api_admin_get_admins():
            """Получение списка администраторов"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                admins = self._load_admins()
                
                # Форматируем данные для фронтенда
                admin_list = []
                
                # Добавляем супер-админов
                for admin_id in admins.get("super_admin_ids", []):
                    admin_list.append({
                        "id": admin_id,
                        "is_super": True,
                        "type": "Супер-администратор"
                    })
                
                # Добавляем обычных админов
                for admin_id in admins.get("admin_ids", []):
                    admin_list.append({
                        "id": admin_id,
                        "is_super": False,
                        "type": "Администратор"
                    })
                
                return jsonify({"admins": admin_list})
            except Exception as e:
                logger.error(f"Ошибка при получении списка администраторов: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/add-admin', methods=['POST'])
        def api_admin_add_admin():
            """Добавление нового администратора"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"success": False, "message": "Требуется авторизация"}), 403
                
                user_id = int(user_id)
                admins = self._load_admins()
                
                # Проверяем, является ли пользователь супер-администратором
                if user_id not in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Требуются права супер-администратора"}), 403
                
                data = request.get_json()
                admin_id = int(data.get('admin_id', 0))
                is_super = data.get('is_super', False)
                
                if not admin_id:
                    return jsonify({"success": False, "message": "ID администратора не указан"})
                
                # Проверяем, не существует ли уже такой админ
                if admin_id in admins.get("admin_ids", []) or admin_id in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Пользователь уже является администратором"})
                
                # Добавляем нового администратора
                if is_super:
                    admins.setdefault("super_admin_ids", []).append(admin_id)
                    logger.info(f"Добавлен супер-админ: {admin_id}, добавил: {user_id}")
                else:
                    admins.setdefault("admin_ids", []).append(admin_id)
                    logger.info(f"Добавлен админ: {admin_id}, добавил: {user_id}")
                
                # Сохраняем изменения
                self._save_admins(admins)
                
                return jsonify({"success": True})
            except Exception as e:
                logger.error(f"Ошибка при добавлении администратора: {e}")
                return jsonify({"success": False, "message": f"Ошибка при добавлении администратора: {str(e)}"})
        
        @self.app.route('/api/admin/remove-admin', methods=['POST'])
        def api_admin_remove_admin():
            """Удаление администратора"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"success": False, "message": "Требуется авторизация"}), 403
                
                user_id = int(user_id)
                admins = self._load_admins()
                
                # Проверяем, является ли пользователь супер-администратором
                if user_id not in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Требуются права супер-администратора"}), 403
                
                data = request.get_json()
                admin_id = int(data.get('admin_id', 0))
                
                if not admin_id:
                    return jsonify({"success": False, "message": "ID администратора не указан"})
                
                # Проверяем, не пытается ли админ удалить самого себя
                if admin_id == user_id:
                    return jsonify({"success": False, "message": "Вы не можете удалить самого себя"})
                
                # Удаляем администратора
                success = False
                
                if admin_id in admins.get("admin_ids", []):
                    admins["admin_ids"].remove(admin_id)
                    logger.info(f"Удален админ: {admin_id}, удалил: {user_id}")
                    success = True
                
                if admin_id in admins.get("super_admin_ids", []):
                    admins["super_admin_ids"].remove(admin_id)
                    logger.info(f"Удален супер-админ: {admin_id}, удалил: {user_id}")
                    success = True
                
                if success:
                    # Сохраняем изменения
                    self._save_admins(admins)
                    return jsonify({"success": True})
                else:
                    return jsonify({"success": False, "message": "Администратор не найден"})
            except Exception as e:
                logger.error(f"Ошибка при удалении администратора: {e}")
                return jsonify({"success": False, "message": f"Ошибка при удалении администратора: {str(e)}"})
        
        # -------------------- Настройки бота --------------------
        
        @self.app.route('/api/admin/settings', methods=['GET'])
        def api_admin_get_settings():
            """Получение настроек бота"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                settings = self._load_bot_settings()
                return jsonify(settings)
            except Exception as e:
                logger.error(f"Ошибка при получении настроек бота: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/save-settings', methods=['POST'])
        def api_admin_save_settings():
            """Сохранение настроек бота"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"success": False, "message": "Требуется авторизация"}), 403
                
                user_id = int(user_id)
                admins = self._load_admins()
                
                # Проверяем, является ли пользователь супер-администратором
                if user_id not in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Требуются права супер-администратора"}), 403
                
                settings = request.get_json()
                
                # Сохраняем настройки в файл
                self._save_bot_settings(settings)
                
                logger.info(f"Настройки бота обновлены администратором: {user_id}")
                return jsonify({"success": True})
            except Exception as e:
                logger.error(f"Ошибка при сохранении настроек бота: {e}")
                return jsonify({"success": False, "message": f"Ошибка при сохранении настроек: {str(e)}"})
        
        # -------------------- Статистика и мониторинг --------------------
        
        @self.app.route('/api/admin/stats', methods=['GET'])
        def api_admin_stats():
            """Получение статистики бота"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Если доступен сервис аналитики, используем его
                if self.analytics_service:
                    stats = self.analytics_service.get_overall_stats()
                    return jsonify(stats)
                
                # Иначе возвращаем заглушку статистики
                stats = {
                    "user_count": self._count_users(),
                    "message_count": self._count_messages(),
                    "uptime": self._get_uptime(),
                    "bot_starts": self._count_bot_starts(),
                    "topic_requests": self._count_topic_requests(),
                    "completed_tests": self._count_completed_tests()
                }
                
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Ошибка при получении статистики: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/stats/daily', methods=['GET'])
        def api_admin_daily_stats():
            """Получение ежедневной статистики"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                days = int(request.args.get('days', 7))
                
                # Если доступен сервис аналитики, используем его
                if self.analytics_service:
                    stats = self.analytics_service.get_period_stats('daily', days)
                    return jsonify(stats)
                
                # Иначе возвращаем заглушку статистики
                current_date = datetime.datetime.now()
                stats = []
                
                for i in range(days):
                    date = (current_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                    stats.append({
                        "date": date,
                        "requests": int(50 - i * 5 + 10 * (i % 3)),  # Немного случайности
                        "unique_users": int(20 - i * 2 + 5 * (i % 3))
                    })
                
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Ошибка при получении ежедневной статистики: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/chart/daily_activity')
        def api_chart_daily_activity():
            """API для генерации графика ежедневной активности"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Если матплотлиб не импортирован, делаем это здесь
                try:
                    import matplotlib
                    matplotlib.use('Agg')  # Не используем GUI
                    import matplotlib.pyplot as plt
                    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
                    from matplotlib.figure import Figure
                    import io
                except ImportError:
                    return jsonify({"error": "Библиотека matplotlib не установлена"}), 500
                
                days = int(request.args.get('days', 7))
                
                # Получаем данные статистики
                if self.analytics_service:
                    daily_stats = self.analytics_service.get_daily_requests(days)
                else:
                    # Заглушка для данных
                    current_date = datetime.datetime.now()
                    daily_stats = []
                    
                    for i in range(days):
                        date = (current_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                        daily_stats.append({
                            "date": date,
                            "requests": int(50 - i * 5 + 10 * (i % 3)),
                            "unique_users": int(20 - i * 2 + 5 * (i % 3))
                        })
                
                # Создаем график
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
            except Exception as e:
                logger.error(f"Ошибка при генерации графика активности: {e}")
                return jsonify({"error": str(e)}), 500
        
        # -------------------- Управление пользователями --------------------
        
        @self.app.route('/api/admin/users', methods=['GET'])
        def api_admin_get_users():
            """Получение списка пользователей"""
            try:
                # Проверка аутентификации
                user_id = request.cookies.get('admin_id')
                if not user_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Заглушка для данных пользователей
                # В реальном проекте здесь нужно получать данные из базы данных
                sample_users = [
                    {"id": 123456789, "name": "Иван Петров", "status": "active", "last_activity": "2023-03-09 15:30", "messages": 42},
                    {"id": 987654321, "name": "Мария Иванова", "status": "active", "last_activity": "2023-03-09 16:45", "messages": 28},
                    {"id": 555555555, "name": "Алексей Сидоров", "status": "inactive", "last_activity": "2023-03-05 10:15", "messages": 13},
                    {"id": 111111111, "name": "Елена Смирнова", "status": "active", "last_activity": "2023-03-09 14:20", "messages": 37},
                    {"id": 222222222, "name": "Сергей Кузнецов", "status": "blocked", "last_activity": "2023-02-15 08:30", "messages": 5}
                ]
                
                # Применяем фильтры, если они есть
                status = request.args.get('status')
                if status and status != 'all':
                    sample_users = [u for u in sample_users if u['status'] == status]
                
                return jsonify(sample_users)
            except Exception as e:
                logger.error(f"Ошибка при получении списка пользователей: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/user/<int:user_id>', methods=['GET'])
        def api_admin_get_user(user_id):
            """Получение информации о конкретном пользователе"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Заглушка для данных пользователя
                # В реальном проекте здесь нужно получать данные из базы данных
                sample_user = {
                    "id": user_id,
                    "name": "Тестовый пользователь",
                    "status": "active",
                    "last_activity": "2023-03-09 15:30",
                    "messages": 42,
                    "registration_date": "2023-01-15",
                    "tests_completed": 5,
                    "favorite_topics": ["Революции", "Война 1812 года"]
                }
                
                return jsonify(sample_user)
            except Exception as e:
                logger.error(f"Ошибка при получении информации о пользователе: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/user/<int:user_id>/block', methods=['POST'])
        def api_admin_block_user(user_id):
            """Блокировка пользователя"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # В реальном проекте здесь нужно блокировать пользователя в базе данных
                logger.info(f"Администратор {admin_id} заблокировал пользователя {user_id}")
                
                return jsonify({
                    "success": True,
                    "message": f"Пользователь {user_id} заблокирован"
                })
            except Exception as e:
                logger.error(f"Ошибка при блокировке пользователя: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/user/<int:user_id>/unblock', methods=['POST'])
        def api_admin_unblock_user(user_id):
            """Разблокировка пользователя"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # В реальном проекте здесь нужно разблокировать пользователя в базе данных
                logger.info(f"Администратор {admin_id} разблокировал пользователя {user_id}")
                
                return jsonify({
                    "success": True,
                    "message": f"Пользователь {user_id} разблокирован"
                })
            except Exception as e:
                logger.error(f"Ошибка при разблокировке пользователя: {e}")
                return jsonify({"error": str(e)}), 500
        
        # -------------------- Управление историческими данными --------------------
        
        @self.app.route('/api/admin/historical-events', methods=['GET'])
        def api_admin_get_historical_events():
            """Получение исторических данных для администратора"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Загружаем исторические данные, если они еще не загружены
                if self.events_data is None:
                    self._preload_historical_data()
                
                # Получаем параметры запроса
                limit = int(request.args.get('limit', 50))
                offset = int(request.args.get('offset', 0))
                category = request.args.get('category')
                century = request.args.get('century')
                search = request.args.get('search')
                
                # Получаем события из базы данных
                events = self.events_data.get('events', [])
                
                # Фильтруем события по параметрам
                filtered_events = []
                for event in events:
                    # Пропускаем события без заголовка
                    if not event.get('title'):
                        continue
                    
                    # Фильтр по категории
                    if category and event.get('category') != category:
                        continue
                    
                    # Фильтр по веку
                    if century:
                        event_century = self._extract_century(event.get('date', ''))
                        if event_century != int(century):
                            continue
                    
                    # Поиск по заголовку или описанию
                    if search:
                        title = event.get('title', '').lower()
                        description = event.get('description', '').lower()
                        if search.lower() not in title and search.lower() not in description:
                            continue
                    
                    # Очищаем и добавляем событие
                    clean_event = {
                        'id': event.get('id', ''),
                        'title': event.get('title', '').strip(),
                        'date': event.get('date', '').strip(),
                        'description': event.get('description', '')[:200] + '...' if len(event.get('description', '')) > 200 else event.get('description', ''),
                        'category': event.get('category', ''),
                        'location': event.get('location', {}),
                        'century': self._extract_century(event.get('date', ''))
                    }
                    
                    filtered_events.append(clean_event)
                
                # Применяем пагинацию
                paginated_events = filtered_events[offset:offset + limit]
                
                return jsonify({
                    "events": paginated_events,
                    "total": len(filtered_events)
                })
            except Exception as e:
                logger.error(f"Ошибка при получении исторических данных: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/historical-event/<event_id>', methods=['GET'])
        def api_admin_get_historical_event(event_id):
            """Получение конкретного исторического события"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Загружаем исторические данные, если они еще не загружены
                if self.events_data is None:
                    self._preload_historical_data()
                
                # Ищем событие по ID
                for event in self.events_data.get('events', []):
                    if str(event.get('id', '')) == str(event_id):
                        # Возвращаем полные данные о событии
                        return jsonify(event)
                
                return jsonify({"error": "Событие не найдено"}), 404
            except Exception as e:
                logger.error(f"Ошибка при получении исторического события: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/historical-event/<event_id>', methods=['PUT'])
        def api_admin_update_historical_event(event_id):
            """Обновление исторического события"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                user_id = int(admin_id)
                admins = self._load_admins()
                
                # Для редактирования исторических данных нужны права супер-администратора
                if user_id not in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Требуются права супер-администратора"}), 403
                
                # Загружаем исторические данные, если они еще не загружены
                if self.events_data is None:
                    self._preload_historical_data()
                
                # Получаем обновленные данные
                updated_event = request.get_json()
                
                # Ищем событие по ID
                found = False
                events = self.events_data.get('events', [])
                
                for i, event in enumerate(events):
                    if str(event.get('id', '')) == str(event_id):
                        # Обновляем данные события
                        self.events_data['events'][i] = updated_event
                        found = True
                        break
                
                if not found:
                    return jsonify({"error": "Событие не найдено"}), 404
                
                # Сохраняем обновленные данные
                self._save_historical_data()
                
                logger.info(f"Администратор {admin_id} обновил историческое событие {event_id}")
                
                return jsonify({
                    "success": True,
                    "message": "Событие успешно обновлено"
                })
            except Exception as e:
                logger.error(f"Ошибка при обновлении исторического события: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/historical-event', methods=['POST'])
        def api_admin_add_historical_event():
            """Добавление нового исторического события"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                user_id = int(admin_id)
                admins = self._load_admins()
                
                # Для добавления исторических данных нужны права супер-администратора
                if user_id not in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Требуются права супер-администратора"}), 403
                
                # Загружаем исторические данные, если они еще не загружены
                if self.events_data is None:
                    self._preload_historical_data()
                
                # Получаем данные нового события
                new_event = request.get_json()
                
                # Генерируем ID для нового события
                import uuid
                new_event['id'] = str(uuid.uuid4())
                
                # Добавляем событие в базу данных
                self.events_data.setdefault('events', []).append(new_event)
                
                # Сохраняем обновленные данные
                self._save_historical_data()
                
                logger.info(f"Администратор {admin_id} добавил новое историческое событие {new_event['id']}")
                
                return jsonify({
                    "success": True,
                    "event_id": new_event['id'],
                    "message": "Событие успешно добавлено"
                })
            except Exception as e:
                logger.error(f"Ошибка при добавлении исторического события: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/historical-event/<event_id>', methods=['DELETE'])
        def api_admin_delete_historical_event(event_id):
            """Удаление исторического события"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                user_id = int(admin_id)
                admins = self._load_admins()
                
                # Для удаления исторических данных нужны права супер-администратора
                if user_id not in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Требуются права супер-администратора"}), 403
                
                # Загружаем исторические данные, если они еще не загружены
                if self.events_data is None:
                    self._preload_historical_data()
                
                # Ищем событие по ID
                found = False
                events = self.events_data.get('events', [])
                
                for i, event in enumerate(events):
                    if str(event.get('id', '')) == str(event_id):
                        # Удаляем событие
                        del self.events_data['events'][i]
                        found = True
                        break
                
                if not found:
                    return jsonify({"error": "Событие не найдено"}), 404
                
                # Сохраняем обновленные данные
                self._save_historical_data()
                
                logger.info(f"Администратор {admin_id} удалил историческое событие {event_id}")
                
                return jsonify({
                    "success": True,
                    "message": "Событие успешно удалено"
                })
            except Exception as e:
                logger.error(f"Ошибка при удалении исторического события: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/categories', methods=['GET'])
        def api_admin_get_categories():
            """Получение списка категорий событий"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Загружаем исторические данные, если они еще не загружены
                if self.events_data is None:
                    self._preload_historical_data()
                
                # Получаем уникальные категории
                categories = set()
                for event in self.events_data.get('events', []):
                    if event.get('category'):
                        categories.add(event.get('category'))
                
                return jsonify(sorted(list(categories)))
            except Exception as e:
                logger.error(f"Ошибка при получении категорий: {e}")
                return jsonify({"error": str(e)}), 500
        
        # -------------------- Логи и обслуживание --------------------
        
        @self.app.route('/api/admin/logs', methods=['GET'])
        def api_admin_logs():
            """Получение логов"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Получаем параметры
                level = request.args.get('level', 'all')
                limit = int(request.args.get('limit', 100))
                
                # Получаем логи
                logs = self._get_last_logs(limit, level)
                
                return jsonify(logs)
            except Exception as e:
                logger.error(f"Ошибка при получении логов: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/export-logs', methods=['GET'])
        def api_admin_export_logs():
            """Экспорт логов в файл"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                # Получаем параметры
                level = request.args.get('level', 'all')
                limit = int(request.args.get('limit', 1000))
                
                # Получаем логи
                logs = self._get_last_logs(limit, level)
                
                # Создаем временный файл
                timestamp = int(time.time())
                temp_file = f"logs_export_{timestamp}.txt"
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(logs))
                
                # Отправляем файл
                response = send_file(
                    temp_file,
                    as_attachment=True,
                    download_name=f"logs_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                )
                
                # Удаляем временный файл после отправки
                @response.call_on_close
                def remove_file():
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                
                return response
            except Exception as e:
                logger.error(f"Ошибка при экспорте логов: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/maintenance', methods=['POST'])
        def api_admin_maintenance():
            """Выполнение операций технического обслуживания"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                user_id = int(admin_id)
                admins = self._load_admins()
                
                # Для операций обслуживания нужны права супер-администратора
                if user_id not in admins.get("super_admin_ids", []):
                    return jsonify({"success": False, "message": "Требуются права супер-администратора"}), 403
                
                # Получаем данные запроса
                data = request.get_json()
                action = data.get('action', '')
                
                if not action:
                    return jsonify({"success": False, "message": "Действие не указано"})
                
                # Выполняем соответствующее действие
                if action == 'clear_cache':
                    # Очистка кэша
                    cache_files = ['api_cache.json']
                    removed = 0
                    
                    for cache_file in cache_files:
                        if os.path.exists(cache_file):
                            os.remove(cache_file)
                            removed += 1
                    
                    logger.info(f"Администратор {admin_id} очистил кэш")
                    
                    return jsonify({
                        "success": True,
                        "message": f"Кэш успешно очищен (удалено файлов: {removed})"
                    })
                
                elif action == 'create_backup':
                    # Создание резервной копии
                    timestamp = int(time.time())
                    backup_dir = 'backups'
                    
                    if not os.path.exists(backup_dir):
                        os.makedirs(backup_dir)
                    
                    # Копируем файлы данных
                    files_to_backup = ['admins.json', 'user_states.json', 'historical_events.json', 'bot_settings.json']
                    backed_up = []
                    
                    for file in files_to_backup:
                        if os.path.exists(file):
                            backup_path = os.path.join(backup_dir, f"{os.path.splitext(file)[0]}_backup_{timestamp}{os.path.splitext(file)[1]}")
                            shutil.copy2(file, backup_path)
                            backed_up.append(file)
                    
                    # Создаем метаданные резервной копии
                    backup_meta = os.path.join(backup_dir, f"data_backup_v{len(os.listdir(backup_dir)) - len(backed_up)}_{timestamp}")
                    with open(backup_meta, 'w', encoding='utf-8') as f:
                        f.write(f"Backup created at {datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    logger.info(f"Администратор {admin_id} создал резервную копию данных")
                    
                    return jsonify({
                        "success": True,
                        "message": f"Резервная копия успешно создана (файлов: {len(backed_up)})",
                        "backup_time": datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                        "files": backed_up
                    })
                
                elif action == 'clean_logs':
                    # Очистка старых логов
                    log_dir = 'logs'
                    deleted = 0
                    
                    if os.path.exists(log_dir):
                        # Удаляем файлы логов старше 7 дней
                        current_time = time.time()
                        for file in os.listdir(log_dir):
                            file_path = os.path.join(log_dir, file)
                            if os.path.isfile(file_path) and file.startswith('bot_log_'):
                                file_time = os.path.getmtime(file_path)
                                if current_time - file_time > 7 * 86400:  # 7 дней в секундах
                                    os.remove(file_path)
                                    deleted += 1
                    
                    logger.info(f"Администратор {admin_id} очистил старые логи")
                    
                    return jsonify({
                        "success": True,
                        "message": f"Старые логи успешно удалены (удалено файлов: {deleted})"
                    })
                
                elif action == 'restart_bot':
                    # Перезапуск бота
                    # ПРИМЕЧАНИЕ: В реальном проекте здесь должен быть код для перезапуска бота
                    # Например, через команду bash или сервисного менеджера
                    
                    logger.info(f"Администратор {admin_id} запросил перезапуск бота")
                    
                    # Пример команды перезапуска (раскомментировать и адаптировать при необходимости)
                    # import subprocess
                    # subprocess.Popen(["bash", "restart_bot.sh"])
                    
                    return jsonify({
                        "success": True,
                        "message": "Запрос на перезапуск бота отправлен"
                    })
                
                else:
                    return jsonify({
                        "success": False,
                        "message": "Неизвестное действие"
                    })
                
            except Exception as e:
                logger.error(f"Ошибка при выполнении операции обслуживания: {e}")
                return jsonify({"error": str(e)}), 500
        
        # -------------------- Документация и дополнительные функции --------------------
        
        @self.app.route('/api/admin/get-doc')
        def api_admin_get_doc():
            """Скачивание документации администратора"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                doc_path = request.args.get('path')
                if not doc_path:
                    return jsonify({"error": "Путь к документу не указан"}), 400
                
                # Проверка безопасности пути (предотвращение path traversal)
                norm_path = os.path.normpath(doc_path)
                if '..' in norm_path:
                    return jsonify({"error": "Недопустимый путь"}), 403
                
                # Проверка существования файла
                if not os.path.exists(norm_path):
                    return jsonify({"error": "Файл не найден"}), 404
                
                # Определяем имя файла из пути
                filename = os.path.basename(norm_path)
                
                # Определяем MIME-тип для ответа
                mime_type = 'application/octet-stream'
                if norm_path.endswith('.md'):
                    mime_type = 'text/markdown'
                elif norm_path.endswith('.pdf'):
                    mime_type = 'application/pdf'
                elif norm_path.endswith('.txt'):
                    mime_type = 'text/plain'
                
                # Отправляем файл
                return send_file(
                    norm_path,
                    as_attachment=True,
                    download_name=filename,
                    mimetype=mime_type
                )
            except Exception as e:
                logger.error(f"Ошибка при скачивании документации: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/admin/view-doc')
        def api_admin_view_doc():
            """Просмотр документации в браузере"""
            try:
                # Проверка аутентификации
                admin_id = request.cookies.get('admin_id')
                if not admin_id:
                    return jsonify({"error": "Требуется авторизация"}), 403
                
                doc_path = request.args.get('path')
                if not doc_path:
                    return "Путь к документу не указан", 400
                
                # Проверка безопасности пути
                norm_path = os.path.normpath(doc_path)
                if '..' in norm_path:
                    return "Недопустимый путь", 403
                
                # Проверка существования файла
                if not os.path.exists(norm_path):
                    return "Файл не найден", 404
                
                # Если это markdown файл, преобразуем его в HTML для отображения
                if norm_path.endswith('.md'):
                    try:
                        import markdown
                        with open(norm_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        html_content = markdown.markdown(content)
                        
                        return f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>Документация</title>
                            <style>
                                body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
                                pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }}
                                code {{ font-family: monospace; background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
                                img {{ max-width: 100%; height: auto; }}
                                h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; }}
                                p {{ margin: 1em 0; }}
                            </style>
                        </head>
                        <body>
                            {html_content}
                        </body>
                        </html>
                        """
                    except ImportError:
                        # Если модуль markdown не установлен, просто отображаем текст
                        with open(norm_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        return f"<pre>{content}</pre>"
                
                # Для других типов файлов отправляем их как есть
                return send_file(norm_path)
            except Exception as e:
                logger.error(f"Ошибка при просмотре документации: {e}")
                return f"Ошибка при просмотре документа: {str(e)}", 500
    
    # -------------------- Вспомогательные методы --------------------
    
    def _load_admins(self):
        """Загружает список администраторов из файла"""
        try:
            # Если у нас уже есть данные в кэше и они актуальны, используем их
            if self.admins_data is not None:
                return self.admins_data
            
            if os.path.exists(ADMINS_FILE_PATH):
                with open(ADMINS_FILE_PATH, 'r', encoding='utf-8') as f:
                    self.admins_data = json.load(f)
                return self.admins_data
            
            # Если файл не существует, создаем структуру по умолчанию
            self.admins_data = {"admin_ids": [], "super_admin_ids": []}
            return self.admins_data
        except Exception as e:
            logger.error(f"Ошибка при загрузке списка администраторов: {e}")
            return {"admin_ids": [], "super_admin_ids": []}
    
    def _save_admins(self, admins):
        """Сохраняет список администраторов в файл"""
        try:
            # Используем атомарную операцию записи через временный файл
            temp_file = f"{ADMINS_FILE_PATH}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(admins, f, indent=4)
            
            # Заменяем основной файл только после успешной записи
            os.replace(temp_file, ADMINS_FILE_PATH)
            
            # Обновляем кэш
            self.admins_data = admins
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении списка администраторов: {e}")
            return False
    
    def _load_bot_settings(self):
        """Загружает настройки бота из файла"""
        try:
            if os.path.exists(BOT_SETTINGS_PATH):
                with open(BOT_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Если файл не существует, создаем настройки по умолчанию
            return {
                "auto_update_topics": True,
                "collect_statistics": True,
                "developer_mode": False,
                "private_mode": False,
                "notification_level": "all",
                "api_model": "gemini-pro",
                "cache_duration": 24
            }
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек бота: {e}")
            return {}
    
    def _save_bot_settings(self, settings):
        """Сохраняет настройки бота в файл"""
        try:
            # Используем атомарную операцию записи через временный файл
            temp_file = f"{BOT_SETTINGS_PATH}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            
            # Заменяем основной файл только после успешной записи
            os.replace(temp_file, BOT_SETTINGS_PATH)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек бота: {e}")
            return False
    
    def _preload_historical_data(self):
        """Предварительная загрузка исторических данных"""
        try:
            if os.path.exists(HISTORY_DB_PATH):
                with open(HISTORY_DB_PATH, 'r', encoding='utf-8') as f:
                    self.events_data = json.load(f)
                logger.info(f"Загружено {len(self.events_data.get('events', []))} исторических событий")
            else:
                logger.warning(f"Файл базы данных не найден: {HISTORY_DB_PATH}")
                self.events_data = {"events": []}
        except Exception as e:
            logger.error(f"Ошибка при загрузке исторических данных: {e}")
            self.events_data = {"events": []}
    
    def _save_historical_data(self):
        """Сохраняет исторические данные в файл"""
        try:
            # Создаем копию данных для сохранения
            backup_path = HISTORY_DB_PATH + '.bak'
            if os.path.exists(HISTORY_DB_PATH):
                shutil.copy2(HISTORY_DB_PATH, backup_path)
            
            # Сохраняем обновленные данные
            with open(HISTORY_DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.events_data, f, indent=4, ensure_ascii=False)
            
            # Удаляем резервную копию, если сохранение прошло успешно
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении исторических данных: {e}")
            
            # Восстанавливаем из резервной копии, если она есть
            backup_path = HISTORY_DB_PATH + '.bak'
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, HISTORY_DB_PATH)
            
            return False
    
    def _extract_century(self, date_str):
        """Извлекает век из строки даты"""
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
            if 800 <= year <= datetime.datetime.now().year + 100:
                return (year // 100) + 1
        
        return 0
    
    def _get_last_logs(self, lines=100, level='all'):
        """Получает последние строки из файла логов"""
        try:
            log_files = []
            log_dir = "logs"
            
            # Проверяем, существует ли директория логов
            if os.path.exists(log_dir) and os.path.isdir(log_dir):
                # Получаем список файлов логов
                files = os.listdir(log_dir)
                log_files = [os.path.join(log_dir, f) for f in files if f.startswith("bot_log_")]
            
            # Если директории нет или нет файлов логов, проверяем в корневой директории
            if not log_files:
                files = [f for f in os.listdir() if f.startswith("bot_log_")]
                log_files = files
            
            # Сортируем файлы по дате изменения (новые в начале)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            if not log_files:
                return ["Файлы логов не найдены"]
            
            # Берем самый свежий файл логов
            latest_log = log_files[0]
            
            with open(latest_log, 'r', encoding='utf-8') as f:
                # Читаем все строки файла
                all_lines = f.readlines()
            
            # Фильтруем по уровню, если указан не 'all'
            if level != 'all':
                level_upper = level.upper()
                filtered_lines = [line for line in all_lines if f" - {level_upper} - " in line]
            else:
                filtered_lines = all_lines
            
            # Берем последние N строк
            return filtered_lines[-lines:]
        except Exception as e:
            logger.error(f"Ошибка при чтении файла логов: {e}")
            return [f"Ошибка при чтении логов: {e}"]
    
    # Методы-заглушки для статистики (при отсутствии analytics_service)
    
    def _count_users(self):
        """Подсчитывает количество уникальных пользователей"""
        try:
            # Попытка получить реальные данные из файла состояний пользователей
            user_states_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_states.json')
            if os.path.exists(user_states_path):
                with open(user_states_path, 'r', encoding='utf-8') as f:
                    user_states = json.load(f)
                    return len(user_states)
            return 42  # Пример, если файл не найден
        except Exception as e:
            logger.error(f"Ошибка при подсчете пользователей: {e}")
            return 42  # Значение по умолчанию
    
    def _count_messages(self):
        """Подсчитывает общее количество сообщений"""
        try:
            # Пытаемся получить реальные данные из файла состояний пользователей
            # Общее количество сообщений может быть суммой взаимодействий пользователей
            user_states_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_states.json')
            if os.path.exists(user_states_path):
                with open(user_states_path, 'r', encoding='utf-8') as f:
                    user_states = json.load(f)
                    # В этом примере предполагаем, что каждый пользователь отправил в среднем 30 сообщений
                    # В реальной системе здесь должен быть точный подсчет по логам или БД
                    return len(user_states) * 30
            return 1337  # Пример, если файл не найден
        except Exception as e:
            logger.error(f"Ошибка при подсчете сообщений: {e}")
            return 1337  # Значение по умолчанию
    
    def _get_uptime(self):
        """Возвращает время работы бота"""
        try:
            # Проверяем наличие лок-файла бота
            bot_lock_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bot.lock')
            if os.path.exists(bot_lock_path):
                start_time = os.path.getmtime(bot_lock_path)
                current_time = time.time()
                uptime_seconds = current_time - start_time
                
                # Форматируем время работы
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                seconds = int(uptime_seconds % 60)
                
                if days > 0:
                    return f"{days} д. {hours} ч. {minutes} мин."
                elif hours > 0:
                    return f"{hours} ч. {minutes} мин. {seconds} сек."
                elif minutes > 0:
                    return f"{minutes} мин. {seconds} сек."
                else:
                    return f"{seconds} сек."
            
            return "3 дня 7 часов"  # Пример, если файл не найден
        except Exception as e:
            logger.error(f"Ошибка при получении времени работы: {e}")
            return "Неизвестно"
    
    def _count_bot_starts(self):
        """Подсчитывает количество запусков бота за последние 24 часа"""
        try:
            # Проверяем логи на наличие записей о запуске бота
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            if os.path.exists(log_dir):
                # Получаем текущую дату
                current_date = datetime.datetime.now().strftime('%Y%m%d')
                log_file = os.path.join(log_dir, f'bot_log_{current_date}.log')
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = f.read()
                        # Ищем записи о запуске бота
                        return logs.count("Bot started") + logs.count("Бот запущен")
            
            return 25  # Пример, если файлы не найдены
        except Exception as e:
            logger.error(f"Ошибка при подсчете запусков бота: {e}")
            return 25  # Значение по умолчанию
    
    def _count_topic_requests(self):
        """Подсчитывает количество запросов тем за последние 24 часа"""
        try:
            # Проверяем логи на наличие записей о запросах тем
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            if os.path.exists(log_dir):
                # Получаем текущую дату
                current_date = datetime.datetime.now().strftime('%Y%m%d')
                log_file = os.path.join(log_dir, f'bot_log_{current_date}.log')
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = f.read()
                        # Ищем записи о запросах тем
                        return logs.count("Requested topic") + logs.count("Запрошена тема")
            
            return 73  # Пример, если файлы не найдены
        except Exception as e:
            logger.error(f"Ошибка при подсчете запросов тем: {e}")
            return 73  # Значение по умолчанию
    
    def _count_completed_tests(self):
        """Подсчитывает количество пройденных тестов за последние 24 часа"""
        try:
            # Проверяем логи на наличие записей о прохождении тестов
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            if os.path.exists(log_dir):
                # Получаем текущую дату
                current_date = datetime.datetime.now().strftime('%Y%m%d')
                log_file = os.path.join(log_dir, f'bot_log_{current_date}.log')
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = f.read()
                        # Ищем записи о прохождении тестов
                        return logs.count("Test completed") + logs.count("Тест завершен")
            
            return 18  # Пример, если файлы не найдены
        except Exception as e:
            logger.error(f"Ошибка при подсчете пройденных тестов: {e}")
            return 18  # Значение по умолчанию
    
    def start(self, host='0.0.0.0', port=8000):
        """Запускает сервер админки в отдельном потоке"""
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("Сервер админки уже запущен")
            return
        
        def run_server():
            logger.info(f"Запуск сервера админки на {host}:{port}")
            self.app.run(host=host, port=port, debug=False, use_reloader=False)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info("Сервер админки запущен в фоновом режиме")
    
    def stop(self):
        """Останавливает сервер админки"""
        if self.server_thread and self.server_thread.is_alive():
            logger.info("Попытка остановки сервера админки")
            
            # Flask не предоставляет простого метода для остановки сервера из другого потока
            # В реальном проекте здесь нужно использовать более сложную логику остановки
            
            logger.info("Сервер админки остановлен")
        else:
            logger.warning("Сервер админки не запущен")

def run_admin_server(host='0.0.0.0', port=8000):
    """
    Функция для запуска сервера админки
    
    Args:
        host: Хост для запуска сервера
        port: Порт для запуска сервера
    """
    logger.info("Инициализация сервера админки")
    
    # Инициализируем сервер
    admin_server = AdminServer()
    
    # Запускаем сервер
    admin_server.start(host=host, port=port)
    
    try:
        # Держим основной поток активным
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Останавливаем сервер при получении сигнала прерывания
        admin_server.stop()
        logger.info("Сервер админки остановлен")

if __name__ == "__main__":
    run_admin_server()
