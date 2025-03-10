"""
Сервер веб-приложения для визуализации исторических данных
"""

import os
import json
import logging
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import time
from datetime import datetime
import sys
import shutil
import zipfile


# Путь к файлу с историческими данными
HISTORY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "history_db_generator/russian_history_database.json")

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))

CORS(app)  # Включаем поддержку CORS для всех маршрутов

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

@app.route('/api/chart/daily_activity')
def api_chart_daily_activity():
    """API для генерации графика ежедневной активности"""
    #This section is a placeholder, needs a proper implementation
    return jsonify({"error": "Сервис аналитики недоступен"}), 500


# API-эндпоинты для работы с админ-панелью
@app.route('/api/admin/stats')
def admin_stats():
    """API для получения статистики бота"""
    try:
        # Получаем общую статистику
        stats = {
            "user_count": _count_users(),
            "message_count": _count_messages(),
            "uptime": _get_uptime(),
            "bot_starts": _count_bot_starts(),
            "topic_requests": _count_topic_requests(),
            "completed_tests": _count_completed_tests()
        }

        return jsonify(stats)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/system-info')
def admin_system_info():
    """API для получения информации о системе"""
    try:
        import psutil
        # Получаем информацию о системе
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)

        # Получаем список процессов Python
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
            if 'python' in proc.info['name'].lower():
                try:
                    mem_usage = proc.memory_info().rss / (1024 * 1024)
                    python_processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "username": proc.info['username'],
                        "memory_percent": proc.info['memory_percent'],
                        "memory_mb": round(mem_usage, 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        # Сортируем по использованию памяти
        python_processes.sort(key=lambda x: x["memory_percent"], reverse=True)

        system_info = {
            "cpu": {
                "percent": cpu_percent
            },
            "memory": {
                "total_gb": round(mem.total / (1024 * 1024 * 1024), 2),
                "used_gb": round(mem.used / (1024 * 1024 * 1024), 2),
                "free_gb": round(mem.free / (1024 * 1024 * 1024), 2),
                "percent": mem.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                "used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
                "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                "percent": disk.percent
            },
            "python_processes": python_processes[:5]  # Только 5 первых процессов
        }

        return jsonify(system_info)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о системе: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/user-stats')
def admin_user_stats():
    """API для получения подробной статистики пользователей"""
    try:
        # Заглушка для демонстрации
        user_stats = {
            "daily_users": {
                "days": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
                "counts": [23, 35, 45, 38, 42, 28, 19]
            },
            "hourly_users": {
                "hours": [
                    "00:00-06:00", 
                    "06:00-12:00", 
                    "12:00-18:00", 
                    "18:00-00:00"
                ],
                "counts": [12, 48, 67, 53]
            },
            "test_stats": {
                "avg_score": 72.5,
                "completed_tests": 145,
                "abandoned_tests": 27
            }
        }

        return jsonify(user_stats)
    except Exception as e:
        logger.error(f"Ошибка при получении подробной статистики пользователей: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/admins')
def admin_get_admins():
    """API для получения списка администраторов"""
    try:
        if os.path.exists('admins.json'):
            with open('admins.json', 'r', encoding='utf-8') as f:
                admins = json.load(f)
            return jsonify(admins)
        else:
            default_data = {"admin_ids": [], "super_admin_ids": []}
            return jsonify(default_data)
    except Exception as e:
        logger.error(f"Ошибка при получении списка администраторов: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/admins', methods=['POST'])
def admin_manage_admins():
    """API для управления администраторами"""
    try:
        data = request.json
        action = data.get('action')
        user_id = data.get('user_id')
        is_super = data.get('is_super', False)

        if not user_id or not action:
            return jsonify({"error": "Недостаточно данных"}), 400

        # Загружаем текущий список администраторов
        if os.path.exists('admins.json'):
            with open('admins.json', 'r', encoding='utf-8') as f:
                admins = json.load(f)
        else:
            admins = {"admin_ids": [], "super_admin_ids": []}

        if action == 'add':
            # Добавляем нового администратора
            if is_super:
                if user_id not in admins.get("super_admin_ids", []):
                    admins.setdefault("super_admin_ids", []).append(user_id)
                    logger.info(f"Добавлен супер-админ: {user_id}")
            else:
                if user_id not in admins.get("admin_ids", []):
                    admins.setdefault("admin_ids", []).append(user_id)
                    logger.info(f"Добавлен админ: {user_id}")

        elif action == 'remove':
            # Удаляем администратора
            if user_id in admins.get("admin_ids", []):
                admins["admin_ids"].remove(user_id)
                logger.info(f"Удален админ: {user_id}")
            elif user_id in admins.get("super_admin_ids", []):
                admins["super_admin_ids"].remove(user_id)
                logger.info(f"Удален супер-админ: {user_id}")
            else:
                return jsonify({"error": "Администратор не найден"}), 404

        # Сохраняем обновленный список администраторов
        temp_file = "admins.json.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(admins, f, indent=4)
        os.replace(temp_file, "admins.json")

        return jsonify({"success": True, "admins": admins})
    except Exception as e:
        logger.error(f"Ошибка при управлении администраторами: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/logs')
def admin_get_logs():
    """API для получения логов"""
    try:
        level = request.args.get('level')
        limit = int(request.args.get('limit', 100))

        log_files = _get_log_files()

        if not log_files:
            return jsonify({"logs": ["Файлы логов не найдены"]})

        # Берем самый свежий файл логов
        latest_log = log_files[0]

        with open(latest_log, 'r', encoding='utf-8') as f:
            log_lines = list(f)[-limit:]

        # Фильтрация по уровню логирования, если указан
        if level and level.lower() != 'all':
            level = level.upper()
            filtered_logs = []
            for line in log_lines:
                if f" - {level} - " in line:
                    filtered_logs.append(line)
            log_lines = filtered_logs

        return jsonify({"logs": log_lines})
    except Exception as e:
        logger.error(f"Ошибка при получении логов: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/clean-logs', methods=['POST'])
def admin_clean_logs():
    """API для очистки старых лог-файлов"""
    try:
        # Получаем все лог-файлы
        log_files = _get_log_files()

        if not log_files:
            return jsonify({"message": "Лог-файлы не найдены"})

        # Оставляем только файлы старше 7 дней (кроме текущего)
        import datetime
        current_date = datetime.datetime.now().date()
        files_to_delete = []
        current_log = None

        for log_file in log_files:
            try:
                # Извлекаем дату из имени файла
                file_name = os.path.basename(log_file)
                if file_name == "bot.log":
                    current_log = log_file
                    continue

                if file_name.startswith("bot_log_") and len(file_name) > 12:
                    date_str = file_name[8:16]  # Формат YYYYMMDD
                    file_date = datetime.datetime.strptime(date_str, "%Y%m%d").date()

                    # Если файл старше 7 дней, добавляем в список на удаление
                    if (current_date - file_date).days > 7:
                        files_to_delete.append(log_file)
            except Exception as e:
                logger.error(f"Ошибка при обработке даты файла лога {log_file}: {e}")

        # Удаляем старые лог-файлы
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Ошибка при удалении лог-файла {file_path}: {e}")

        # Очищаем текущий лог, если он слишком большой (более 10 МБ)
        current_log_truncated = False
        if current_log and os.path.exists(current_log):
            file_size = os.path.getsize(current_log)
            if file_size > 10 * 1024 * 1024:  # 10 МБ
                try:
                    # Создаем резервную копию перед очисткой
                    backup_path = f"{current_log}.bak"
                    import shutil
                    shutil.copy2(current_log, backup_path)

                    # Очищаем файл, оставляя последние 1000 строк
                    with open(current_log, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    with open(current_log, 'w', encoding='utf-8') as f:
                        f.writelines(lines[-1000:])

                    current_log_truncated = True
                    logger.info(f"Текущий лог-файл усечен (оставлено последние 1000 строк)")
                except Exception as e:
                    logger.error(f"Ошибка при усечении текущего лог-файла: {e}")

        result = {
            "deleted_count": deleted_count,
            "truncated": current_log_truncated
        }

        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при очистке логов: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/settings')
def admin_get_settings():
    """API для получения настроек бота"""
    try:
        settings = _get_bot_settings()
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Ошибка при получении настроек бота: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/settings', methods=['POST'])
def admin_update_settings():
    """API для обновления настроек бота"""
    try:
        new_settings = request.json

        # Валидация настроек
        required_fields = [
            "auto_update_topics", 
            "collect_statistics", 
            "developer_mode", 
            "private_mode", 
            "notification_enabled", 
            "log_level", 
            "max_messages_per_user"
        ]

        for field in required_fields:
            if field not in new_settings:
                return jsonify({"error": f"Отсутствует обязательное поле: {field}"}), 400

        # Сохраняем настройки через временный файл
        temp_file = "bot_settings.json.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(new_settings, f, indent=4)

        # Атомарно заменяем оригинальный файл
        os.replace(temp_file, "bot_settings.json")

        logger.info("Настройки бота успешно обновлены")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек бота: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/clear-cache', methods=['POST'])
def admin_clear_cache():
    """API для очистки кэша API"""
    try:
        # Проверяем файл кэша API
        api_cache_file = 'api_cache.json'
        api_cache_file_removed = False

        if os.path.exists(api_cache_file):
            try:
                os.remove(api_cache_file)
                api_cache_file_removed = True
                logger.info(f"Файл кэша API удален")
            except Exception as e:
                logger.error(f"Ошибка при удалении файла кэша API: {e}")

        result = {
            "cache_cleared": api_cache_file_removed
        }

        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/backup', methods=['POST'])
def admin_create_backup():
    """API для создания резервной копии данных бота"""
    try:
        # Текущее время для имени файла
        timestamp = int(time.time())
        backup_dir = "backups"

        # Создаем директорию для резервных копий, если она не существует
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # Список файлов для резервного копирования
        files_to_backup = [
            'user_states.json',
            'historical_events.json',
            'admins.json',
            'bot_settings.json',
            'api_cache.json'
        ]

        # Копируем каждый файл в директорию резервных копий
        backup_files = []
        for file_name in files_to_backup:
            if os.path.exists(file_name):
                backup_file_name = f"{file_name.split('.')[0]}_backup_{timestamp}.json"
                backup_path = os.path.join(backup_dir, backup_file_name)
                try:
                    import shutil
                    shutil.copy2(file_name, backup_path)
                    backup_files.append({
                        "original": file_name, 
                        "backup": backup_file_name
                    })
                    logger.info(f"Создана резервная копия файла {file_name}")
                except Exception as e:
                    logger.error(f"Ошибка при копировании файла {file_name}: {e}")

        # Также создаем общую резервную копию
        data_backup_path = os.path.join(backup_dir, f"data_backup_v{len(backup_files}_{timestamp}")
        try:
            import zipfile
            with zipfile.ZipFile(data_backup_path + '.zip', 'w') as zipf:
                for file_name in files_to_backup:
                    if os.path.exists(file_name):
                        zipf.write(file_name)
                # Добавляем лог в архив
                log_files = _get_log_files()
                if log_files:
                    zipf.write(log_files[0])
            logger.info(f"Создана общая резервная копия данных: {data_backup_path}.zip")
            backup_files.append({
                "original": "Все данные", 
                "backup": f"data_backup_v{len(backup_files)}_{timestamp}.zip"
            })
        except Exception as e:
            logger.error(f"Ошибка при создании общей резервной копии: {e}")

        result = {
            "backup_files": backup_files,
            "timestamp": timestamp,
            "backup_dir": backup_dir
        }

        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/restart', methods=['POST'])
def admin_restart_bot():
    """API для перезапуска бота"""
    try:
        # Создаем файл-индикатор для restart.sh скрипта
        with open("bot.restart", "w") as f:
            f.write(f"Restart triggered at {datetime.now()}")

        logger.warning("Бот перезапускается через API админ-панели")

        # В реальном сценарии здесь бы запускался скрипт перезапуска
        # Но для демонстрации просто вернем успешный результат
        return jsonify({"success": True, "message": "Команда на перезапуск отправлена"})
    except Exception as e:
        logger.error(f"Ошибка при перезапуске бота: {e}")
        return jsonify({"error": str(e)}), 500

# Вспомогательные функции для админ-панели
def _count_users():
    """Подсчитывает количество уникальных пользователей"""
    try:
        # Запасной вариант - чтение из user_states.json
        if os.path.exists('user_states.json'):
            with open('user_states.json', 'r', encoding='utf-8') as f:
                user_states = json.load(f)
                return len(user_states)

        return 0
    except Exception as e:
        logger.error(f"Ошибка при подсчёте пользователей: {e}")
        return 0

def _count_messages():
    """Подсчитывает общее количество сообщений"""
    try:
        # Заглушка для демонстрации
        return 1250
    except Exception as e:
        logger.error(f"Ошибка при подсчёте сообщений: {e}")
        return 0

def _get_uptime():
    """Возвращает время работы бота"""
    try:
        # Заглушка для демонстрации
        return "2 дн. 5 ч. 30 мин."
    except Exception as e:
        logger.error(f"Ошибка при расчёте времени работы: {e}")
        return "Неизвестно"

def _count_bot_starts():
    """Подсчитывает количество запусков бота за последние 24 часа"""
    try:
        # Заглушка для демонстрации
        return 45
    except Exception as e:
        logger.error(f"Ошибка при подсчёте запусков бота: {e}")
        return 0

def _count_topic_requests():
    """Подсчитывает количество запросов тем за последние 24 часа"""
    try:
        # Заглушка для демонстрации
        return 128
    except Exception as e:
        logger.error(f"Ошибка при подсчёте запросов тем: {e}")
        return 0

def _count_completed_tests():
    """Подсчитывает количество пройденных тестов за последние 24 часа"""
    try:
        # Заглушка для демонстрации
        return 87
    except Exception as e:
        logger.error(f"Ошибка при подсчёте пройденных тестов: {e}")
        return 0

def _get_log_files():
    """Получает список всех файлов логов"""
    log_files = []

    # Проверяем директорию логов
    log_dir = "logs"
    if os.path.exists(log_dir) and os.path.isdir(log_dir):
        for file_name in os.listdir(log_dir):
            if file_name.startswith("bot_log_") or file_name == "bot.log":
                log_files.append(os.path.join(log_dir, file_name))

    # Проверяем корневую директорию
    for file_name in os.listdir("."):
        if file_name.startswith("bot_log_") or file_name == "bot.log":
            log_files.append(file_name)

    # Сортируем по времени изменения (новые сначала)
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    return log_files

def _get_bot_settings():
    """Получает текущие настройки бота"""
    try:
        if os.path.exists('bot_settings.json'):
            with open('bot_settings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Возвращаем настройки по умолчанию
            return {
                "auto_update_topics": True,
                "collect_statistics": True,
                "developer_mode": False,
                "private_mode": False,
                "notification_enabled": True,
                "log_level": "INFO",
                "max_messages_per_user": 100
            }
    except Exception as e:
        logger.error(f"Ошибка при загрузке настроек бота: {e}")
        return {}

def run_server(host='0.0.0.0', port=8080):
    """Запуск веб-сервера"""
    logger.info(f"Запуск веб-сервера на {host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    run_server()