import threading
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler

from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION

class Bot:
    """Класс для управления Telegram ботом"""

    def __init__(self, config, logger, command_handlers):
        self.config = config
        self.logger = logger
        self.handlers = command_handlers
        self.updater = None
        
        # Инициализируем админ-панель и привязываем её к обработчику команд
        from src.admin_panel import AdminPanel
        admin_panel = AdminPanel(logger, config)
        self.handlers.admin_panel = admin_panel

    def setup(self):
        """Настройка бота и диспетчера"""
        try:
            # Инициализируем бота и диспетчер с оптимизированными настройками
            self.updater = Updater(self.config.telegram_token, use_context=True, workers=4)  # Увеличиваем количество рабочих потоков
            dp = self.updater.dispatcher

            # Создаем ConversationHandler для управления диалогом
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', self.handlers.start)],
                states={
                    TOPIC: [
                        CallbackQueryHandler(self.handlers.button_handler)
                    ],
                    CHOOSE_TOPIC: [
                        CallbackQueryHandler(self.handlers.button_handler, pattern='^(more_topics|custom_topic|back_to_menu)$'),
                        CallbackQueryHandler(self.handlers.choose_topic, pattern='^topic_'),
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_custom_topic)
                    ],
                    TEST: [
                        CallbackQueryHandler(self.handlers.button_handler)
                    ],
                    ANSWER: [
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_answer),
                        CallbackQueryHandler(self.handlers.button_handler)  # Добавляем обработчик для кнопки завершения теста
                    ],
                    CONVERSATION: [
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_conversation),
                        CallbackQueryHandler(self.handlers.button_handler)  # Обработчик для кнопки возврата в меню
                    ],
                    MAP: [
                        CallbackQueryHandler(self.handlers.button_handler)  # Обработчик для взаимодействия с картой
                    ]
                },
                fallbacks=[CommandHandler('start', self.handlers.start)],
                allow_reentry=True
            )

            # Добавляем обработчики
            dp.add_error_handler(self.handlers.error_handler)
            dp.add_handler(conv_handler)
            
            # Добавляем обработчик для команды администратора
            dp.add_handler(CommandHandler('admin', self.handlers.admin_command))
            
            # Добавляем обработчик для обработки callback запросов администратора
            dp.add_handler(CallbackQueryHandler(self.handlers.admin_callback, pattern='^admin_'))

            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при настройке бота")
            return False

    def run(self):
        """Запускает бота и веб-сервер для логов"""
        self.logger.info("Запуск бота и веб-сервера логов...")

        # Запуск фонового процесса для веб-сервера
        threading.Thread(target=self.run_log_server, daemon=True).start()

        try:
            # Включаем сбор обновлений для реагирования на сообщения, запускаем бота
            # Установка более длинного таймаута для обработки конфликтов
            # Используем drop_pending_updates=True (не используем clean=True, так как они взаимоисключающие)
            self.updater.start_polling(timeout=30, drop_pending_updates=True)
            self.logger.info("Бот успешно запущен")

            # Остаемся в режиме работы до получения Ctrl+C
            self.updater.idle()
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            # Попытка принудительного завершения updater если он был создан
            if hasattr(self, 'updater'):
                self.updater.stop()
                
    def run_log_server(self):
        """Запускает простой веб-сервер для отображения логов"""
        from flask import Flask, render_template_string, send_file, request
        import os
        from datetime import datetime
        
        # Создаем приложение Flask
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            # Получаем список всех лог-файлов
            log_files = []
            log_dir = "logs"
            if os.path.exists(log_dir):
                for file in os.listdir(log_dir):
                    if file.startswith('bot_log_') and file.endswith('.log'):
                        log_path = os.path.join(log_dir, file)
                        size = os.path.getsize(log_path)
                        mtime = os.path.getmtime(log_path)
                        mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                        log_files.append({
                            'name': file,
                            'path': log_path,
                            'size': f"{size / 1024:.1f} KB",
                            'mtime': mtime_str
                        })
            
            # Сортируем по времени изменения (новые сверху)
            log_files.sort(key=lambda x: x['name'], reverse=True)
            
            # HTML шаблон для страницы
            template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>История России Бот - Логи</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    h1 {
                        color: #333;
                        border-bottom: 2px solid #ddd;
                        padding-bottom: 10px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                        background-color: white;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    }
                    th, td {
                        padding: 12px 15px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }
                    th {
                        background-color: #4CAF50;
                        color: white;
                    }
                    tr:hover {
                        background-color: #f5f5f5;
                    }
                    a {
                        color: #2196F3;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                    .refresh {
                        display: inline-block;
                        margin-top: 20px;
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 15px;
                        border-radius: 4px;
                        text-decoration: none;
                    }
                    .no-logs {
                        text-align: center;
                        padding: 20px;
                        color: #666;
                    }
                    .log-content {
                        white-space: pre-wrap;
                        font-family: monospace;
                        padding: 15px;
                        background-color: #f8f8f8;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        margin-top: 20px;
                        overflow-x: auto;
                        max-height: 600px;
                        overflow-y: auto;
                    }
                    .error {
                        color: #D32F2F;
                    }
                    .info {
                        color: #1976D2;
                    }
                    .warning {
                        color: #FFA000;
                    }
                    .critical {
                        color: #B71C1C;
                        font-weight: bold;
                    }
                    .back-link {
                        margin-bottom: 15px;
                        display: inline-block;
                    }
                </style>
            </head>
            <body>
                <h1>История России Бот - Логи</h1>
                
                {% if log_data %}
                    <a href="/" class="back-link">← Назад к списку логов</a>
                    <h2>{{ current_log }}</h2>
                    <div class="log-content">{{ log_data|safe }}</div>
                {% else %}
                    {% if log_files %}
                        <table>
                            <tr>
                                <th>Имя файла</th>
                                <th>Размер</th>
                                <th>Последнее изменение</th>
                                <th>Действия</th>
                            </tr>
                            {% for log in log_files %}
                            <tr>
                                <td>{{ log.name }}</td>
                                <td>{{ log.size }}</td>
                                <td>{{ log.mtime }}</td>
                                <td>
                                    <a href="/view/{{ log.name }}">Просмотр</a> |
                                    <a href="/download/{{ log.name }}">Скачать</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </table>
                    {% else %}
                        <div class="no-logs">Лог-файлы не найдены</div>
                    {% endif %}
                {% endif %}
                
                <a href="javascript:location.reload()" class="refresh">Обновить</a>
            </body>
            </html>
            """
            
            return render_template_string(template, log_files=log_files, log_data=None, current_log=None)
        
        @app.route('/view/<path:filename>')
        def view_log(filename):
            log_path = os.path.join("logs", filename)
            
            if not os.path.exists(log_path) or not filename.startswith('bot_log_') or not filename.endswith('.log'):
                return "Файл не найден", 404
            
            # Читаем содержимое лог-файла
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Раскрашиваем различные типы сообщений
                content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                content = content.replace('ERROR', '<span class="error">ERROR</span>')
                content = content.replace('INFO', '<span class="info">INFO</span>')
                content = content.replace('WARNING', '<span class="warning">WARNING</span>')
                content = content.replace('CRITICAL', '<span class="critical">CRITICAL</span>')
                
                # HTML шаблон с содержимым лога
                template = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Лог: {{ current_log }}</title>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            max-width: 1200px;
                            margin: 0 auto;
                            padding: 20px;
                            background-color: #f5f5f5;
                        }
                        h1 {
                            color: #333;
                            border-bottom: 2px solid #ddd;
                            padding-bottom: 10px;
                        }
                        .back-link {
                            margin-bottom: 15px;
                            display: inline-block;
                        }
                        .log-content {
                            white-space: pre-wrap;
                            font-family: monospace;
                            padding: 15px;
                            background-color: #f8f8f8;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                            margin-top: 20px;
                            overflow-x: auto;
                            max-height: 600px;
                            overflow-y: auto;
                        }
                        .error {
                            color: #D32F2F;
                        }
                        .info {
                            color: #1976D2;
                        }
                        .warning {
                            color: #FFA000;
                        }
                        .critical {
                            color: #B71C1C;
                            font-weight: bold;
                        }
                        .refresh {
                            display: inline-block;
                            margin-top: 20px;
                            background-color: #4CAF50;
                            color: white;
                            padding: 10px 15px;
                            border-radius: 4px;
                            text-decoration: none;
                        }
                    </style>
                </head>
                <body>
                    <h1>Просмотр лог-файла</h1>
                    <a href="/" class="back-link">← Назад к списку логов</a>
                    <h2>{{ current_log }}</h2>
                    <div class="log-content">{{ log_data|safe }}</div>
                    <a href="javascript:location.reload()" class="refresh">Обновить</a>
                </body>
                </html>
                """
                
                return render_template_string(template, log_data=content, current_log=filename)
            except Exception as e:
                return f"Ошибка при чтении файла: {e}", 500
        
        @app.route('/download/<path:filename>')
        def download_log(filename):
            log_path = os.path.join("logs", filename)
            
            if not os.path.exists(log_path) or not filename.startswith('bot_log_') or not filename.endswith('.log'):
                return "Файл не найден", 404
            
            return send_file(log_path, as_attachment=True)
        
        # Запускаем Flask-сервер на порту 8080
        try:
            self.logger.info("Запуск веб-сервера для просмотра логов на порту 8080")
            app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
        except Exception as e:
            self.logger.error(f"Ошибка запуска веб-сервера логов: {e}")
        try:
            import http.server
            import socketserver
            import threading
            import os
            
            # Определяем путь к директории с логами
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # Устанавливаем порт и handler
            PORT = 8080
            Handler = http.server.SimpleHTTPRequestHandler
            
            # Настраиваем и запускаем сервер
            self.logger.info(f"Запуск веб-сервера логов на порту {PORT}")
            httpd = socketserver.TCPServer(("0.0.0.0", PORT), Handler)
            
            # Запускаем сервер в отдельном потоке
            httpd.serve_forever()
        except Exception as e:
            self.logger.error(f"Ошибка при запуске веб-сервера логов: {e}")


class BotManager:
    """Класс для управления запуском бота и его жизненным циклом"""
    
    def __init__(self):
        self.logger = None
        
    def run(self):
        """Запускает основную функцию для инициализации и запуска бота"""
        from main import main
        main()