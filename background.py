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
flask_handler = RotatingFileHandler('flask_log.log', maxBytes=10485760, backupCount=3)
flask_handler.setFormatter(log_formatter)
app.logger.addHandler(flask_handler)
app.logger.setLevel(logging.INFO)

# Шаблон HTML для отображения логов
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Бот истории России</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Roboto', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            padding-bottom: 15px;
            text-align: center;
            margin-top: 10px;
            font-size: 28px;
        }
        h2 {
            color: #34495e;
            margin-top: 25px;
            font-size: 22px;
        }
        
        /* Стили для навигации */
        .navigation {
            display: flex;
            justify-content: center;
            margin: 10px 0 20px 0;
            padding: 12px 0;
            background-color: #f8f9fa;
            border-radius: 8px;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .nav-button {
            background-color: #ecf0f1;
            color: #444;
            border: 1px solid #ddd;
            padding: 12px 25px;
            margin: 0 15px;
            cursor: pointer;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .nav-button:hover {
            background-color: #d6e0f0;
            transform: translateY(-2px);
        }

        .nav-button.active {
            background-color: #3498db;
            color: white;
            border-color: #2980b9;
            box-shadow: 0 3px 6px rgba(0,0,0,0.1);
        }
        
        /* Стили для логов */
        .log-container {
            height: 600px;
            overflow-y: auto;
            background-color: #fafafa;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 25px;
            font-family: 'Consolas', monospace;
        }
        
        .log-entry {
            margin-bottom: 8px;
            padding: 8px;
            border-bottom: 1px solid #eee;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .error { color: #e74c3c; font-weight: bold; }
        .warning { color: #f39c12; }
        .info { color: #3498db; }
        .debug { color: #2ecc71; }
        .critical { 
            color: #c0392b; 
            background-color: #fadbd8; 
            font-weight: bold; 
            padding: 8px;
            border-radius: 4px;
        }

        .controls {
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
        }
        
        button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            border-radius: 6px;
            margin-right: 12px;
            font-size: 15px;
            transition: background-color 0.2s, transform 0.2s;
        }
        
        button:hover {
            background-color: #2980b9;
            transform: translateY(-2px);
        }
        
        .filter-group {
            margin: 12px 0;
            display: flex;
            flex-wrap: wrap;
        }
        
        .filter-group label {
            margin-right: 15px;
            display: flex;
            align-items: center;
            font-size: 15px;
            cursor: pointer;
        }
        
        .filter-group input[type="checkbox"] {
            margin-right: 5px;
            width: 16px;
            height: 16px;
        }

        /* Стили для главной страницы */
        #main-section {
            text-align: center;
            padding: 20px;
            line-height: 1.6;
        }

        #main-section p {
            margin-bottom: 15px;
            font-size: 17px;
        }

        /* Улучшенные стили для чата */
        .chat-container {
            max-width: 1000px;
            margin: 20px auto;
            border: 1px solid #ddd;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .chat-header {
            background-color: #3498db;
            color: white;
            padding: 18px;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
            letter-spacing: 0.5px;
        }

        .chat-messages {
            height: 500px;
            overflow-y: auto;
            padding: 20px;
            background-color: #f9f9f9;
        }

        .message {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
            max-width: 80%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            position: relative;
            line-height: 1.5;
        }

        .user-message {
            background-color: #d5f5e3;
            margin-left: auto;
            border-top-right-radius: 2px;
            color: #1e8449;
        }
        
        .user-message:before {
            content: '';
            position: absolute;
            top: 0;
            right: -10px;
            width: 0;
            height: 0;
            border-left: 10px solid #d5f5e3;
            border-top: 10px solid transparent;
            border-bottom: 10px solid transparent;
        }

        .bot-message {
            background-color: #eaf2f8;
            margin-right: auto;
            border-top-left-radius: 2px;
            color: #2c3e50;
        }
        
        .bot-message:before {
            content: '';
            position: absolute;
            top: 0;
            left: -10px;
            width: 0;
            height: 0;
            border-right: 10px solid #eaf2f8;
            border-top: 10px solid transparent;
            border-bottom: 10px solid transparent;
        }
        
        /* Стили для структурированного ответа бота */
        .bot-message h3 {
            margin-top: 0;
            margin-bottom: 10px;
            color: #2471a3;
            font-size: 18px;
            border-bottom: 1px solid #aed6f1;
            padding-bottom: 8px;
        }
        
        .bot-message .chapter {
            margin-bottom: 15px;
            padding: 10px;
            background-color: #f4f9fc;
            border-radius: 8px;
            border-left: 3px solid #3498db;
        }
        
        .bot-message .chapter-title {
            font-weight: bold;
            color: #2980b9;
            margin-bottom: 5px;
            font-size: 16px;
        }

        .chat-input {
            display: flex;
            padding: 15px;
            background-color: #f0f0f0;
            border-top: 1px solid #ddd;
        }

        .chat-input input {
            flex-grow: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 25px;
            margin-right: 10px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .chat-input input:focus {
            border-color: #3498db;
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }

        .chat-input button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }

        .chat-input button:hover {
            background-color: #2980b9;
            transform: scale(1.05);
        }

        .typing-indicator {
            padding: 12px;
            color: #7f8c8d;
            font-style: italic;
            display: none;
            text-align: center;
            background-color: #f5f5f5;
            border-radius: 15px;
            margin: 10px auto;
            max-width: 150px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Бот истории России</h1>

        <div class="navigation">
            <button onclick="showChat()" class="nav-button active" id="chat-btn">Чат с ботом</button>
            <button onclick="showLogs()" class="nav-button" id="logs-btn">Просмотр логов</button>
        </div>
        
        <div id="chat-section">
            <h2>Изучайте историю России в диалоге с ботом</h2>
            <p>Задайте вопрос по истории России, и бот даст вам подробный ответ. Вы можете спрашивать о событиях, исторических личностях, эпохах и многом другом.</p>
            
            <div class="chat-container">
                <div class="chat-header">Диалог с ботом истории России</div>
                <div class="chat-messages" id="chat-messages"></div>
                <div class="typing-indicator" id="typing-indicator">Бот печатает...</div>
                <div class="chat-input">
                    <input type="text" id="chat-input" placeholder="Введите ваш вопрос по истории России...">
                    <button onclick="sendMessage()">Отправить</button>
                </div>
            </div>
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
        function showChat() {
            document.getElementById('chat-section').style.display = 'block';
            document.getElementById('logs-section').style.display = 'none';
            document.getElementById('chat-btn').classList.add('active');
            document.getElementById('logs-btn').classList.remove('active');
        }
        
        function showLogs() {
            document.getElementById('logs-section').style.display = 'block';
            document.getElementById('chat-section').style.display = 'none';
            document.getElementById('logs-btn').classList.add('active');
            document.getElementById('chat-btn').classList.remove('active');
            refreshLogs(); // Обновляем логи при переходе на эту страницу
        }

        // Загружаем данные при загрузке страницы
        document.addEventListener('DOMContentLoaded', function() {
            // По умолчанию показываем чат
            showChat();
            
            // Обновляем логи каждые 5 секунд, только если активна вкладка логов
            setInterval(function() {
                if (document.getElementById('logs-section').style.display !== 'none') {
                    refreshLogs();
                }
            }, 5000);
            
            // Обработка нажатия Enter в поле ввода
            const inputField = document.getElementById('chat-input');
            inputField.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessage();
                }
            });
            
            // Фокус на поле ввода при загрузке
            inputField.focus();
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
                
                // Обрабатываем и показываем ответ бота
                formatAndAddBotMessage(data.response);
                
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
        
        // Функция для добавления сообщения пользователя в чат
        function addMessage(text, className) {
            const chatMessages = document.getElementById('chat-messages');
            const messageElement = document.createElement('div');
            messageElement.className = `message ${className}`;
            messageElement.textContent = text;
            chatMessages.appendChild(messageElement);
            
            // Прокручиваем чат вниз
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Функция для форматирования и добавления ответа бота в чат
        function formatAndAddBotMessage(text) {
            const chatMessages = document.getElementById('chat-messages');
            const messageElement = document.createElement('div');
            messageElement.className = 'message bot-message';
            
            // Проверяем, содержит ли текст заголовки глав истории России
            const chapterTitles = [
                "📜 ВВЕДЕНИЕ И ИСТОКИ",
                "⚔️ ОСНОВНЫЕ СОБЫТИЯ И РАЗВИТИЕ",
                "🏛️ КЛЮЧЕВЫЕ ФИГУРЫ И РЕФОРМЫ",
                "🌍 ВНЕШНЯЯ ПОЛИТИКА И ВЛИЯНИЕ",
                "📊 ИТОГИ И ИСТОРИЧЕСКОЕ ЗНАЧЕНИЕ"
            ];
            
            let containsChapters = false;
            for (const title of chapterTitles) {
                if (text.includes(title)) {
                    containsChapters = true;
                    break;
                }
            }
            
            if (containsChapters) {
                // Создаем заголовок для ответа
                const topicMatch = text.match(/\*(.+?)\*/);
                let topicTitle = "История России";
                if (topicMatch && topicMatch[1]) {
                    topicTitle = topicMatch[1].replace(/^\*+|\*+$/g, '');
                }
                
                const header = document.createElement('h3');
                header.textContent = topicTitle;
                messageElement.appendChild(header);
                
                // Разделяем текст на главы
                const chapters = text.split('\n\n');
                
                chapters.forEach(chapter => {
                    // Пропускаем пустые строки
                    if (chapter.trim() === '') return;
                    
                    const chapterDiv = document.createElement('div');
                    chapterDiv.className = 'chapter';
                    
                    // Проверяем, содержит ли глава заголовок
                    const titleMatch = chapter.match(/\*(📜|⚔️|🏛️|🌍|📊)[^*]+\*/);
                    
                    if (titleMatch) {
                        const titleText = titleMatch[0].replace(/^\*+|\*+$/g, '');
                        const titleElement = document.createElement('div');
                        titleElement.className = 'chapter-title';
                        titleElement.textContent = titleText;
                        chapterDiv.appendChild(titleElement);
                        
                        // Контент главы (без заголовка)
                        const contentText = chapter.replace(titleMatch[0], '').trim();
                        if (contentText) {
                            const contentElement = document.createElement('div');
                            contentElement.textContent = contentText;
                            chapterDiv.appendChild(contentElement);
                        }
                    } else {
                        // Если нет заголовка, просто добавляем текст
                        chapterDiv.textContent = chapter;
                    }
                    
                    messageElement.appendChild(chapterDiv);
                });
                
            } else {
                // Если нет структуры глав, просто добавляем текст как есть
                messageElement.textContent = text;
            }
            
            chatMessages.appendChild(messageElement);
            
            // Прокручиваем чат вниз
            chatMessages.scrollTop = chatMessages.scrollHeight;
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
        app.logger.info('Запрос главной страницы (чат)')
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

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        app.logger.info('Получен запрос чата')
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
            
        # Импортируем функцию для генерации ответа
        from main import ask_grok
        
        # Формируем промпт для бота истории
        prompt = f"Ответь на вопрос пользователя по истории России: {user_message}\n\nОтвет должен быть полезным, информативным и основан на исторических фактах. Если вопрос не связан с историей России, вежливо попроси задать вопрос по теме истории России."
        
        app.logger.info(f'Обработка сообщения пользователя: {user_message}')
        bot_response = ask_grok(prompt, max_tokens=1024)
        app.logger.info('Ответ сгенерирован')
        
        return jsonify({'response': bot_response})
    except Exception as e:
        app.logger.error(f'Ошибка при обработке запроса чата: {e}')
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