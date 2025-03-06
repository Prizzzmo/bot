
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Логи бота истории России</h1>
        
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
        
        // Загружаем логи при загрузке страницы
        document.addEventListener('DOMContentLoaded', function() {
            refreshLogs();
            // Обновляем логи каждые 5 секунд
            setInterval(refreshLogs, 5000);
        });
    </script>
</body>
</html>
"""

# Функция для чтения логов с применением паттернов ошибок
def read_logs():
    log_files = [f for f in os.listdir('.') if f.startswith('bot_log_') and f.endswith('.log')]
    logs = []
    
    # Паттерны распространенных ошибок с комментариями
    error_patterns = {
        r'ConnectionError': 'Ошибка подключения к внешнему API. Проверьте интернет-соединение.',
        r'Timeout': 'Превышено время ожидания ответа от внешнего API.',
        r'JSONDecodeError': 'Ошибка при разборе JSON ответа от API.',
        r'HTTPError': 'Ошибка HTTP при запросе к внешнему API.',
        r'API вернул ответ без содержимого': 'Ответ API не содержит ожидаемых данных, возможна блокировка запроса.',
        r'ApiError': 'Ошибка при взаимодействии с внешним API.',
        r'TelegramError': 'Ошибка при взаимодействии с Telegram API.',
    }
    
    for log_file in sorted(log_files, reverse=True):
        try:
            with open(log_file, 'r', encoding='utf-8') as file:
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
        app.logger.info('Запрос главной страницы логов')
        return HTML_TEMPLATE
    except Exception as e:
        app.logger.error(f'Ошибка при обработке запроса главной страницы: {e}')
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
    app.run(host='0.0.0.0', port=8080, debug=False)

# Функция для запуска Flask в отдельном потоке
def start_flask_server():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # Поток будет завершен при завершении основной программы
    flask_thread.start()
    return flask_thread

if __name__ == '__main__':
    # Запуск Flask напрямую (для тестирования)
    app.run(host='0.0.0.0', port=8080, debug=True)
