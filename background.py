import os
import re
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import threading
import logging
from logging.handlers import RotatingFileHandler

# Инициализация Flask-приложения
app = Flask(__name__)

# Настройка логирования для Flask
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Очищаем лог Flask при инициализации
flask_log_path = 'flask_log.log'
try:
    # Если файл существует, открываем для записи (что очищает содержимое)
    if os.path.exists(flask_log_path):
        with open(flask_log_path, 'w') as f:
            f.write("")
    print(f"Лог Flask очищен при инициализации веб-сервера: {flask_log_path}")
except Exception as e:
    print(f"Ошибка при очистке лога Flask: {e}")

flask_handler = RotatingFileHandler(flask_log_path, maxBytes=10485760, backupCount=3)
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
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
            max-width: 90%;
            width: 100%;
            min-width: auto;
            margin: 20px auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }

        @media (max-width: 768px) {
            .chat-container {
                max-width: 95%;
                margin: 10px auto;
            }

            .chat-messages {
                height: 400px;
            }

            .chat-input input {
                padding: 8px 12px;
            }

            .chat-input button {
                padding: 8px 15px;
            }
        }

        @media (max-width: 480px) {
            .chat-container {
                max-width: 100%;
                margin: 5px auto;
            }

            .chat-header {
                padding: 12px;
                font-size: 16px;
            }

            .chat-messages {
                height: 350px;
                padding: 10px;
            }

            .message {
                max-width: 90%;
                padding: 8px 12px;
            }
        }

        .chat-header {
            background-color: #337ab7;
            color: white;
            padding: 18px;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
        }

        .chat-messages {
            height: 500px;
            overflow-y: auto;
            padding: 20px;
            background-color: #f9f9f9;
        }

        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 80%;
            line-height: 1.4;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        .user-message {
            background-color: #DCF8C6;
            margin-left: auto;
            text-align: right;
            border-top-right-radius: 4px;
        }

        .bot-message {
            background-color: #E9EAEC;
            margin-right: auto;
            border-top-left-radius: 4px;
        }

        .chat-input {
            display: flex;
            flex-direction: column;
            padding: 15px;
            background-color: #f0f0f0;
            border-top: 1px solid #ddd;
        }

        .chat-button-container {
            display: flex;
            justify-content: center;
            margin-top: 10px;
        }

        .chat-input input {
            flex-grow: 1;
            padding: 12px 15px;
            border: 1px solid #ccc;
            border-radius: 20px;
            margin-right: 12px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }

        .chat-input input:focus {
            border-color: #337ab7;
            box-shadow: 0 0 5px rgba(51, 122, 183, 0.3);
        }

        .chat-input button {
            background-color: #337ab7;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 20px;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.3s;
            width: 50%;
            max-width: 200px;
        }

        .chat-input button:hover {
            background-color: #2e6da4;
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
            <button onclick="showLogs()" class="nav-button" id="logs-btn">Просмотр логов</button>
            <button onclick="showMainPage()" class="nav-button active" id="main-btn">Главная страница</button>
            <a href="/download/presentation" class="nav-button" style="text-decoration: none;">
                📄 Презентация
            </a>
        </div>

        <div id="logs-section" style="display: none;">
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

        <div id="main-section">
            <h2>Главная страница</h2>
            <p>Добро пожаловать в панель управления ботом истории России!</p>
            <p>Этот веб-интерфейс позволяет просматривать логи работы бота и отслеживать его активность.</p>
            <p>Для просмотра логов нажмите кнопку "Просмотр логов" вверху страницы.</p>
            <div style="text-align: center; margin: 20px 0;">
                <a href="/download/presentation" 
                   style="background-color: #337ab7; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    📄 Скачать презентацию бота
                </a>
            </div>
            <p>Чтобы связаться с ботом, используйте чат ниже:</p>
            <div class="chat-container">
                <div class="chat-header">Чат с ботом</div>
                <div class="chat-messages" id="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" id="chat-input" placeholder="Введите сообщение...">
                    <div class="chat-button-container">
                        <button onclick="sendMessage()">Отправить</button>
                    </div>
                </div>
                <div class="typing-indicator" id="typing-indicator">Бот печатает...</div>
            </div>
        </div>

    </div>
    <footer style="text-align: center; margin-top: 20px; font-size: 14px;">
        © 2025 Silver Raven. Образовательный бот по истории России. Все права защищены.<br>
        <span style="font-size: 12px; color: #666;">Версия 1.2.0 • Используется Google Gemini API</span>
    </footer>
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


        // Функции для чата
        function sendMessage() {
            const messageInput = document.getElementById('chat-input');
            const message = messageInput.value.trim();

            if (!message) return; // Не отправляем пустые сообщения

            // Показываем сообщение пользователя
            addMessage(message, 'user-message');

            // Очищаем поле ввода
            messageInput.value = '';

            // Показываем индикатор "бот печатает"
            document.getElementById('typing-indicator').style.display = 'block';

            // Отправляем запрос на сервер
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Ошибка запроса');
                }
                return response.json();
            })
            .then(data => {
                // Скрываем индикатор "бот печатает"
                document.getElementById('typing-indicator').style.display = 'none';

                // Показываем ответ бота
                addMessage(data.response, 'bot-message');

                // Прокручиваем чат вниз
                const chatMessages = document.getElementById('chat-messages');
                chatMessages.scrollTop = chatMessages.scrollHeight;
            })
            .catch(error => {
                console.error('Ошибка:', error);
                // Скрываем индикатор "бот печатает"
                document.getElementById('typing-indicator').style.display = 'none';

                // Показываем сообщение об ошибке
                addMessage('Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.', 'bot-message');
            });
        }

        // Функция для добавления сообщения в чат
        function addMessage(text, className) {
            const chatMessages = document.getElementById('chat-messages');
            const messageElement = document.createElement('div');
            messageElement.className = `message ${className}`;
            messageElement.textContent = text;
            chatMessages.appendChild(messageElement);

            // Прокручиваем чат вниз
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // Обработка нажатия Enter в поле ввода
        document.addEventListener('DOMContentLoaded', function() {
            const inputField = document.getElementById('chat-input');
            if (inputField) {
                inputField.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        sendMessage();
                    }
                });
            }
        });
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

@app.route('/download/presentation')
def download_presentation():
    """
    Маршрут для скачивания презентации бота через веб-интерфейс.
    """
    try:
        app.logger.info('Запрос на скачивание презентации')

        # Проверяем наличие директории static
        if not os.path.exists('static'):
            os.makedirs('static')
            app.logger.info('Создана директория static')

        # Путь к файлу презентации
        presentation_path = 'static/presentation.txt'

        # Если файла нет, создаем его
        if not os.path.exists(presentation_path):
            app.logger.info('Файл презентации не найден, создаем новый')
            try:
                with open('presentation.md', 'r', encoding='utf-8') as md_file:
                    md_content = md_file.read()

                    # Упрощаем форматирование для txt версии
                    txt_content = md_content.replace('## ', '').replace('### ', '').replace('- ', '   - ')

                    with open(presentation_path, 'w', encoding='utf-8') as txt_file:
                        txt_file.write(txt_content)

                app.logger.info('Презентация успешно создана')
            except Exception as e:
                app.logger.error(f'Ошибка при создании презентации: {e}')
                return f'Ошибка при создании презентации: {e}', 500

        # Отправляем файл для скачивания
        from flask import send_file
        return send_file(
            presentation_path, 
            as_attachment=True, 
            download_name='Презентация_бота_истории_России.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        app.logger.error(f'Ошибка при обработке запроса на скачивание презентации: {e}')
        return f'Ошибка при скачивании презентации: {e}', 500

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

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Обрабатывает API запросы для чата с ботом.

    Принимает сообщение пользователя, проверяет его на соответствие теме истории России,
    генерирует соответствующий ответ и возвращает его в формате JSON.

    Returns:
        JSON-ответ с текстом ответа бота или сообщением об ошибке
    """
    try:
        app.logger.info('Получен запрос чата')
        data = request.json
        user_message = data.get('message', '')

        # Валидация входных данных
        if not user_message:
            app.logger.warning('Получен пустой запрос чата')
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400

        # Импортируем функцию для генерации ответа
        from main import ask_grok

        # Сначала проверяем, относится ли сообщение к истории России
        # Используем короткий запрос для эффективности
        check_prompt = f"Проверь, относится ли следующее сообщение к истории России: \"{user_message}\". Ответь только 'да' или 'нет'."
        is_history_related = ask_grok(check_prompt, max_tokens=50, temp=0.1).lower().strip()

        app.logger.info(f'Проверка темы сообщения: {is_history_related}')

        # Формируем разные промпты в зависимости от темы сообщения
        if 'да' in is_history_related:
            # Если сообщение относится к истории России - отвечаем по существу
            prompt = (
                f"Пользователь задал вопрос на тему истории России: \"{user_message}\"\n\n"
                "Ответь на этот вопрос, опираясь на исторические факты. "
                "Будь информативным, но кратким. Акцентируй внимание на наиболее важных "
                "аспектах и датах, относящихся к вопросу."
            )
        else:
            # Если сообщение не относится к истории России - вежливо отказываем
            prompt = (
                f"Пользователь задал вопрос не относящийся к истории России: \"{user_message}\"\n\n"
                "Вежливо объясни, что ты специализируешься только на истории России, и "
                "предложи задать вопрос, связанный с историей России. "
                "Приведи пример возможного вопроса, который мог бы быть интересен пользователю."
            )

        app.logger.info(f'Обработка сообщения пользователя: {user_message[:50]}...' if len(user_message) > 50 else f'Обработка сообщения пользователя: {user_message}')

        # Генерируем ответ
        bot_response = ask_grok(prompt, max_tokens=1024)

        # Если сообщение не относится к истории России, добавляем предупреждение
        if 'да' not in is_history_related:
            bot_response = "⚠️ Я могу общаться только на темы, связанные с историей России. ⚠️\n\n" + bot_response

        app.logger.info('Ответ сгенерирован успешно')

        return jsonify({'response': bot_response})
    except Exception as e:
        app.logger.error(f'Ошибка при обработке запроса чата: {e}')
        return jsonify({
            'error': str(e),
            'response': "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или обратитесь к администратору."
        }), 500

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