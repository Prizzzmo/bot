import os
import re
from flask import Flask, render_template, jsonify
from datetime import datetime
import threading
import logging
from logging.handlers import RotatingFileHandler

# Инициализация Flask-приложения
app = Flask(__name__)

# Настройка логирования для Flask
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
flask_handler = RotatingFileHandler('flask_log.log', maxBytes=10485760, backupCount=3)
flask_handler.setFormatter(log_formatter)
app.logger.addHandler(flask_handler)
app.logger.setLevel(logging.INFO)

# Шаблон HTML для отображения логов
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Логи бота истории России</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
            text-align: center;
        }
        h2 {
            color: #444;
            margin-top: 20px;
        }
        .log-container {
            height: 600px;
            overflow-y: auto;
            background-color: #f9f9f9;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 3px;
            margin-bottom: 20px;
        }
        .log-entry {
            margin-bottom: 5px;
            padding: 5px;
            border-bottom: 1px solid #eee;
        }
        .error { color: #d9534f; font-weight: bold; }
        .warning { color: #f0ad4e; }
        .info { color: #5bc0de; }
        .debug { color: #5cb85c; }
        .critical { color: #ff0000; background-color: #ffecec; font-weight: bold; padding: 5px; }

        .controls {
            margin-bottom: 20px;
        }
        button {
            background-color: #337ab7;
            color: white;
            border: none;
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 3px;
            margin-right: 10px;
        }
        button:hover {
            background-color: #286090;
        }
        .filter-group {
            margin: 10px 0;
        }
        .filter-group label {
            margin-right: 10px;
        }

        /* Новые стили для навигации */
        .navigation {
            display: flex;
            justify-content: center;
            margin: 20px 0;
            border-bottom: 1px solid #ddd;
            padding-bottom: 15px;
        }

        .nav-button {
            background-color: #f8f9fa;
            color: #444;
            border: 1px solid #ddd;
            padding: 10px 20px;
            margin: 0 10px;
            cursor: pointer;
            border-radius: 5px;
            font-size: 16px;
            transition: all 0.3s ease;
        }

        .nav-button:hover {
            background-color: #e9ecef;
        }

        .nav-button.active {
            background-color: #337ab7;
            color: white;
            border-color: #2e6da4;
        }

        #main-section {
            text-align: center;
            padding: 20px;
            line-height: 1.6;
        }

        #main-section p {
            margin-bottom: 15px;
            font-size: 16px;
        }

        /* Стили для чата */
        .chat-container {
            max-width: 800px;
            margin: 20px auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }

        .chat-header {
            background-color: #337ab7;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
        }

        .chat-messages {
            height: 400px;
            overflow-y: auto;
            padding: 15px;
            background-color: #f9f9f9;
        }

        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
            max-width: 70%;
        }

        .user-message {
            background-color: #DCF8C6;
            margin-left: auto;
            text-align: right;
        }

        .bot-message {
            background-color: #E9EAEC;
            margin-right: auto;
        }

        .chat-input {
            display: flex;
            padding: 10px;
            background-color: #f0f0f0;
        }

        .chat-input input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-right: 10px;
        }

        .chat-input button {
            background-color: #337ab7;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
        }

        .chat-input button:hover {
            background-color: #286090;
        }

        .typing-indicator {
            padding: 10px;
            color: #777;
            font-style: italic;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Панель управления ботом истории России</h1>

        <div class="navigation">
            <button onclick="showLogs()" class="nav-button active" id="logs-btn">Просмотр логов</button>
            <button onclick="showMainPage()" class="nav-button" id="main-btn">Главная страница</button>
        </div>

        <div id="logs-section">
            <h2>Логи бота</h2>
            <div class="controls">
                <button onclick="refreshLogs()">Обновить логи</button>
                <button onclick="clearFilters()">Сбросить фильтры</button>

                <div class="filter-group">
                    <label><input type="checkbox" id="show-error" checked> Ошибки</label>
                    <label><input type="checkbox" id="show-warning" checked> Предупреждения</label>
                    <label><input type="checkbox" id="show-info" checked> Информация</label>
                    <label><input type="checkbox" id="show-debug" checked> Отладка</label>
                    <label><input type="checkbox" id="show-critical" checked> Критические</label>
                </div>
            </div>
            <div class="log-container" id="logs"></div>
        </div>

        <div id="main-section" style="display: none;">
            <h2>Главная страница</h2>
            <p>Добро пожаловать в панель управления ботом истории России!</p>
            <p>Этот веб-интерфейс позволяет просматривать логи работы бота и отслеживать его активность.</p>
            <p>Для просмотра логов нажмите кнопку "Просмотр логов" вверху страницы.</p>
            <p>Чтобы связаться с ботом, используйте чат ниже:</p>
            <div class="chat-container">
                <div class="chat-header">Чат с ботом</div>
                <div class="chat-messages" id="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" id="chat-input" placeholder="Введите сообщение...">
                    <button onclick="sendMessage()">Отправить</button>
                </div>
                <div class="typing-indicator" id="typing-indicator">Бот печатает...</div>
            </div>
        </div>

    </div>

    <script>
        // Функция для обновления логов
        function refreshLogs() {
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    const logsContainer = document.getElementById('logs');
                    logsContainer.innerHTML = '';

                    data.logs.forEach(log => {
                        if (shouldDisplayLog(log)) {
                            const logElement = document.createElement('div');
                            logElement.className = `log-entry ${getLogLevelClass(log)}`;
                            logElement.textContent = log;
                            logsContainer.appendChild(logElement);
                        }
                    });

                    // Автоскролл вниз
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                })
                .catch(error => console.error('Ошибка при загрузке логов:', error));
        }

        // Функция для определения класса CSS на основе уровня лога
        function getLogLevelClass(logText) {
            if (logText.includes(' ERROR ') || logText.includes(' - ERROR - ')) return 'error';
            if (logText.includes(' WARNING ') || logText.includes(' - WARNING - ')) return 'warning';
            if (logText.includes(' INFO ') || logText.includes(' - INFO - ')) return 'info';
            if (logText.includes(' DEBUG ') || logText.includes(' - DEBUG - ')) return 'debug';
            if (logText.includes(' CRITICAL ') || logText.includes(' - CRITICAL - ')) return 'critical';
            return '';
        }

        // Функция для определения, нужно ли отображать лог на основе фильтров
        function shouldDisplayLog(logText) {
            const showError = document.getElementById('show-error').checked;
            const showWarning = document.getElementById('show-warning').checked;
            const showInfo = document.getElementById('show-info').checked;
            const showDebug = document.getElementById('show-debug').checked;
            const showCritical = document.getElementById('show-critical').checked;

            const logClass = getLogLevelClass(logText);

            if (logClass === 'error' && !showError) return false;
            if (logClass === 'warning' && !showWarning) return false;
            if (logClass === 'info' && !showInfo) return false;
            if (logClass === 'debug' && !showDebug) return false;
            if (logClass === 'critical' && !showCritical) return false;

            return true;
        }

        // Функция для сброса фильтров
        function clearFilters() {
            document.getElementById('show-error').checked = true;
            document.getElementById('show-warning').checked = true;
            document.getElementById('show-info').checked = true;
            document.getElementById('show-debug').checked = true;
            document.getElementById('show-critical').checked = true;
            refreshLogs();
        }

        // Функции для навигации между разделами
        function showLogs() {
            document.getElementById('logs-section').style.display = 'block';
            document.getElementById('main-section').style.display = 'none';
            document.getElementById('logs-btn').classList.add('active');
            document.getElementById('main-btn').classList.remove('active');
            refreshLogs(); // Обновляем логи при переходе на эту страницу
        }

        function showMainPage() {
            document.getElementById('logs-section').style.display = 'none';
            document.getElementById('main-section').style.display = 'block';
            document.getElementById('main-btn').classList.add('active');
            document.getElementById('logs-btn').classList.remove('active');
        }

        // Загружаем логи при загрузке страницы
        document.addEventListener('DOMContentLoaded', function() {
            refreshLogs();
            // Обновляем логи каждые 5 секунд, только если активна вкладка логов
            setInterval(function() {
                if (document.getElementById('logs-section').style.display !== 'none') {
                    refreshLogs();
                }
            }, 5000);
        });


        //Функции для чата (placeholder)
        function sendMessage() {
            const message = document.getElementById('chat-input').value;
            // Здесь должна быть логика отправки сообщения на сервер
            console.log("Отправлено сообщение:", message);
            document.getElementById('chat-input').value = '';
        }

    </script>
</body>
</html>
"""

# Функция для чтения логов с применением паттернов ошибок
def read_logs():
    logs = []

    # Проверяем наличие директории logs
    log_dir = "logs"
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.startswith('bot_log_') and f.endswith('.log')]
    else:
        # Если нет директории logs, ищем в корневой директории
        log_files = [f for f in os.listdir('.') if f.startswith('bot_log_') and f.endswith('.log')]

    # Если логов нет совсем, возвращаем сообщение
    if not log_files:
        return ["Лог-файлы не найдены. Запустите бота для создания логов."]

    # Паттерны распространенных ошибок с комментариями
    error_patterns = {
        r'ConnectionError': 'Ошибка подключения к внешнему API. Проверьте интернет-соединение.',
        r'Timeout': 'Превышено время ожидания ответа от внешнего API.',
        r'JSONDecodeError': 'Ошибка при разборе JSON ответа от API.',
        r'HTTPError': 'Ошибка HTTP при запросе к внешнему API.',
        r'API вернул ответ без содержимого': 'Ответ API не содержит ожидаемых данных, возможна блокировка запроса.',
        r'ApiError': 'Ошибка при взаимодействии с внешним API.',
        r'TelegramError': 'Ошибка при взаимодействии с Telegram API.',
        r'Отсутствует TELEGRAM_TOKEN': 'Не настроен токен Telegram бота в файле .env',
        r'Отсутствует GEMINI_API_KEY': 'Не настроен API ключ для Google Gemini в файле .env',
    }

    for log_file in sorted(log_files, reverse=True):
        try:
            log_path = os.path.join(log_dir, log_file) if os.path.exists(log_dir) else log_file
            with open(log_path, 'r', encoding='utf-8') as file:
                content = file.readlines()

                for line in content:
                    # Добавляем комментарии к известным ошибкам
                    for pattern, comment in error_patterns.items():
                        if re.search(pattern, line):
                            line = line.strip() + f" => {comment}\n"
                            break

                    logs.append(line.strip())
        except Exception as e:
            logs.append(f"Ошибка при чтении лог-файла {log_file}: {e}")

    # Ограничиваем количество логов для отображения (последние 1000)
    return logs[-1000:]

@app.route('/')
def index():
    try:
        app.logger.info('Запрос главной страницы')
        return HTML_TEMPLATE
    except Exception as e:
        app.logger.error(f'Ошибка при обработке запроса главной страницы: {e}')
        return str(e), 500

@app.route('/logs')
def logs():
    try:
        app.logger.info('Запрос страницы логов')
        # Используем тот же шаблон, JavaScript определит, что показывать
        return HTML_TEMPLATE
    except Exception as e:
        app.logger.error(f'Ошибка при обработке запроса страницы логов: {e}')
        return str(e), 500

@app.route('/api/logs')
def get_logs():
    try:
        app.logger.info('Запрос API логов')
        logs = read_logs()
        return jsonify({'logs': logs})
    except Exception as e:
        app.logger.error(f'Ошибка при получении логов через API: {e}')
        return jsonify({'error': str(e)}), 500

def run_flask():
    try:
        app.logger.info("Запуск Flask сервера на порту 8080")
        app.run(host='0.0.0.0', port=8080, debug=False)
    except Exception as e:
        app.logger.error(f"Ошибка при запуске Flask сервера: {e}")
        print(f"Ошибка при запуске Flask сервера: {e}")

# Функция для запуска Flask в отдельном потоке
def start_flask_server():
    try:
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True  # Поток будет завершен при завершении основной программы
        flask_thread.start()
        return flask_thread
    except Exception as e:
        app.logger.error(f"Не удалось запустить поток для Flask сервера: {e}")
        print(f"Не удалось запустить поток для Flask сервера: {e}")
        return None

if __name__ == '__main__':
    # Запуск Flask напрямую (для тестирования)
    app.run(host='0.0.0.0', port=8080, debug=True)