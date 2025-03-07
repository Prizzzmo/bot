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

    Returns:
        tuple: Кортеж (директория логов, путь к файлу лога)
    """
    try:
        # Проверяем наличие директории для логов
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"Создана директория для логов: {log_dir}")

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

# Класс для кэширования ответов API с улучшенной производительностью
class APICache:
    """
    Оптимизированный класс для кэширования ответов API.
    Поддерживает сохранение и загрузку кэша из файла.
    Добавлена оптимизация по времени жизни кэша и сохранению на диск.
    """
    def __init__(self, max_size=100, cache_file='api_cache.json', save_interval=20):
        self.cache = {}
        self.max_size = max_size
        self.cache_file = cache_file
        self.save_interval = save_interval  # Интервал автоматического сохранения кэша
        self.operation_count = 0  # Счетчик операций для периодического сохранения
        self.load_cache()

    def get(self, key):
        """Получить значение из кэша по ключу с обновлением времени доступа"""
        if key in self.cache:
            # Обновляем время последнего доступа
            self.cache[key]['last_accessed'] = datetime.now().timestamp()
            return self.cache[key]['value']
        return None

    def set(self, key, value, ttl=86400):  # ttl по умолчанию 24 часа
        """Добавить значение в кэш с оптимизированной стратегией вытеснения"""
        # Если кэш переполнен, удаляем наименее востребованные элементы
        if len(self.cache) >= self.max_size:
            # Используем более эффективный алгоритм сортировки
            items_to_remove = sorted(
                [(k, v['last_accessed']) for k, v in self.cache.items()],
                key=lambda x: x[1]
            )[:int(self.max_size * 0.2)]  # Удаляем 20% старых элементов

            for key_to_remove, _ in items_to_remove:
                del self.cache[key_to_remove]

        timestamp = datetime.now().timestamp()
        # Добавляем новый элемент с временной меткой и TTL
        self.cache[key] = {
            'value': value,
            'last_accessed': timestamp,
            'created_at': timestamp,
            'ttl': ttl
        }

        # Инкрементируем счетчик операций
        self.operation_count += 1

        # Периодически сохраняем кэш и очищаем устаревшие записи
        if self.operation_count >= self.save_interval:
            self.cleanup_expired()
            self.save_cache()
            self.operation_count = 0

    def cleanup_expired(self):
        """Очистка устаревших элементов кэша по TTL"""
        current_time = datetime.now().timestamp()
        keys_to_remove = []

        for key, data in self.cache.items():
            if current_time - data['created_at'] > data['ttl']:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        if keys_to_remove:
            logger.info(f"Удалено {len(keys_to_remove)} устаревших элементов из кэша")

    def load_cache(self):
        """Загружает кэш из файла, если он существует, с оптимизацией"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    loaded_cache = json.load(f)
                    # Добавляем проверку TTL при загрузке
                    current_time = datetime.now().timestamp()
                    for k, v in loaded_cache.items():
                        if 'created_at' in v and 'ttl' in v:
                            if current_time - v['created_at'] <= v['ttl']:
                                self.cache[k] = v
                        else:
                            # Для обратной совместимости
                            self.cache[k] = {
                                'value': v.get('value', v),
                                'last_accessed': v.get('last_accessed', current_time),
                                'created_at': v.get('created_at', current_time),
                                'ttl': v.get('ttl', 86400)
                            }

                    logger.info(f"Кэш загружен из {self.cache_file}, {len(self.cache)} записей")
        except Exception as e:
            logger.error(f"Ошибка при загрузке кэша: {e}")
            self.cache = {}

    def save_cache(self):
        """Сохраняет кэш в файл с оптимизацией"""
        try:
            # Используем временный файл для безопасной записи
            temp_file = f"{self.cache_file}.temp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False)

            # Переименовываем временный файл для атомарной операции
            os.replace(temp_file, self.cache_file)
            logger.info(f"Кэш сохранен в {self.cache_file}, {len(self.cache)} записей")
        except Exception as e:
            logger.error(f"Ошибка при сохранении кэша: {e}")

    def clear(self):
        """Очистить кэш"""
        self.cache.clear()
        self.save_cache()

# Создаем глобальный экземпляр кэша
api_cache = APICache(max_size=200, save_interval=10)  # Увеличенный размер кэша и меньший интервал сохранения

# Получаем ключи API из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Используем Google Gemini API

# Оптимизированная функция для запросов к Google Gemini API
def ask_grok(prompt, max_tokens=1024, temp=0.7, use_cache=True):
    """
    Отправляет запрос к Google Gemini API и возвращает ответ с оптимизированным кэшированием.

    Args:
        prompt (str): Текст запроса
        max_tokens (int): Максимальное количество токенов в ответе
        temp (float): Температура генерации (0.0-1.0)
        use_cache (bool): Использовать ли кэширование

    Returns:
        str: Ответ от API или сообщение об ошибке
    """
    # Создаем более короткий уникальный ключ для кэша на основе хэша запроса
    if use_cache:
        import hashlib
        cache_key = hashlib.md5(f"{prompt}_{max_tokens}_{temp}".encode()).hexdigest()

        # Проверяем кэш с улучшенной производительностью
        cached_response = api_cache.get(cache_key)
        if cached_response:
            logger.info("Использую кэшированный ответ")
            return cached_response

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
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

        # Оптимизируем запрос с таймаутом и пулингом соединений
        session = requests.Session()
        response = session.post(url, headers=headers, json=data, timeout=30)
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

        # Сохраняем результат в кэш с TTL в зависимости от типа запроса
        # Долгоживущий кэш для более общих запросов, короткий для специфичных
        if use_cache:
            ttl = 86400  # 24 часа по умолчанию
            if "тест" in prompt.lower():
                ttl = 3600  # 1 час для тестов
            elif "беседа" in prompt.lower() or "разговор" in prompt.lower():
                ttl = 1800  # 30 минут для бесед

            api_cache.set(cache_key, result, ttl=ttl)

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
        [InlineKeyboardButton("ℹ️ Информация о проекте", callback_data='project_info')],
        [InlineKeyboardButton("❌ Завершить", callback_data='cancel')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команда /start (начало работы с ботом)
def start(update, context):
    """
    Обрабатывает команду /start, показывает приветствие и главное меню.

    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора

    Returns:
        int: Следующее состояние разговора
    """
    user = update.message.from_user
    logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")

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
        "❗ *Данный бот создан в качестве учебного пособия.*",
        parse_mode='Markdown'
    )
    # Сохраняем ID сообщения
    save_message_id(update, context, sent_message.message_id)

    # Отправляем основное меню
    sent_msg = update.message.reply_text(
        "Выберите действие в меню ниже, чтобы начать:",
        reply_markup=main_menu()
    )
    save_message_id(update, context, sent_msg.message_id)
    return TOPIC

# Оптимизированная функция для парсинга тем из текста ответа API
def parse_topics(topics_text):
    """
    Парсит текст с темами и возвращает отформатированный список тем с оптимизацией.

    Args:
        topics_text (str): Текст с темами от API

    Returns:
        list: Список отформатированных тем
    """
    filtered_topics = []

    # Оптимизированное регулярное выражение для более эффективного извлечения тем
    pattern = r'(?:^\d+[.):]\s*|^[*•-]\s*|^[а-яА-Я\w]+[:.]\s*)(.+?)$'

    # Используем множество для быстрой проверки дубликатов
    unique_topics_set = set()

    for line in topics_text.split('\n'):
        line = line.strip()
        if not line or len(line) <= 1:
            continue

        # Пытаемся извлечь тему с помощью регулярного выражения
        match = re.search(pattern, line, re.MULTILINE)
        if match:
            topic_text = match.group(1).strip()
            if topic_text and topic_text not in unique_topics_set:
                filtered_topics.append(topic_text)
                unique_topics_set.add(topic_text)
        # Если регулярное выражение не сработало, используем упрощенную версию
        elif '.' in line or ':' in line:
            parts = line.split('.', 1) if '.' in line else line.split(':', 1)
            if len(parts) > 1:
                topic_text = parts[1].strip()
                if topic_text and topic_text not in unique_topics_set:
                    filtered_topics.append(topic_text)
                    unique_topics_set.add(topic_text)
        # Простая эвристика для строк, начинающихся с цифры
        elif line[0].isdigit():
            i = 1
            while i < len(line) and (line[i].isdigit() or line[i] in ' \t.):'):
                i += 1
            if i < len(line):
                topic_text = line[i:].strip()
                if topic_text and topic_text not in unique_topics_set:
                    filtered_topics.append(topic_text)
                    unique_topics_set.add(topic_text)
        else:
            if line not in unique_topics_set:
                filtered_topics.append(line)
                unique_topics_set.add(line)

    # Ограничиваем до 30 тем
    return filtered_topics[:30]

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
    try:
        query.answer()  # Подтверждаем нажатие кнопки
    except Exception as e:
        logger.warning(f"Не удалось подтвердить кнопку: {e}")

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
    elif query.data == 'project_info':
        # Загружаем информацию о проекте из файла
        try:
            with open('static/presentation.txt', 'r', encoding='utf-8') as file:
                presentation_text = file.read()
        except Exception as e:
            logger.error(f"Ошибка при чтении файла presentation.txt: {e}")
            presentation_text = "Информация о проекте временно недоступна."

        # Разбиваем длинный текст на части (максимум 3000 символов)
        max_length = 3000
        parts = []
        
        # Заголовок добавляем только в первую часть
        current_part = "📋 *Информация о проекте*\n\n"
        
        # Разбиваем текст по параграфам для сохранения форматирования
        paragraphs = presentation_text.split('\n\n')
        
        for paragraph in paragraphs:
            # Если добавление параграфа превысит максимальную длину
            if len(current_part) + len(paragraph) + 2 > max_length:
                # Сохраняем текущую часть
                parts.append(current_part)
                current_part = paragraph
            else:
                # Добавляем параграф с разделителем
                if current_part and current_part != "📋 *Информация о проекте*\n\n":
                    current_part += '\n\n' + paragraph
                else:
                    current_part += paragraph
        
        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part)
        
        try:
            # Отправляем первую часть с редактированием сообщения
            query.edit_message_text(
                parts[0][:4000],  # Ограничиваем длину для безопасности
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
            )
            
            # Отправляем остальные части как новые сообщения
            for part in parts[1:]:
                query.message.reply_text(
                    part[:4000],  # Ограничиваем длину для безопасности
                    parse_mode='Markdown'
                )
                
            logger.info(f"Пользователь {user_id} просмотрел информацию о проекте")
        except telegram.error.BadRequest as e:
            logger.error(f"Ошибка при отправке информации о проекте: {e}")
            # Отправляем новое сообщение вместо редактирования
            for part in parts:
                query.message.reply_text(
                    part[:4000],  # Ограничиваем длину для безопасности
                    parse_mode='Markdown'
                )
            query.message.reply_text(
                "Выберите действие:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
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
            try:
                query.edit_message_text("⏳ Загружаю список тем истории России...")
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение о загрузке тем: {e}")
                query.message.reply_text("⏳ Загружаю список тем истории России...")

            topics_text = ask_grok(prompt)

            # Парсим и сохраняем темы
            filtered_topics = parse_topics(topics_text)
            context.user_data['topics'] = filtered_topics

            # Создаем клавиатуру с темами
            reply_markup = create_topics_keyboard(filtered_topics)

            try:
                query.edit_message_text(
                    "📚 *Темы по истории России*\n\nВыберите тему для изучения или введите свою:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение со списком тем: {e}")
                query.message.reply_text(
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
    elif query.data == 'back_to_menu':
        query.edit_message_text(
            "Выберите действие в меню ниже:",
            reply_markup=main_menu()
        )
        return TOPIC

# Оптимизированная функция для получения информации о теме
def get_topic_info(topic, update_message_func=None):
    """
    Получает информацию о теме из API и форматирует её для отправки с оптимизацией.

    Args:
        topic (str): Тема для изучения
        update_message_func (callable, optional): Функция для обновления сообщенияо загрузке

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

    # Оптимизация: параллельная обработка запросов к API (используем нативные потоки)
    all_responses = [""] * len(prompts)
    threads = []

    def fetch_response(index, prompt):
        if update_message_func:
            update_message_func(f"📝 Загружаю главу {index+1} из {len(prompts)} по теме: *{topic}*...")

        # Получаем ответ от API с использованием общего кэша
        response = ask_grok(prompt)

        # Добавляем заголовок главы перед текстом
        chapter_response = f"*{chapter_titles[index]}*\n\n{response}"
        all_responses[index] = chapter_response

    # Создаем и запускаем потоки
    for i, prompt in enumerate(prompts):
        thread = threading.Thread(target=fetch_response, args=(i, prompt))
        thread.start()
        threads.append(thread)
        # Добавляем небольшую задержку для разгрузки API
        import time
        time.sleep(0.5)

    # Ждем завершения всех потоков
    for thread in threads:
        thread.join()

    # Объединяем ответы с разделителями
    combined_responses = "\n\n" + "\n\n".join(all_responses)

    # Оптимизированный алгоритм разделения на части (макс. 4000 символов) для отправки в Telegram
    messages = []
    max_length = 4000

    # Эффективный алгоритм разделения на части с сохранением форматирования markdown
    current_part = ""
    paragraphs = combined_responses.split('\n\n')

    for paragraph in paragraphs:
        if paragraph.startswith('*') and current_part and len(current_part) + len(paragraph) + 2 > max_length:
            # Начало новой главы, сохраняем предыдущую часть
            messages.append(current_part)
            current_part = paragraph
        elif len(current_part) + len(paragraph) + 2 > max_length:
            # Превышение лимита, сохраняем текущую часть
            messages.append(current_part)
            current_part = paragraph
        else:
            # Добавляем абзац к текущей части
            if current_part:
                current_part += '\n\n' + paragraph
            else:
                current_part = paragraph

    # Добавляем последнюю часть, если она не пуста
    if current_part:
        messages.append(current_part)

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

                    # Отправляем сообщения, проверяя возможность редактирования
                    if messages:
                        try:
                            # Пробуем отредактировать первое сообщение
                            query.edit_message_text(messages[0], parse_mode='Markdown')
                        except Exception as e:
                            # Если редактирование не удалось, отправляем как новое сообщение
                            logger.warning(f"Не удалось отредактировать сообщение: {e}")
                            query.message.reply_text(messages[0], parse_mode='Markdown')

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

    # Парсим правильный ответ из оригинального текста вопроса
    try:
        correct_answer_match = re.search(r"Правильный ответ:\s*(\d+)", original_questions[current_question])
        if correct_answer_match:
            correct_answer = correct_answer_match.group(1)
        else:
            raise ValueError("Формат правильного ответа не найден")
    except (IndexError, ValueError) as e:
        logger.error(f"Ошибка при обработке ответа пользователя {user_id}: {e}")
        update.message.reply_text(
            "Ошибка в формате вопросов. Попробуй начать тест заново, нажав 'Пройти тест'.", 
            reply_markup=main_menu()
        )
        return TOPIC

    # Проверяем ответ пользователя
    if user_answer == correct_answer:
        context.user_data['score'] = context.user_data.get('score', 0) + 1
        sent_msg = update.message.reply_text("✅ Правильно!")
        save_message_id(update, context, sent_msg.message_id)
        logger.info(f"Пользователь {user_id} ответил верно на вопрос {current_question+1}")
    else:
        # Не показываем правильный ответ
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

        # Оценка усвоенного материала
        if percentage >= 90:
            assessment = "🏆 Отлично! Ты прекрасно усвоил материал."
        elif percentage >= 70:
            assessment = "👍 Хорошо! Ты неплохо усвоил материал, но есть над чем поработать."
        elif percentage >= 50:
            assessment = "👌 Удовлетворительно. Рекомендуется повторить материал."
        else:
            assessment = "📚 Неудовлетворительно. Тебе стоит изучить тему заново."

        update.message.reply_text(
            f"🎯 Тест завершен! Ты ответил правильно на {score} из {total_questions} вопросов ({percentage:.1f}%).\n\n{assessment}\n\n"
            "Выбери следующее действие:",
            reply_markup=main_menu()
        )
        logger.info(f"Пользователь {user_id} завершил тест с результатом {score}/{total_questions} ({percentage:.1f}%)")
        return TOPIC

# Оптимизированная функция для обработки сообщений в режиме беседы
def handle_conversation(update, context):
    """
    Обрабатывает сообщения пользователя в режиме беседы с оптимизацией.

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

    # Проверяем, относится ли сообщение к истории России - используем кэширование
    check_prompt = f"Проверь, относится ли следующее сообщение к истории России: \"{user_message}\". Ответь только 'да' или 'нет'."

    # Отправляем индикатор набора текста
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)

    try:
        # Проверяем тему сообщения с малым лимитом токенов для ускорения
        is_history_related = ask_grok(check_prompt, max_tokens=50, temp=0.1).lower().strip()
        logger.info(f"Проверка темы сообщения пользователя {user_id}: {is_history_related}")

        if 'да' in is_history_related:
            # Если сообщение относится к истории России - более детальный ответ
            prompt = f"Пользователь задал вопрос на тему истории России: \"{user_message}\"\n\n" \
                    "Ответь на этот вопрос, опираясь на исторические факты. " \
                    "Будь информативным, но кратким."
        else:
            # Если сообщение не относится к истории России - краткий отказ
            prompt = f"Пользователь задал вопрос не относящийся к истории России: \"{user_message}\"\n\n" \
                    "Вежливо объясни, что ты специализируешься только на истории России, и " \
                    "предложи задать вопрос, связанный с историей России. Приведи пример возможного вопроса."

        # Получаем ответ от API с индикатором набора
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

# Улучшенная функция для очистки истории чата
def clear_chat_history(update, context):
    """
    Очищает историю чата, удаляя предыдущие сообщения бота.
    Улучшенная версия с повышенной производительностью и защитой от ошибок.

    Args:
        update (telegram.Update): Объект обновления Telegram
        context (telegram.ext.CallbackContext): Контекст разговора
    """
    if not update or not update.effective_chat:
        return
        
    try:
        # Получаем ID чата
        chat_id = update.effective_chat.id

        # Получаем список сохраненных ID сообщений
        message_ids = context.user_data.get('previous_messages', [])

        if not message_ids:
            return

        # Удаляем дубликаты и устаревшие сообщения (старше 48 часов)
        # Telegram API не позволяет удалять сообщения старше 48 часов
        import time
        current_time = int(time.time())
        message_ids = list(set(message_ids))  # Удаление дубликатов
        
        # Определяем максимальное количество сообщений для удаления за один запрос
        max_messages = min(len(message_ids), 100)
        
        # Используем многопоточность для асинхронного удаления сообщений
        import threading
        
        def delete_messages_batch(msgs_batch):
            nonlocal count_deleted
            for msg_id in msgs_batch:
                try:
                    context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    count_deleted += 1
                except telegram.error.TelegramError as te:
                    # Более точная обработка ошибок Telegram
                    if "message to delete not found" in str(te).lower():
                        # Сообщение уже удалено или недоступно
                        pass
                    elif "message can't be deleted" in str(te).lower():
                        # Сообщение не может быть удалено по правам доступа
                        pass
                    else:
                        logger.warning(f"Telegram error при удалении сообщения {msg_id}: {te}")
                except Exception as e:
                    # Другие ошибки
                    pass
        
        # Удаляем сообщения асинхронно в нескольких потоках
        count_deleted = 0
        batch_size = 10  # Оптимальный размер пакета для Telegram API
        threads = []
        
        # Создаем и запускаем потоки для удаления сообщений
        for i in range(0, min(max_messages, len(message_ids)), batch_size):
            batch = message_ids[i:i+batch_size]
            thread = threading.Thread(target=delete_messages_batch, args=(batch,))
            thread.daemon = True  # Фоновый поток
            threads.append(thread)
            thread.start()
        
        # Ждем завершения всех потоков, но не более 3 секунд
        for thread in threads:
            thread.join(timeout=0.5)
        
        # Очищаем список предыдущих сообщений
        context.user_data['previous_messages'] = []

        if count_deleted > 0:
            logger.info(f"История чата очищена для пользователя {chat_id}: удалено {count_deleted} сообщений")
    except Exception as e:
        logger.error(f"Ошибка при очистке истории чата: {str(e)}")

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
        logger.info("Запуск бота истории России...")
        print("Начинаю запуск бота истории России...")

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

        # Инициализируем бота и диспетчер с оптимизированными настройками
        updater = Updater(TELEGRAM_TOKEN, use_context=True, workers=4)  # Увеличиваем количество рабочих потоков
        dp = updater.dispatcher

        # Создаем ConversationHandler для управления диалогом
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
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

        # Запускаем бота с оптимизированными параметрами
        logger.info("Бот успешно запущен")
        print("Бот успешно запущен")
        updater.start_polling(timeout=30, read_latency=2.0, drop_pending_updates=True)
        updater.idle()

    except Exception as e:
        log_error(e, "Критическая ошибка при запуске бота")
        logger.critical(f"Бот не был запущен из-за критической ошибки: {e}")
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == '__main__':
    main()