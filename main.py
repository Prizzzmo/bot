
import os
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
import requests
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading
import re
import json
import background  # Импортируем модуль Flask-сервера

# Константы для состояний ConversationHandler
TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION = range(5)

# Словарь с описаниями ошибок для расширенного логирования
ERROR_DESCRIPTIONS = {
    'ConnectionError': 'Ошибка подключения к внешнему API. Проверьте интернет-соединение.',
    'Timeout': 'Превышено время ожидания ответа от внешнего API.',
    'JSONDecodeError': 'Ошибка при разборе JSON ответа от API.',
    'HTTPError': 'Ошибка HTTP при запросе к внешнему API.',
    'TelegramError': 'Ошибка при взаимодействии с Telegram API.',
    'KeyboardInterrupt': 'Бот был остановлен вручную.',
    'ApiError': 'Ошибка при взаимодействии с внешним API.',
}

# Функция для очистки логов
def clean_logs():
    """
    Очищает лог-файлы при запуске бота.
    Удаляет содержимое текущего лог-файла и flask_log.log.
    
    Returns:
        tuple: Кортеж (директория логов, путь к файлу лога)
    """
    try:
        # Проверяем наличие директории для логов
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"Создана директория для логов: {log_dir}")
            
        # Очищаем лог Flask, если он существует
        flask_log_path = "flask_log.log"
        if os.path.exists(flask_log_path):
            with open(flask_log_path, 'w') as f:
                f.write("")
            print(f"Лог Flask очищен: {flask_log_path}")
            
        # Дата для имени файла лога
        log_date = datetime.now().strftime('%Y%m%d')
        log_file_path = f"{log_dir}/bot_log_{log_date}.log"
        
        # Очищаем текущий лог бота, если он существует
        if os.path.exists(log_file_path):
            with open(log_file_path, 'w') as f:
                f.write("")
            print(f"Лог бота очищен: {log_file_path}")
            
        # Очищаем временные логи в корневой директории, если они есть
        root_log_path = f"bot_log_{log_date}.log"
        if os.path.exists(root_log_path):
            with open(root_log_path, 'w') as f:
                f.write("")
            print(f"Временный лог очищен: {root_log_path}")
            
        print("Все логи успешно очищены")
        return log_dir, log_file_path
    except Exception as e:
        print(f"Ошибка при очистке логов: {e}")
        # Возвращаем стандартные пути в случае ошибки
        return "logs", f"logs/bot_log_{datetime.now().strftime('%Y%m%d')}.log"

# Настройка логирования
def setup_logging():
    """
    Настраивает систему логирования для бота.
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Очищаем логи и получаем пути
    log_dir, log_file_path = clean_logs()

    # Расширенная настройка логирования
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Используем RotatingFileHandler для ограничения размера файлов логов
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10485760,  # 10 МБ
        backupCount=5
    )
    file_handler.setFormatter(log_formatter)

    # Консольный вывод
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    # Настройка корневого логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Удаляем существующие обработчики, чтобы избежать дублирования
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    print(f"Логирование настроено. Файлы логов будут сохраняться в: {log_file_path}")
    return logger

# Инициализируем логгер
logger = setup_logging()

# Расширенная функция логирования ошибок с комментариями
def log_error(error, additional_info=None):
    """
    Логирует ошибку с дополнительной информацией и комментариями.
    
    Args:
        error (Exception): Объект ошибки
        additional_info (str, optional): Дополнительная информация
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Добавляем комментарий к известным типам ошибок
    if error_type in ERROR_DESCRIPTIONS:
        comment = ERROR_DESCRIPTIONS[error_type]
        logger.error(f"{error_type}: {error_message} => {comment}")
    else:
        logger.error(f"{error_type}: {error_message}")

    if additional_info:
        logger.error(f"Дополнительная информация: {additional_info}")

# Загружаем переменные окружения из файла .env
load_dotenv()

# Класс для кэширования ответов API
class APICache:
    """
    Простой класс для кэширования ответов API.
    Поддерживает сохранение и загрузку кэша из файла.
    """
    def __init__(self, max_size=100, cache_file='api_cache.json'):
        self.cache = {}
        self.max_size = max_size
        self.cache_file = cache_file
        self.load_cache()
        
    def get(self, key):
        """Получить значение из кэша по ключу"""
        return self.cache.get(key)

    def set(self, key, value):
        """Добавить значение в кэш"""
        # Если кэш переполнен, удаляем наименее востребованные элементы
        if len(self.cache) >= self.max_size:
            # Сортируем по времени последнего доступа
            items = sorted(self.cache.items(), key=lambda x: x[1].get('last_accessed', 0))
            # Удаляем 10% старых элементов
            for i in range(int(self.max_size * 0.1)):
                if items:
                    del self.cache[items[i][0]]
        
        # Добавляем новый элемент с временной меткой
        self.cache[key] = {
            'value': value,
            'last_accessed': datetime.now().timestamp()
        }
        # Периодически сохраняем кэш
        if len(self.cache) % 10 == 0:
            self.save_cache()

    def load_cache(self):
        """Загружает кэш из файла, если он существует"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    loaded_cache = json.load(f)
                    self.cache = {k: {'value': v['value'], 'last_accessed': v['last_accessed']} 
                                 for k, v in loaded_cache.items()}
                    logger.info(f"Кэш загружен из {self.cache_file}, {len(self.cache)} записей")
        except Exception as e:
            logger.error(f"Ошибка при загрузке кэша: {e}")
            self.cache = {}

    def save_cache(self):
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Кэш сохранен в {self.cache_file}, {len(self.cache)} записей")
        except Exception as e:
            logger.error(f"Ошибка при сохранении кэша: {e}")

    def clear(self):
        """Очистить кэш"""
        self.cache.clear()
        self.save_cache()

# Создаем глобальный экземпляр кэша
api_cache = APICache()

# Получаем ключи API из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Используем Google Gemini API

# Функция для запросов к Google Gemini API
def ask_grok(prompt, max_tokens=1024, temp=0.7, use_cache=True):
    """
    Отправляет запрос к Google Gemini API и возвращает ответ.

    Args:
        prompt (str): Текст запроса
        max_tokens (int): Максимальное количество токенов в ответе
        temp (float): Температура генерации (0.0-1.0)
        use_cache (bool): Использовать ли кэширование

    Returns:
        str: Ответ от API или сообщение об ошибке
    """
    # Создаем уникальный ключ для кэша на основе параметров запроса
    cache_key = f"{prompt}_{max_tokens}_{temp}"

    # Проверяем кэш, если использование кэша включено
    if use_cache:
        cached_response = api_cache.get(cache_key)
        if cached_response:
            logger.info("Использую кэшированный ответ")
            return cached_response['value']

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temp,
            "maxOutputTokens": max_tokens
        }
    }

    try:
        logger.info(f"Отправка запроса к Gemini API: {prompt[:50]}...")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        response_json = response.json()

        # Проверка наличия всех необходимых ключей в ответе
        if "candidates" not in response_json or not response_json["candidates"]:
            logger.warning(f"Ответ не содержит 'candidates': {response_json}")
            return "API вернул ответ без содержимого. Возможно, запрос был заблокирован фильтрами безопасности."

        candidate = response_json["candidates"][0]
        if "content" not in candidate:
            logger.warning(f"Ответ не содержит 'content': {candidate}")
            return "API вернул неверный формат ответа."

        content = candidate["content"]
        if "parts" not in content or not content["parts"]:
            logger.warning(f"Ответ не содержит 'parts': {content}")
            return "API вернул пустой ответ."

        result = content["parts"][0]["text"]
        logger.info(f"Получен ответ от API: {result[:50]}...")

        # Сохраняем результат в кэш
        if use_cache:
            api_cache.set(cache_key, result)

        return result

    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"{error_type}: {error_msg}")

        if isinstance(e, requests.exceptions.HTTPError) and hasattr(e, 'response'):
            logger.error(f"Статус код: {e.response.status_code}")
            logger.error(f"Ответ сервера: {e.response.text}")
            return f"Ошибка HTTP при запросе к Google Gemini ({e.response.status_code}): {error_msg}"

        error_messages = {
            "ConnectionError": "Ошибка соединения с API Google Gemini. Проверьте подключение к интернету.",
            "Timeout": "Превышено время ожидания ответа от API Google Gemini.",
            "JSONDecodeError": "Ошибка при обработке ответа от API Google Gemini.",
            "HTTPError": f"Ошибка HTTP при запросе к Google Gemini: {error_msg}"
        }

        return error_messages.get(error_type, f"Неизвестная ошибка при запросе к Google Gemini: {error_msg}")

# Функция для создания главного меню
def main_menu():
    """
    Создает главное меню в виде кнопок.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками меню
    """
    keyboard = [
        [InlineKeyboardButton("🔍 Выбрать тему", callback_data='topic')],
        [InlineKeyboardButton("✅ Пройти тест", callback_data='test')],
        [InlineKeyboardButton("💬 Беседа о истории России", callback_data='conversation')],
        [InlineKeyboardButton("📄 Скачать презентацию", callback_data='download_presentation')],
        [InlineKeyboardButton("❌ Завершить", callback_data='cancel')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команда /start (начало работы с ботом)
def start(update, context):
    """
    Обрабатывает команду /start, показывает приветствие и главное меню.
    Также предлагает скачать презентацию бота.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
        
    Returns:
        int: Следующее состояние разговора
    """
    user = update.message.from_user
    logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")
    
    # Создаем директорию static, если её нет
    if not os.path.exists('static'):
        os.makedirs('static')
        logger.info("Создана директория для статических файлов")
    
    # Очищаем историю чата
    clear_chat_history(update, context)
    
    # Отправляем приветственное сообщение и сохраняем его ID
    sent_message = update.message.reply_text(
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "🤖 Я образовательный бот по истории России. С моей помощью вы сможете:\n\n"
        "📚 *Изучать различные исторические темы* — от древних времен до современности\n"
        "✅ *Проходить тесты* для проверки полученных знаний\n"
        "🔍 *Выбирать интересующие темы* из предложенного списка\n"
        "📝 *Предлагать свои темы* для изучения, если не нашли в списке\n\n"
        "Каждая тема подробно раскрывается в 5 главах с информацией об истоках, ключевых событиях, "
        "исторических личностях, международных отношениях и историческом значении.\n\n"
        "❗ *Данный бот создан в качестве учебного пособия.*\n\n"
        "📋 Вам отправлена подробная презентация бота, содержащая информацию о функциональности, "
        "принципах работы с ИИ Gemini и мерах безопасности.\n\n"
        "© 2025 Silver Raven. Образовательный бот по истории России.",
        parse_mode='Markdown'
    )
    # Сохраняем ID сообщения
    save_message_id(update, context, sent_message.message_id)
    
    # Отправляем файл презентации
    try:
        # Проверяем наличие файла презентации
        presentation_path = 'static/presentation.txt'
        
        if not os.path.exists(presentation_path):
            logger.warning(f"Файл презентации {presentation_path} не найден")
            # Если файла нет, создаем его
            with open(presentation_path, 'w', encoding='utf-8') as f:
                with open('presentation.md', 'r', encoding='utf-8') as md_file:
                    # Упрощаем форматирование для txt версии
                    md_content = md_file.read()
                    txt_content = md_content.replace('## ', '').replace('### ', '').replace('- ', '   - ')
                    f.write(txt_content)
            logger.info(f"Файл презентации {presentation_path} создан")
        
        # Отправляем презентацию пользователю
        with open(presentation_path, 'rb') as document:
            update.message.reply_document(
                document=document, 
                filename="Презентация_бота_истории_России.txt",
                caption="📝 *Презентация бота*\nЗдесь вы можете ознакомиться с подробным описанием функций и возможностей бота.",
                parse_mode='Markdown'
            )
        logger.info(f"Презентация отправлена пользователю {user.id}")
    except Exception as e:
        log_error(e, f"Ошибка при отправке презентации пользователю {user.id}")
        update.message.reply_text("К сожалению, не удалось отправить презентацию. Пожалуйста, попробуйте позже.")
    
    # Отправляем основное меню
    sent_msg = update.message.reply_text(
        "Выберите действие в меню ниже, чтобы начать:",
        reply_markup=main_menu()
    )
    save_message_id(update, context, sent_msg.message_id)
    return TOPIC

# Функция для парсинга тем из текста ответа API
def parse_topics(topics_text):
    """
    Парсит текст с темами и возвращает отформатированный список тем.

    Args:
        topics_text (str): Текст с темами от API

    Returns:
        list: Список отформатированных тем
    """
    filtered_topics = []
    
    # Усовершенствованное регулярное выражение для более точного извлечения тем
    # Паттерн ищет строки, которые начинаются с цифры, маркера списка или содержат разделители
    pattern = r'(?:^\d+[.):]\s*|^[*•\-–—]\s*|^[а-яА-ЯA-Za-z]+[:.]\s*)(.+?)$'
    
    # Предварительная очистка текста
    lines = [line.strip() for line in topics_text.split('\n') if line.strip()]
    
    for line in lines:
        if len(line) <= 1:
            continue
            
        # Пытаемся извлечь тему с помощью регулярного выражения
        match = re.search(pattern, line, re.MULTILINE)
        if match:
            topic_text = match.group(1).strip()
            if topic_text and len(topic_text) > 3:  # Проверка минимальной длины
                # Удаляем кавычки в начале и конце, если они есть
                topic_text = topic_text.strip('"\'«»')
                filtered_topics.append(topic_text)
        # Если регулярное выражение не сработало, используем улучшенные эвристические методы
        elif any(sep in line for sep in ['. ', ': ', ' - ', ' – ']):
            # Ищем первый подходящий разделитель
            for sep in ['. ', ': ', ' - ', ' – ']:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) > 1 and parts[0].strip().isdigit():
                        topic_text = parts[1].strip()
                        if topic_text and len(topic_text) > 3:
                            topic_text = topic_text.strip('"\'«»')
                            filtered_topics.append(topic_text)
                            break
        elif line[0].isdigit():
            # Улучшенный алгоритм поиска начала темы после цифр
            i = 0
            # Пропускаем цифры и разделители в начале
            while i < len(line) and (line[i].isdigit() or line[i] in ' \t.):,-–—'):
                i += 1
            if i < len(line):
                topic_text = line[i:].strip()
                if topic_text and len(topic_text) > 3:
                    topic_text = topic_text.strip('"\'«»')
                    filtered_topics.append(topic_text)
        # Добавляем строки, которые выглядят как темы (не содержат запрещенных символов)
        elif (not any(char in line for char in ['?', '!', '=', '@', '#', '%', '&', '*', '(', ')', '[', ']', '{', '}']) 
              and len(line) > 5 and len(line) < 100):
            topic_text = line.strip('"\'«»')
            filtered_topics.append(topic_text)

    # Очистка тем от общих проблем
    cleaned_topics = []
    for topic in filtered_topics:
        # Удаление множественных пробелов
        topic = re.sub(r'\s+', ' ', topic)
        
        # Проверка на окончание предложения и обрезка, если это необходимо
        if '.' in topic[:-1]:  # Точка не в конце строки
            topic = topic.split('.')[0] + '.'
            
        # Обрезка слишком длинных тем
        if len(topic) > 70:
            words = topic.split()
            shortened = ' '.join(words[:8])  # Берем первые 8 слов
            if not shortened.endswith('.'):
                shortened += '...'
            topic = shortened
            
        # Удаление вводных слов в начале темы
        starters = ['тема:', 'topic:', 'вопрос:', 'период:', 'эпоха:']
        for starter in starters:
            if topic.lower().startswith(starter):
                topic = topic[len(starter):].strip()
        
        # Убедимся, что первая буква заглавная
        if topic and topic[0].isalpha():
            topic = topic[0].upper() + topic[1:]
            
        cleaned_topics.append(topic)

    # Удаляем дубликаты и похожие темы, сохраняя порядок
    unique_topics = []
    for topic in cleaned_topics:
        # Проверка на похожие темы (если одна тема полностью содержится в другой)
        is_duplicate = False
        for existing in unique_topics:
            # Игнорируем регистр при сравнении
            if topic.lower() in existing.lower() or existing.lower() in topic.lower():
                # Выбираем более короткую тему, если она не слишком короткая
                if len(topic) < len(existing) and len(topic) > 10:
                    unique_topics.remove(existing)
                    unique_topics.append(topic)
                is_duplicate = True
                break
                
        if not is_duplicate and topic not in unique_topics:
            unique_topics.append(topic)

    # Ограничиваем до 30 тем
    return unique_topics[:30]

# Функция для создания клавиатуры с темами
def create_topics_keyboard(topics):
    """
    Создает клавиатуру с кнопками для выбора темы.

    Args:
        topics (list): Список тем

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками
    """
    keyboard = []

    for i, topic in enumerate(topics, 1):
        # Проверяем, что тема не пустая
        if topic and len(topic.strip()) > 0:
            # Ограничиваем длину темы в кнопке
            display_topic = topic[:30] + '...' if len(topic) > 30 else topic
            keyboard.append([InlineKeyboardButton(f"{i}. {display_topic}", callback_data=f'topic_{i}')])
        else:
            # Если тема пустая, добавляем заполнитель
            keyboard.append([InlineKeyboardButton(f"{i}. [Тема не определена]", callback_data=f'topic_{i}')])

    # Добавляем кнопку для ввода своей темы и показать больше тем
    keyboard.append([
        InlineKeyboardButton("📝 Своя тема", callback_data='custom_topic'),
        InlineKeyboardButton("🔄 Больше тем", callback_data='more_topics')
    ])
    
    # Добавляем кнопку возврата в меню
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')])

    return InlineKeyboardMarkup(keyboard)

# Обработка нажатий на кнопки меню
def button_handler(update, context):
    """
    Обрабатывает нажатия на кнопки меню.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
        
    Returns:
        int: Следующее состояние разговора
    """
    query = update.callback_query
    query.answer()  # Подтверждаем нажатие кнопки
    user_id = query.from_user.id
    
    # Очищаем историю чата перед новым действием
    clear_chat_history(update, context)
    
    logger.info(f"Пользователь {user_id} нажал кнопку: {query.data}")

    if query.data == 'back_to_menu':
        query.edit_message_text(
            "Выберите действие в меню ниже:",
            reply_markup=main_menu()
        )
        return TOPIC
    elif query.data == 'conversation':
        # Обработка кнопки беседы о истории России
        query.edit_message_text(
            "🗣️ *Беседа о истории России*\n\n"
            "Здесь вы можете задать вопрос или начать беседу на любую тему, связанную с историей России.\n\n"
            "Просто напишите вашу мысль или вопрос, и я отвечу вам на основе исторических данных.",
            parse_mode='Markdown'
        )
        return CONVERSATION
    elif query.data == 'topic':
        # Генерируем список тем с помощью ИИ
        prompt = "Составь список из 30 ключевых тем по истории России, которые могут быть интересны для изучения. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
        try:
            query.edit_message_text("⏳ Загружаю список тем истории России...")
            topics_text = ask_grok(prompt)

            # Парсим и сохраняем темы
            filtered_topics = parse_topics(topics_text)
            context.user_data['topics'] = filtered_topics

            # Создаем клавиатуру с темами
            reply_markup = create_topics_keyboard(filtered_topics)

            query.edit_message_text(
                "📚 *Темы по истории России*\n\nВыберите тему для изучения или введите свою:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info(f"Пользователю {user_id} показаны темы для изучения")
        except Exception as e:
            log_error(e, f"Ошибка при генерации списка тем для пользователя {user_id}")
            query.edit_message_text(
                f"Произошла ошибка при генерации списка тем: {e}. Попробуй еще раз.", 
                reply_markup=main_menu()
            )
        return CHOOSE_TOPIC
    elif query.data == 'test':
        topic = context.user_data.get('current_topic', None)
        if not topic:
            query.edit_message_text(
                "⚠️ Сначала выбери тему, нажав на кнопку 'Выбрать тему'.",
                reply_markup=main_menu()
            )
            return TOPIC

        # Генерируем тест из вопросов
        query.edit_message_text(f"🧠 Генерирую тест по теме: *{topic}*...", parse_mode='Markdown')
        logger.info(f"Генерация теста по теме '{topic}' для пользователя {user_id}")

        # Используем параметры для возможности генерации большего текста
        prompt = f"Составь 15 вопросов с вариантами ответа (1, 2, 3, 4) по теме '{topic}' в истории России. После каждого вопроса с вариантами ответов укажи правильный ответ в формате 'Правильный ответ: <цифра>'. Каждый вопрос должен заканчиваться строкой '---'."
        try:
            # Увеличиваем лимит токенов для получения полных вопросов
            questions = ask_grok(prompt, max_tokens=2048)

            # Очистка и валидация вопросов
            question_list = [q.strip() for q in questions.split('---') if q.strip()]

            # Проверка наличия правильных ответов в каждом вопросе
            valid_questions = []
            for q in question_list:
                if 'Правильный ответ:' in q:
                    valid_questions.append(q)

            if not valid_questions:
                raise ValueError("Не удалось сгенерировать корректные вопросы для теста")

            context.user_data['questions'] = valid_questions
            context.user_data['current_question'] = 0
            context.user_data['score'] = 0

            # Создаем кнопку для завершения теста
            keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Очищаем правильные ответы из текста вопросов для отображения пользователю
            display_questions = []
            for q in valid_questions:
                # Удаляем строку с правильным ответом из текста вопроса
                cleaned_q = re.sub(r"Правильный ответ:\s*\d+", "", q).strip()
                display_questions.append(cleaned_q)
                
            # Сохраняем оригинальные вопросы для проверки ответов
            context.user_data['original_questions'] = valid_questions
            # Сохраняем очищенные вопросы для отображения
            context.user_data['display_questions'] = display_questions

            query.edit_message_text(
                f"📝 *Тест по теме: {topic}*\n\nНачинаем тест из {len(valid_questions)} вопросов! Вот первый вопрос:",
                parse_mode='Markdown'
            )
            query.message.reply_text(display_questions[0])
            query.message.reply_text(
                "Напиши цифру правильного ответа (1, 2, 3 или 4).", 
                reply_markup=reply_markup
            )
            logger.info(f"Тест по теме '{topic}' успешно сгенерирован для пользователя {user_id}")
        except Exception as e:
            log_error(e, f"Ошибка при генерации вопросов для пользователя {user_id}")
            query.edit_message_text(
                f"Произошла ошибка при генерации вопросов: {e}. Попробуй еще раз.", 
                reply_markup=main_menu()
            )
        return ANSWER
    elif query.data == 'more_topics':
        # Генерируем новый список тем с помощью ИИ
        # Добавляем случайный параметр для получения разных тем
        import random
        random_seed = random.randint(1, 1000)
        prompt = f"Составь список из 30 новых и оригинальных тем по истории России, которые могут быть интересны для изучения. Сосредоточься на темах {random_seed}. Выбери темы, отличные от стандартных и ранее предложенных. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
        try:
            query.edit_message_text("🔄 Генерирую новый список уникальных тем по истории России...")
            # Отключаем кэширование для получения действительно новых тем каждый раз
            topics = ask_grok(prompt, use_cache=False)

            # Парсим и сохраняем темы
            filtered_topics = parse_topics(topics)
            context.user_data['topics'] = filtered_topics

            # Создаем клавиатуру с темами
            reply_markup = create_topics_keyboard(filtered_topics)

            query.edit_message_text(
                "📚 *Новые темы по истории России*\n\nВыберите одну из только что сгенерированных тем или введите свою:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info(f"Пользователю {user_id} показан новый список тем для изучения")
        except Exception as e:
            log_error(e, f"Ошибка при генерации новых тем для пользователя {user_id}")
            query.edit_message_text(
                f"Произошла ошибка при генерации списка тем: {e}. Попробуй еще раз.", 
                reply_markup=main_menu()
            )
        return CHOOSE_TOPIC
    elif query.data == 'download_presentation':
        # Обработка кнопки скачивания презентации
        logger.info(f"Пользователь {user_id} запросил презентацию через меню")
        query.edit_message_text("Загружаю презентацию...")
        
        try:
            presentation_path = 'static/presentation.txt'
            
            # Проверяем наличие директории static
            if not os.path.exists('static'):
                os.makedirs('static')
                logger.info("Создана директория для статических файлов")
            
            # Проверяем наличие файла презентации
            if not os.path.exists(presentation_path):
                logger.warning(f"Файл презентации {presentation_path} не найден")
                # Если файла нет, создаем его
                if os.path.exists('presentation.md'):
                    with open(presentation_path, 'w', encoding='utf-8') as f:
                        with open('presentation.md', 'r', encoding='utf-8') as md_file:
                            md_content = md_file.read()
                            txt_content = md_content.replace('## ', '').replace('### ', '').replace('- ', '   - ')
                            f.write(txt_content)
                    logger.info(f"Файл презентации {presentation_path} создан")
                else:
                    logger.error("Файл presentation.md не найден")
                    query.message.reply_text("К сожалению, файл презентации не найден. Обратитесь к администратору.")
                    query.message.reply_text("Выберите действие:", reply_markup=main_menu())
                    return TOPIC
            
            # Отправляем презентацию пользователю
            with open(presentation_path, 'rb') as document:
                query.message.reply_document(
                    document=document, 
                    filename="Презентация_бота_истории_России.txt",
                    caption="📝 *Презентация бота*\nЗдесь вы можете ознакомиться с подробным описанием функций и возможностей бота.",
                    parse_mode='Markdown'
                )
            logger.info(f"Презентация отправлена пользователю {user_id}")
            query.message.reply_text("Выберите действие:", reply_markup=main_menu())
        except Exception as e:
            log_error(e, f"Ошибка при отправке презентации пользователю {user_id}")
            query.message.reply_text("К сожалению, не удалось отправить презентацию. Пожалуйста, попробуйте позже.")
            query.message.reply_text("Выберите действие:", reply_markup=main_menu())
        return TOPIC
    
    elif query.data == 'end_test' or query.data == 'cancel':
        if query.data == 'end_test':
            logger.info(f"Пользователь {user_id} досрочно завершил тест")
            query.edit_message_text("Тест завершен досрочно. Возвращаемся в главное меню.")
            query.message.reply_text("Выберите действие:", reply_markup=main_menu())
            return TOPIC
        else:
            logger.info(f"Пользователь {user_id} отменил действие")
            query.edit_message_text("Действие отменено. Нажми /start, чтобы начать заново.")
            return ConversationHandler.END
    elif query.data == 'custom_topic':
        query.edit_message_text("Напиши тему по истории России, которую ты хочешь изучить:")
        return CHOOSE_TOPIC
    elif query.data == 'more_topics':
        # Генерируем новый список тем с помощью ИИ
        # Добавляем случайный параметр для получения разных тем
        import random
        random_seed = random.randint(1, 1000)
        prompt = f"Составь список из 30 новых и оригинальных тем по истории России, которые могут быть интересны для изучения. Сосредоточься на темах {random_seed}. Выбери темы, отличные от стандартных и ранее предложенных. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
        try:
            query.edit_message_text("🔄 Генерирую новый список уникальных тем по истории России...")
            # Отключаем кэширование для получения действительно новых тем каждый раз
            topics = ask_grok(prompt, use_cache=False)

            # Парсим и сохраняем темы
            filtered_topics = parse_topics(topics)
            context.user_data['topics'] = filtered_topics

            # Создаем клавиатуру с темами
            reply_markup = create_topics_keyboard(filtered_topics)

            query.edit_message_text(
                "📚 *Новые темы по истории России*\n\nВыберите одну из только что сгенерированных тем или введите свою:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info(f"Пользователю {user_id} показан новый список тем для изучения")
        except Exception as e:
            log_error(e, f"Ошибка при генерации новых тем для пользователя {user_id}")
            query.edit_message_text(
                f"Произошла ошибка при генерации списка тем: {e}. Попробуй еще раз.", 
                reply_markup=main_menu()
            )
        return CHOOSE_TOPIC
    elif query.data == 'custom_topic':
        # Обработка кнопки своей темы
        query.edit_message_text("Напиши тему по истории России, которую ты хочешь изучить:")
        logger.info(f"Пользователь {user_id} выбрал ввод своей темы")
        return CHOOSE_TOPIC
    elif query.data == 'back_to_menu':
        query.edit_message_text(
            "Выберите действие в меню ниже:",
            reply_markup=main_menu()
        )
        return TOPIC

# Функция для получения информации о теме
def get_topic_info(topic, update_message_func=None):
    """
    Получает информацию о теме из API и форматирует её для отправки.

    Args:
        topic (str): Тема для изучения
        update_message_func (callable, optional): Функция для обновления сообщения о загрузке

    Returns:
        list: Список сообщений для отправки
    """
    chapter_titles = [
        "📜 ВВЕДЕНИЕ И ИСТОКИ",
        "⚔️ ОСНОВНЫЕ СОБЫТИЯ И РАЗВИТИЕ",
        "🏛️ КЛЮЧЕВЫЕ ФИГУРЫ И РЕФОРМЫ",
        "🌍 ВНЕШНЯЯ ПОЛИТИКА И ВЛИЯНИЕ",
        "📊 ИТОГИ И ИСТОРИЧЕСКОЕ ЗНАЧЕНИЕ"
    ]

    prompts = [
        f"Расскажи о {topic} в истории России (глава 1). Дай введение и начальную историю, истоки темы. Используй структурированное изложение. Объем - один абзац. Не пиши 'продолжение следует'.",
        f"Расскажи о {topic} в истории России (глава 2). Опиши основные события и развитие. Не делай вступление, продолжай повествование. Объем - один абзац. Не пиши 'продолжение следует'.",
        f"Расскажи о {topic} в истории России (глава 3). Сосредоточься на ключевых фигурах, реформах и внутренней политике. Объем - один абзац. Не пиши 'продолжение следует'.",
        f"Расскажи о {topic} в истории России (глава 4). Опиши внешнюю политику, международное влияние и связи. Объем - один абзац. Не пиши 'продолжение следует'.",
        f"Расскажи о {topic} в истории России (глава 5). Опиши итоги, значение в истории и культуре, последствия. Заверши повествование. Объем - один абзац."
    ]

    # Получаем информацию по частям
    all_responses = []
    for i, prompt in enumerate(prompts, 1):
        if update_message_func:
            update_message_func(f"📝 Загружаю главу {i} из {len(prompts)} по теме: *{topic}*...")
        
        # Получаем ответ от API с настройкой температуры для более точных фактов
        response = ask_grok(prompt, temp=0.3)
        
        # Удаляем лишние пробелы и переносы строк
        response = response.strip()
        
        # Добавляем заголовок главы перед текстом
        chapter_response = f"*{chapter_titles[i-1]}*\n\n{response}"
        all_responses.append(chapter_response)

    # Объединяем ответы с разделителями
    combined_responses = "\n\n" + "\n\n".join(all_responses)
    
    # Добавляем копирайт в конце материала
    combined_responses += "\n\n---\n\n*© 2025 Silver Raven. Образовательный бот по истории России.*"

    # Разделяем длинный текст на части для отправки в Telegram (макс. 4000 символов)
    messages = []
    max_length = 4000
    
    # Более эффективный алгоритм разделения на части с сохранением форматирования markdown
    parts = []
    current_part = ""
    
    # Разделяем текст по абзацам
    paragraphs = combined_responses.split('\n\n')
    
    for paragraph in paragraphs:
        # Если абзац с новой главой (начинается с *), и текущая часть не пуста, 
        # и добавление абзаца превысит лимит - сохраняем текущую часть и начинаем новую
        if paragraph.startswith('*') and current_part and len(current_part) + len(paragraph) + 2 > max_length:
            parts.append(current_part)
            current_part = paragraph
        # Иначе, если просто добавление абзаца превысит лимит - сохраняем текущую часть и начинаем новую
        elif len(current_part) + len(paragraph) + 2 > max_length:
            parts.append(current_part)
            current_part = paragraph
        # Иначе добавляем абзац к текущей части
        else:
            if current_part:
                current_part += '\n\n' + paragraph
            else:
                current_part = paragraph
    
    # Добавляем последнюю часть, если она не пуста
    if current_part:
        parts.append(current_part)
    
    # Проверяем, что копирайт есть только в последней части
    # Если копирайт оказался в середине - перемещаем его в конец
    copyright_text = "*© 2025 Silver Raven. Образовательный бот по истории России.*"
    for i in range(len(parts) - 1):
        if copyright_text in parts[i]:
            parts[i] = parts[i].replace(copyright_text, "").strip()
            if not parts[-1].endswith(copyright_text):
                parts[-1] = parts[-1] + "\n\n---\n\n" + copyright_text
    
    # Если копирайт отсутствует в последней части, добавляем его
    if not parts[-1].endswith(copyright_text):
        if "---" not in parts[-1][-10:]:
            parts[-1] = parts[-1] + "\n\n---\n\n" + copyright_text
        else:
            parts[-1] = parts[-1] + "\n\n" + copyright_text
    
    # Форматируем части для отправки
    for part in parts:
        messages.append(part)

    return messages

# Обработка выбора темы из списка или ввода своей темы
def choose_topic(update, context):
    """
    Обрабатывает выбор темы пользователем из списка или ввод своей темы.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
        
    Returns:
        int: Следующее состояние разговора
    """
    user_id = None
    
    # Проверяем, пришел ли запрос от кнопки или от текстового сообщения
    if update.callback_query:
        query = update.callback_query
        query.answer()
        user_id = query.from_user.id
        
        # Очищаем историю чата перед новым действием
        clear_chat_history(update, context)
        
        logger.info(f"Пользователь {user_id} выбирает тему через кнопку: {query.data}")
        
        # Если пользователь выбрал "Больше тем"
        if query.data == 'more_topics':
            return button_handler(update, context)
        
        # Если пользователь выбрал "Своя тема"
        elif query.data == 'custom_topic':
            query.edit_message_text("Напиши тему по истории России, которую ты хочешь изучить:")
            return CHOOSE_TOPIC
        
        # Если пользователь хочет вернуться в меню
        elif query.data == 'back_to_menu':
            return button_handler(update, context)
        
        # Если пользователь выбрал тему из списка
        elif query.data.startswith('topic_'):
            try:
                topic_index = int(query.data.split('_')[1]) - 1

                # Проверяем наличие индекса в списке
                if 0 <= topic_index < len(context.user_data['topics']):
                    topic = context.user_data['topics'][topic_index]
                    # Удаляем номер из темы, если он есть
                    if '. ' in topic:
                        topic = topic.split('. ', 1)[1]

                    context.user_data['current_topic'] = topic
                    query.edit_message_text(f"📝 Загружаю информацию по теме: *{topic}*...", parse_mode='Markdown')
                    logger.info(f"Пользователь {user_id} выбрал тему: {topic}")

                    # Функция для обновления сообщения о загрузке
                    def update_message(text):
                        query.edit_message_text(text, parse_mode='Markdown')

                    # Получаем информацию о теме
                    messages = get_topic_info(topic, update_message)

                    # Отправляем первое сообщение с тем же ID (edit)
                    if messages:
                        query.edit_message_text(messages[0], parse_mode='Markdown')

                        # Отправляем остальные сообщения как новые
                        for msg in messages[1:]:
                            query.message.reply_text(msg, parse_mode='Markdown')

                    query.message.reply_text("Выбери следующее действие:", reply_markup=main_menu())
                    logger.info(f"Пользователю {user_id} успешно отправлена информация по теме: {topic}")
                else:
                    logger.warning(f"Пользователь {user_id} выбрал несуществующую тему с индексом {topic_index+1}")
                    query.edit_message_text(
                        f"Ошибка: Тема с индексом {topic_index+1} не найдена. Попробуйте выбрать другую тему.", 
                        reply_markup=main_menu()
                    )
            except Exception as e:
                log_error(e, f"Ошибка при обработке темы для пользователя {user_id}")
                query.edit_message_text(
                    f"Произошла ошибка при загрузке темы: {e}. Попробуй еще раз.", 
                    reply_markup=main_menu()
                )
            return TOPIC
    # Возвращаем CHOOSE_TOPIC, если не обработано другими условиями
    return CHOOSE_TOPIC

# Обработка ввода своей темы
def handle_custom_topic(update, context):
    """
    Обрабатывает ввод пользователем своей темы.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
        
    Returns:
        int: Следующее состояние разговора
    """
    topic = update.message.text
    user_id = update.message.from_user.id
    context.user_data['current_topic'] = topic
    
    # Очищаем историю чата перед обработкой новой темы
    clear_chat_history(update, context)
    
    logger.info(f"Пользователь {user_id} ввел свою тему: {topic}")

    try:
        update.message.reply_text(f"📝 Загружаю информацию по теме: *{topic}*...", parse_mode='Markdown')

        # Функция для обновления сообщения о загрузке
        def update_message(text):
            update.message.reply_text(text, parse_mode='Markdown')

        # Получаем информацию о теме
        messages = get_topic_info(topic, update_message)

        # Отправляем все сообщения
        for msg in messages:
            update.message.reply_text(msg, parse_mode='Markdown')

        update.message.reply_text("Выбери следующее действие:", reply_markup=main_menu())
        logger.info(f"Пользователю {user_id} успешно отправлена информация по теме: {topic}")
    except Exception as e:
        log_error(e, f"Ошибка при обработке пользовательской темы для пользователя {user_id}")
        update.message.reply_text(f"Произошла ошибка: {e}. Попробуй еще раз.", reply_markup=main_menu())
    return TOPIC

# Обработка ответов на тест
def handle_answer(update, context):
    """
    Обрабатывает ответы пользователя на вопросы теста.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
        
    Returns:
        int: Следующее состояние разговора
    """
    user_answer = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Очищаем историю чата перед ответом на новый вопрос
    clear_chat_history(update, context)
    
    questions = context.user_data.get('questions', [])
    current_question = context.user_data.get('current_question', 0)
    
    if not questions:
        logger.warning(f"Пользователь {user_id} пытается ответить на вопрос, но вопросы отсутствуют")
        update.message.reply_text(
            "Ошибка: вопросы не найдены. Начните тест заново.",
            reply_markup=main_menu()
        )
        return TOPIC

    # Получаем оригинальные вопросы с правильными ответами и вопросы для отображения
    original_questions = context.user_data.get('original_questions', questions)
    display_questions = context.user_data.get('display_questions', questions)
    
    # Валидация пользовательского ввода
    valid_answers = ['1', '2', '3', '4']
    if user_answer not in valid_answers:
        sent_msg = update.message.reply_text(
            "⚠️ Пожалуйста, введите только цифру (1, 2, 3 или 4)."
        )
        save_message_id(update, context, sent_msg.message_id)
        
        # Создаем клавиатуру с кнопкой для завершения теста
        keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_msg = update.message.reply_text(
            "Введите ответ еще раз:",
            reply_markup=reply_markup
        )
        save_message_id(update, context, sent_msg.message_id)
        return ANSWER
    
    # Парсим правильный ответ из оригинального текста вопроса
    try:
        correct_answer_match = re.search(r"Правильный ответ:\s*(\d+)", original_questions[current_question])
        if correct_answer_match:
            correct_answer = correct_answer_match.group(1)
        else:
            # Попытка найти ответ в альтернативных форматах
            alt_match = re.search(r"Правильный ответ[:-]\s*([1-4])", original_questions[current_question], re.IGNORECASE)
            if alt_match:
                correct_answer = alt_match.group(1)
            else:
                raise ValueError("Формат правильного ответа не найден")
    except (IndexError, ValueError) as e:
        logger.error(f"Ошибка при обработке ответа пользователя {user_id}: {e}")
        update.message.reply_text(
            "Ошибка в формате вопросов. Попробуй начать тест заново, нажав 'Пройти тест'.", 
            reply_markup=main_menu()
        )
        return TOPIC

    # Отслеживаем ответы пользователя для статистики
    if 'user_answers' not in context.user_data:
        context.user_data['user_answers'] = []
    
    # Добавляем текущий ответ в статистику
    context.user_data['user_answers'].append({
        'question_num': current_question + 1,
        'user_answer': user_answer,
        'correct_answer': correct_answer,
        'is_correct': user_answer == correct_answer
    })
    
    # Проверяем ответ пользователя
    if user_answer == correct_answer:
        context.user_data['score'] = context.user_data.get('score', 0) + 1
        sent_msg = update.message.reply_text("✅ Правильно!")
        save_message_id(update, context, sent_msg.message_id)
        logger.info(f"Пользователь {user_id} ответил верно на вопрос {current_question+1}")
    else:
        # Не показываем правильный ответ во время теста
        sent_msg = update.message.reply_text("❌ Неправильно!")
        save_message_id(update, context, sent_msg.message_id)
        logger.info(f"Пользователь {user_id} ответил неверно на вопрос {current_question+1}")

    # Переходим к следующему вопросу
    context.user_data['current_question'] = current_question + 1
    
    if context.user_data['current_question'] < len(display_questions):
        next_question = context.user_data['current_question'] + 1
        sent_msg1 = update.message.reply_text(f"Вопрос {next_question} из {len(display_questions)}:")
        save_message_id(update, context, sent_msg1.message_id)
        
        sent_msg2 = update.message.reply_text(display_questions[context.user_data['current_question']])
        save_message_id(update, context, sent_msg2.message_id)

        # Создаем клавиатуру с кнопкой для завершения теста
        keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        sent_msg3 = update.message.reply_text("Напиши цифру правильного ответа (1, 2, 3 или 4).", reply_markup=reply_markup)
        save_message_id(update, context, sent_msg3.message_id)
        return ANSWER
    else:
        # Тест завершен, показываем результаты
        score = context.user_data.get('score', 0)
        total_questions = len(questions)
        percentage = (score / total_questions) * 100
        
        # Оценка усвоенного материала с развернутым комментарием
        if percentage >= 90:
            assessment = "🏆 Отлично! Ты прекрасно усвоил материал. Твои знания по данной теме очень глубокие."
            next_steps = "Можешь попробовать изучить другие темы или углубить знания по смежным историческим периодам."
        elif percentage >= 70:
            assessment = "👍 Хорошо! Ты неплохо усвоил материал, но есть над чем поработать."
            next_steps = "Рекомендую повторить некоторые аспекты темы и затем снова пройти тест для закрепления."
        elif percentage >= 50:
            assessment = "👌 Удовлетворительно. Ты понимаешь основы темы, но многие детали упущены."
            next_steps = "Стоит внимательнее изучить материал, особенно обратить внимание на даты и ключевые события."
        else:
            assessment = "📚 Неудовлетворительно. Тема усвоена недостаточно хорошо."
            next_steps = "Рекомендую заново изучить все главы по данной теме и затем повторить тестирование."
        
        # Формируем краткую статистику по ответам
        user_answers = context.user_data.get('user_answers', [])
        incorrect_count = sum(1 for answer in user_answers if not answer['is_correct'])
        
        # Добавляем информацию о правильных ответах на вопросы, в которых пользователь ошибся
        incorrect_info = ""
        if incorrect_count > 0:
            incorrect_info = "\n\n*Информация о правильных ответах:*\n"
            for answer in user_answers:
                if not answer['is_correct']:
                    q_num = answer['question_num']
                    correct = answer['correct_answer']
                    incorrect_info += f"• Вопрос {q_num}: правильный ответ - {correct}\n"
            
        # Отправляем результаты теста
        update.message.reply_text(
            f"🎯 *Тест завершен!*\n\nТы ответил правильно на {score} из {total_questions} вопросов ({percentage:.1f}%).\n\n"
            f"{assessment}\n\n{next_steps}{incorrect_info}\n\n"
            "Выбери следующее действие:",
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )
        logger.info(f"Пользователь {user_id} завершил тест с результатом {score}/{total_questions} ({percentage:.1f}%)")
        
        # Очищаем информацию о текущем тесте
        # Но сохраняем выбранную тему
        current_topic = context.user_data.get('current_topic')
        context.user_data.pop('questions', None)
        context.user_data.pop('current_question', None)
        context.user_data.pop('score', None)
        context.user_data.pop('user_answers', None)
        context.user_data.pop('original_questions', None)
        context.user_data.pop('display_questions', None)
        if current_topic:
            context.user_data['current_topic'] = current_topic
            
        return TOPIC

# Функция для обработки сообщений в режиме беседы
def handle_conversation(update, context):
    """
    Обрабатывает сообщения пользователя в режиме беседы.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
        
    Returns:
        int: Следующее состояние разговора
    """
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    # Очищаем историю чата перед ответом на новое сообщение
    clear_chat_history(update, context)
    
    logger.info(f"Пользователь {user_id} отправил сообщение в режиме беседы: {user_message[:50]}...")
    
    # Проверяем, относится ли сообщение к истории России
    check_prompt = f"Проверь, относится ли следующее сообщение к истории России: \"{user_message}\". Ответь только 'да' или 'нет'."
    
    # Отправляем индикатор набора текста
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
    
    try:
        # Проверяем тему сообщения
        is_history_related = ask_grok(check_prompt, max_tokens=50).lower().strip()
        logger.info(f"Проверка темы сообщения пользователя {user_id}: {is_history_related}")
        
        if 'да' in is_history_related:
            # Если сообщение относится к истории России
            prompt = f"Пользователь задал вопрос на тему истории России: \"{user_message}\"\n\n" \
                    "Ответь на этот вопрос, опираясь на исторические факты. " \
                    "Будь информативным, но кратким."
        else:
            # Если сообщение не относится к истории России
            prompt = f"Пользователь задал вопрос не относящийся к истории России: \"{user_message}\"\n\n" \
                    "Вежливо объясни, что ты специализируешься только на истории России, и " \
                    "предложи задать вопрос, связанный с историей России. Приведи пример возможного вопроса."
        
        # Получаем ответ от API
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
        response = ask_grok(prompt, max_tokens=1024)
        
        # Отправляем ответ пользователю и сохраняем ID сообщения
        sent_msg = update.message.reply_text(response)
        save_message_id(update, context, sent_msg.message_id)
        logger.info(f"Отправлен ответ пользователю {user_id}")
        
        # Предлагаем продолжить беседу или вернуться в меню
        keyboard = [
            [InlineKeyboardButton("🔙 Вернуться в меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Если сообщение не относилось к истории, добавляем дополнительное пояснение
        if 'да' not in is_history_related:
            update.message.reply_text(
                "⚠️ Я могу общаться только на темы, связанные с историей России. Пожалуйста, задайте вопрос по этой теме.",
                reply_markup=reply_markup
            )
            logger.info(f"Пользователь {user_id} получил предупреждение о теме сообщения")
        else:
            update.message.reply_text(
                "Вы можете продолжить беседу, задав новый вопрос, или вернуться в главное меню:",
                reply_markup=reply_markup
            )
    except Exception as e:
        log_error(e, f"Ошибка при обработке беседы для пользователя {user_id}")
        update.message.reply_text(
            f"Произошла ошибка при обработке вашего сообщения: {e}. Попробуйте еще раз или вернитесь в меню.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Вернуться в меню", callback_data='back_to_menu')]])
        )
    
    return CONVERSATION

# Функция для очистки истории чата
def clear_chat_history(update, context):
    """
    Очищает историю чата, удаляя все предыдущие сообщения бота и пользователя.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
    """
    try:
        # Получаем ID чата
        chat_id = update.effective_chat.id
        
        # Получаем текущее сообщение ID
        current_message_id = None
        if update.message:
            current_message_id = update.message.message_id
        elif update.callback_query and update.callback_query.message:
            current_message_id = update.callback_query.message.message_id
        
        # Если нет текущего сообщения, не можем определить диапазон
        if not current_message_id:
            logger.warning(f"Не удалось определить текущее сообщение для чата {chat_id}")
            return
        
        # Получаем все сохраненные ID сообщений для удаления
        message_ids_to_delete = context.user_data.get('previous_messages', [])
        
        # Если нет сохраненных ID, пытаемся использовать диапазон сообщений
        if not message_ids_to_delete:
            # Определяем диапазон сообщений для удаления
            first_message_id = context.user_data.get('first_message_id', current_message_id - 200)
            
            # Создаем список ID сообщений для удаления
            message_ids_to_delete = list(range(first_message_id, current_message_id))
        
        # Добавляем более старые сообщения для обеспечения полной очистки
        extra_old_messages = list(range(current_message_id - 300, current_message_id - 200))
        message_ids_to_delete.extend(extra_old_messages)
        
        # Удаляем дубликаты и сортируем ID сообщений в обратном порядке
        message_ids_to_delete = sorted(list(set(message_ids_to_delete)), reverse=True)
        
        # Группируем удаление для большей эффективности
        batches = [message_ids_to_delete[i:i+30] for i in range(0, len(message_ids_to_delete), 30)]
        
        # Удаляем сообщения пакетами
        total_deleted = 0
        total_errors = 0
        
        import time
        
        for batch in batches:
            deleted_in_batch = 0
            errors_in_batch = 0
            
            for msg_id in batch:
                if msg_id >= current_message_id:
                    continue  # Пропускаем текущее и будущие сообщения
                
                try:
                    context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted_in_batch += 1
                    total_deleted += 1
                    
                    # Короткая пауза после каждого 5-го удаления, чтобы избежать ограничений API
                    if deleted_in_batch % 5 == 0:
                        time.sleep(0.05)
                        
                except Exception as e:
                    errors_in_batch += 1
                    total_errors += 1
                    
                    # Лог для отладки, но не перегружаем журнал
                    if errors_in_batch <= 3:
                        logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
            
            # Пауза между пакетами для снижения нагрузки на API
            if deleted_in_batch > 0:
                time.sleep(0.5)
        
        # Сохраняем текущее ID сообщения как отправную точку для следующей очистки
        context.user_data['first_message_id'] = current_message_id
        
        # Сбрасываем список предыдущих сообщений
        context.user_data['previous_messages'] = []
        
        logger.info(f"История чата очищена для пользователя {chat_id}: удалено {total_deleted} сообщений, {total_errors} ошибок")
    except Exception as e:
        logger.error(f"Ошибка при очистке истории чата: {e}")

# Функция для сохранения ID сообщения
def save_message_id(update, context, message_id):
    """
    Сохраняет ID сообщения в список предыдущих сообщений.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
        message_id (int): ID сообщения для сохранения
    """
    if 'previous_messages' not in context.user_data:
        context.user_data['previous_messages'] = []
    
    context.user_data['previous_messages'].append(message_id)
    
    # Ограничиваем список последними 50 сообщениями
    if len(context.user_data['previous_messages']) > 50:
        context.user_data['previous_messages'] = context.user_data['previous_messages'][-50:]

# Обработчик ошибок
def error_handler(update, context):
    """
    Обработчик ошибок: записывает их в журнал с комментариями и информирует пользователя.
    
    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
    """
    error = context.error
    error_type = type(error).__name__

    # Используем расширенное логирование ошибок
    user_info = f"пользователь {update.effective_user.id}" if update and update.effective_user else "неизвестный пользователь"
    additional_info = f"Ошибка для {user_info} в обновлении {update}" if update else "Ошибка без контекста обновления"
    
    log_error(error, additional_info)

    if update and update.effective_message:
        # Формируем информативное сообщение для пользователя
        error_message = f"❌ Произошла ошибка: {error}"

        # Добавляем пользователю пояснение для известных типов ошибок
        if error_type in ERROR_DESCRIPTIONS:
            error_message += f"\n{ERROR_DESCRIPTIONS[error_type]}"

        update.effective_message.reply_text(
            error_message,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
        )

# Основная функция для запуска бота
def main():
    """
    Основная функция для инициализации и запуска бота.
    """
    try:
        logger.info("Запуск бота и веб-сервера логов...")
        print("Начинаю запуск бота и веб-сервера логов...")
        
        # Запускаем Flask-сервер для отображения логов в отдельном потоке
        logger.info("Запуск Flask-сервера для отображения логов...")
        flask_thread = background.start_flask_server()
        if flask_thread:
            logger.info("Flask-сервер запущен на http://0.0.0.0:8080")
        else:
            logger.warning("Не удалось запустить Flask-сервер")
        
        # Проверка наличия токенов с более подробными сообщениями
        if not TELEGRAM_TOKEN:
            error_msg = "Отсутствует TELEGRAM_TOKEN! Проверьте .env файл. Токен должен быть установлен в переменной TELEGRAM_TOKEN."
            logger.error(error_msg)
            print(error_msg)
            return
        if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN_HERE":
            error_msg = "TELEGRAM_TOKEN не настроен! Замените YOUR_TELEGRAM_TOKEN_HERE на реальный токен в .env файле."
            logger.error(error_msg)
            print(error_msg)
            return
        if not GEMINI_API_KEY:
            error_msg = "Отсутствует GEMINI_API_KEY! Проверьте .env файл. Ключ должен быть установлен в переменной GEMINI_API_KEY."
            logger.error(error_msg)
            print(error_msg)
            return
        if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            error_msg = "GEMINI_API_KEY не настроен! Замените YOUR_GEMINI_API_KEY_HERE на реальный ключ в .env файле."
            logger.error(error_msg)
            print(error_msg)
            return

        # Инициализируем бота и диспетчер
        updater = Updater(TELEGRAM_TOKEN, use_context=True)
        dp = updater.dispatcher
            
        # Добавляем команду для получения презентации
        def get_presentation(update, context):
            """
            Обрабатывает команду /presentation, отправляет презентацию бота.
            
            Args:
                update (telegram.Update): Объект обновления Telegram
                context (telegram.ext.CallbackContext): Контекст разговора
            """
            user = update.message.from_user
            logger.info(f"Пользователь {user.id} запросил презентацию")
            
            try:
                presentation_path = 'static/presentation.txt'
                
                # Проверяем наличие директории static
                if not os.path.exists('static'):
                    os.makedirs('static')
                    logger.info("Создана директория для статических файлов")
                
                # Проверяем наличие файла презентации
                if not os.path.exists(presentation_path):
                    logger.warning(f"Файл презентации {presentation_path} не найден")
                    # Если файла нет, создаем его из MD версии
                    if os.path.exists('presentation.md'):
                        with open(presentation_path, 'w', encoding='utf-8') as f:
                            with open('presentation.md', 'r', encoding='utf-8') as md_file:
                                md_content = md_file.read()
                                txt_content = md_content.replace('## ', '').replace('### ', '').replace('- ', '   - ')
                                f.write(txt_content)
                        logger.info(f"Файл презентации {presentation_path} создан")
                    else:
                        logger.error("Файл presentation.md не найден")
                        update.message.reply_text("К сожалению, файл презентации не найден. Обратитесь к администратору.")
                        return
                
                # Отправляем презентацию пользователю
                with open(presentation_path, 'rb') as document:
                    sent_doc = update.message.reply_document(
                        document=document, 
                        filename="Презентация_бота_истории_России.txt",
                        caption="📝 *Презентация бота*\nЗдесь вы можете ознакомиться с подробным описанием функций и возможностей бота.",
                        parse_mode='Markdown'
                    )
                    # Сохраняем ID сообщения с документом
                    save_message_id(update, context, sent_doc.message_id)
                logger.info(f"Презентация отправлена пользователю {user.id}")
            except Exception as e:
                log_error(e, f"Ошибка при отправке презентации пользователю {user.id}")
                update.message.reply_text("К сожалению, не удалось отправить презентацию. Пожалуйста, попробуйте позже.")
        
        # Создаем ConversationHandler для управления диалогом
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start), CommandHandler('presentation', get_presentation)],
            states={
                TOPIC: [
                    CallbackQueryHandler(button_handler)
                ],
                CHOOSE_TOPIC: [
                    CallbackQueryHandler(button_handler, pattern='^(more_topics|custom_topic|back_to_menu)$'),
                    CallbackQueryHandler(choose_topic, pattern='^topic_'),
                    MessageHandler(Filters.text & ~Filters.command, handle_custom_topic)
                ],
                TEST: [
                    CallbackQueryHandler(button_handler)
                ],
                ANSWER: [
                    MessageHandler(Filters.text & ~Filters.command, handle_answer),
                    CallbackQueryHandler(button_handler)  # Добавляем обработчик для кнопки завершения теста
                ],
                CONVERSATION: [
                    MessageHandler(Filters.text & ~Filters.command, handle_conversation),
                    CallbackQueryHandler(button_handler)  # Обработчик для кнопки возврата в меню
                ]
            },
            fallbacks=[CommandHandler('start', start)],
            allow_reentry=True
        )

        # Добавляем обработчики
        dp.add_error_handler(error_handler)
        dp.add_handler(conv_handler)

        # Запускаем бота
        logger.info("Бот успешно запущен")
        print("Бот успешно запущен")
        updater.start_polling()
        updater.idle()

    except Exception as e:
        log_error(e, "Критическая ошибка при запуске бота")
        logger.critical(f"Бот не был запущен из-за критической ошибки: {e}")
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == '__main__':
    main()
