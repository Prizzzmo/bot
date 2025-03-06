import os
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
import requests
from dotenv import load_dotenv


import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import background  # Импортируем модуль Flask-сервера

# Расширенная настройка логирования
log_date = datetime.now().strftime('%Y%m%d')
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Проверяем наличие директории для логов
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Используем RotatingFileHandler для ограничения размера файлов логов
log_file_path = f"{log_dir}/bot_log_{log_date}.log"
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
logger.addHandler(file_handler)
logger.addHandler(console_handler)

print(f"Логирование настроено. Файлы логов будут сохраняться в: {log_file_path}")

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

# Расширенная функция логирования ошибок с комментариями
def log_error(error, additional_info=None):
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


# Добавляем простой механизм кэширования
class SimpleCache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size

    def get(self, key):
        """Получить значение из кэша по ключу"""
        return self.cache.get(key)

    def set(self, key, value):
        """Добавить значение в кэш"""
        # Если кэш переполнен, удаляем случайный элемент
        if len(self.cache) >= self.max_size:
            import random
            random_key = random.choice(list(self.cache.keys()))
            del self.cache[random_key]

        self.cache[key] = value

    def clear(self):
        """Очистить кэш"""
        self.cache.clear()

# Создаем глобальный экземпляр кэша
api_cache = SimpleCache()

# Получаем ключи API из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Используем Google Gemini API

# Состояния для ConversationHandler
TOPIC, CHOOSE_TOPIC, TEST, ANSWER = range(4)

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
            print("Использую кэшированный ответ")
            return cached_response

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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        response_json = response.json()

        # Проверка наличия всех необходимых ключей в ответе
        if "candidates" not in response_json or not response_json["candidates"]:
            print(f"Ответ не содержит 'candidates': {response_json}")
            return "API вернул ответ без содержимого. Возможно, запрос был заблокирован фильтрами безопасности."

        candidate = response_json["candidates"][0]
        if "content" not in candidate:
            print(f"Ответ не содержит 'content': {candidate}")
            return "API вернул неверный формат ответа."

        content = candidate["content"]
        if "parts" not in content or not content["parts"]:
            print(f"Ответ не содержит 'parts': {content}")
            return "API вернул пустой ответ."

        result = content["parts"][0]["text"]

        # Сохраняем результат в кэш
        if use_cache:
            api_cache.set(cache_key, result)

        return result

    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"{error_type}: {error_msg}")

        if isinstance(e, requests.exceptions.HTTPError) and hasattr(e, 'response'):
            print(f"Статус код: {e.response.status_code}")
            print(f"Ответ сервера: {e.response.text}")
            return f"Ошибка HTTP при запросе к Google Gemini ({e.response.status_code}): {error_msg}"

        error_messages = {
            "ConnectionError": "Ошибка соединения с API Google Gemini. Проверьте подключение к интернету.",
            "Timeout": "Превышено время ожидания ответа от API Google Gemini.",
            "JSONDecodeError": "Ошибка при обработке ответа от API Google Gemini.",
            "HTTPError": f"Ошибка HTTP при запросе к Google Gemini: {error_msg}"
        }

        return error_messages.get(error_type, f"Неизвестная ошибка при запросе к Google Gemini: {error_msg}")

# Альтернативная функция для Hugging Face (раскомментируйте, если используете Hugging Face)
"""
def ask_grok(prompt):
    url = "https://api-inference.huggingface.co/models/google/flan-t5-large"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": prompt,
        "parameters": {"max_length": 1000}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()[0]["generated_text"]
    except Exception as e:
        return f"Ошибка при запросе к Hugging Face: {e}"
"""

# Функция для создания главного меню
def main_menu():
    keyboard = [
        [InlineKeyboardButton("Выбрать тему", callback_data='topic')],
        [InlineKeyboardButton("Пройти тест", callback_data='test')],
        [InlineKeyboardButton("Завершить", callback_data='cancel')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команда /start (начало работы с ботом)
def start(update, context):
    user = update.message.from_user
    update.message.reply_text(
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "🤖 Я образовательный бот по истории России. С моей помощью вы сможете:\n\n"
        "📚 *Изучать различные исторические темы* — от древних времен до современности\n"
        "✅ *Проходить тесты* для проверки полученных знаний\n"
        "🔍 *Выбирать интересующие темы* из предложенного списка\n"
        "📝 *Предлагать свои темы* для изучения, если не нашли в списке\n\n"
        "Каждая тема подробно раскрывается в 5 главах с информацией об истоках, ключевых событиях, "
        "исторических личностях, международных отношениях и историческом значении.\n\n"
        "❗ *Данный бот создан в качестве учебного пособия.*\n\n"
        "Выберите действие в меню ниже, чтобы начать:",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )
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
    for line in topics_text.split('\n'):
        line = line.strip()
        if not line or len(line) <= 1:
            continue

        # Извлекаем текст темы после номера или двоеточия
        if '.' in line or ':' in line:
            parts = line.split('.', 1) if '.' in line else line.split(':', 1)
            if len(parts) > 1:
                topic_text = parts[1].strip()
                if topic_text:
                    filtered_topics.append(topic_text)
        # Если нет стандартного разделителя, проверяем наличие номера в начале
        elif line[0].isdigit():
            # Ищем первый не цифровой и не разделительный символ
            i = 1
            while i < len(line) and (line[i].isdigit() or line[i] in ' \t.):'):
                i += 1
            if i < len(line):
                topic_text = line[i:].strip()
                if topic_text:
                    filtered_topics.append(topic_text)
        # Иначе берем строку как есть
        else:
            filtered_topics.append(line)

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

    # Добавляем кнопку для ввода своей темы
    keyboard.append([InlineKeyboardButton("Своя тема", callback_data='custom_topic')])

    return InlineKeyboardMarkup(keyboard)

# Обработка нажатий на кнопки меню
def button_handler(update, context):
    query = update.callback_query
    query.answer()  # Подтверждаем нажатие кнопки

    if query.data == 'back_to_menu':
        query.edit_message_text(
            "Выберите действие в меню ниже:",
            reply_markup=main_menu()
        )
        return TOPIC
    elif query.data == 'topic':
        # Генерируем список тем с помощью ИИ
        prompt = "Составь список из 30 ключевых тем по истории России, которые могут быть интересны для изучения. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
        try:
            query.edit_message_text("Загружаю список тем истории России...")
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
        except Exception as e:
            query.edit_message_text(f"Произошла ошибка при генерации списка тем: {e}. Попробуй еще раз.", reply_markup=main_menu())
        return CHOOSE_TOPIC
    elif query.data == 'test':
        topic = context.user_data.get('current_topic', None)
        if not topic:
            query.edit_message_text(
                "Сначала выбери тему, нажав на кнопку 'Выбрать тему'.",
                reply_markup=main_menu()
            )
            return TOPIC

        # Генерируем тест из вопросов
        query.edit_message_text(f"🧠 Генерирую тест по теме: *{topic}*...", parse_mode='Markdown')

        # Используем параметры для возможности генерации большего текста
        prompt = f"Составь 10 вопросов с вариантами ответа (1, 2, 3, 4) по теме '{topic}' в истории России. После каждого вопроса с вариантами ответов укажи правильный ответ в формате 'Правильный ответ: <цифра>'. Каждый вопрос должен заканчиваться строкой '---'."
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

            query.edit_message_text(
                f"📝 *Тест по теме: {topic}*\n\nНачинаем тест из {len(valid_questions)} вопросов! Вот первый вопрос:",
                parse_mode='Markdown'
            )
            query.message.reply_text(valid_questions[0])
            query.message.reply_text(
                "Напиши цифру правильного ответа (1, 2, 3 или 4).", 
                reply_markup=reply_markup
            )
        except Exception as e:
            query.edit_message_text(
                f"Произошла ошибка при генерации вопросов: {e}. Попробуй еще раз.", 
                reply_markup=main_menu()
            )
        return ANSWER
    elif query.data == 'continue_reading':
        # Отображаем вторую часть текста
        part2 = context.user_data.get('topic_part2', "Продолжение не найдено.")
        query.edit_message_text(part2)
        query.message.reply_text("Выбери следующее действие:", reply_markup=main_menu())
        return TOPIC
    elif query.data == 'more_topics':
        # Генерируем новый список тем с помощью ИИ
        # Добавляем случайный параметр для получения разных тем
        import random
        random_seed = random.randint(1, 1000)
        prompt = f"Составь список из 30 новых и оригинальных тем по истории России, которые могут быть интересны для изучения. Сосредоточься на темах {random_seed}. Выбери темы, отличные от стандартных и ранее предложенных. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
        try:
            query.edit_message_text("🔄 Генерирую новый список уникальных тем по истории России...")
            topics = ask_grok(prompt)

            # Очищаем и форматируем полученные темы
            filtered_topics = []
            for line in topics.split('\n'):
                line = line.strip()
                if line:
                    # Извлекаем текст темы после номера или двоеточия, если они есть
                    if ('.' in line or ':' in line):
                        parts = line.split('.', 1) if '.' in line else line.split(':', 1)
                        if len(parts) > 1:
                            topic_text = parts[1].strip()
                            if topic_text:  # Проверяем, что текст темы не пустой
                                filtered_topics.append(topic_text)
                    # Если нет стандартного разделителя, проверяем наличие номера в начале
                    elif line[0].isdigit() and len(line) > 1:
                        # Ищем первый не цифровой и не разделительный символ
                        i = 1
                        while i < len(line) and (line[i].isdigit() or line[i] in ' \t.):'):
                            i += 1
                        if i < len(line):
                            topic_text = line[i:].strip()
                            if topic_text:  # Проверяем, что текст темы не пустой
                                filtered_topics.append(topic_text)
                    # Если все остальные методы не сработали, берем строку как есть
                    elif len(line) > 1:
                        filtered_topics.append(line)

            # Ограничиваем до 30 тем
            filtered_topics = filtered_topics[:30]

            context.user_data['topics'] = filtered_topics
            keyboard = []

            # Создаем красивые кнопки с темами
            for i, topic in enumerate(filtered_topics, 1):
                # Проверяем, что тема не пустая
                if topic and len(topic.strip()) > 0:
                    # Ограничиваем длину темы в кнопке
                    display_topic = topic[:30] + '...' if len(topic) > 30 else topic
                    keyboard.append([InlineKeyboardButton(f"{i}. {display_topic}", callback_data=f'topic_{i}')])
                else:
                    # Если тема пустая, добавляем заполнитель
                    keyboard.append([InlineKeyboardButton(f"{i}. [Тема не определена]", callback_data=f'topic_{i}')])

            # Добавляем только кнопку для ввода своей темы
            bottom_row = [InlineKeyboardButton("Своя тема", callback_data='custom_topic')]
            keyboard.append(bottom_row)

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                "📚 *Новые темы по истории России*\n\nВыберите одну из только что сгенерированных тем или введите свою:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            query.edit_message_text(f"Произошла ошибка при генерации списка тем: {e}. Попробуй еще раз.", reply_markup=main_menu())
        return CHOOSE_TOPIC
    elif query.data == 'end_test' or query.data == 'cancel':
        if query.data == 'end_test':
            query.edit_message_text("Тест завершен досрочно. Возвращаемся в главное меню.")
            query.message.reply_text("Выберите действие:", reply_markup=main_menu())
            return TOPIC
        else:
            query.edit_message_text("Действие отменено. Нажми /start, чтобы начать заново.")
            return ConversationHandler.END

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

        response = ask_grok(prompt)
        # Добавляем заголовок главы перед текстом
        chapter_response = f"*{chapter_titles[i-1]}*\n\n{response}"
        all_responses.append(chapter_response)

    # Объединяем ответы с разделителями
    combined_responses = "\n\n" + "\n\n".join(all_responses)

    # Разделяем длинный текст на части для отправки в Telegram (макс. 4000 символов)
    messages = []
    paragraphs = combined_responses.split('\n\n')
    current_message = ""

    for paragraph in paragraphs:
        # Если добавление абзаца не превысит лимит
        if len(current_message) + len(paragraph) + 2 < 4000:
            if current_message:
                current_message += '\n\n' + paragraph
            else:
                current_message = paragraph
        else:
            # Сохраняем текущее сообщение и начинаем новое
            messages.append(current_message)
            current_message = paragraph

    # Добавляем последнее сообщение
    if current_message:
        messages.append(current_message)

    return messages

# Обработка выбора темы из списка или ввода своей темы
def choose_topic(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'custom_topic':
        query.edit_message_text("Напиши тему по истории России, которую ты хочешь изучить.")
        return CHOOSE_TOPIC
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
            else:
                query.edit_message_text(f"Ошибка: Тема с индексом {topic_index+1} не найдена. Попробуйте выбрать другую тему.", reply_markup=main_menu())
        except Exception as e:
            print(f"Ошибка при обработке темы: {e}")
            query.edit_message_text(f"Произошла ошибка при загрузке темы: {e}. Попробуй еще раз.", reply_markup=main_menu())
        return TOPIC

# Обработка ввода своей темы
def handle_custom_topic(update, context):
    topic = update.message.text
    context.user_data['current_topic'] = topic

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
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {e}. Попробуй еще раз.", reply_markup=main_menu())
    return TOPIC

# Обработка ответов на тест
def handle_answer(update, context):
    user_answer = update.message.text.strip()
    questions = context.user_data['questions']
    current_question = context.user_data['current_question']

    # Парсим правильный ответ из текста вопроса
    try:
        correct_answer = questions[current_question].split("Правильный ответ: ")[1][0]
    except IndexError:
        update.message.reply_text("Ошибка в формате вопросов. Попробуй начать тест заново, нажав 'Пройти тест'.", reply_markup=main_menu())
        return TOPIC

    if user_answer == correct_answer:
        context.user_data['score'] += 1
        update.message.reply_text("Правильно!")
    else:
        update.message.reply_text(f"Неправильно. Правильный ответ: {correct_answer}")

    context.user_data['current_question'] += 1
    if context.user_data['current_question'] < len(questions):
        update.message.reply_text(f"Вопрос {context.user_data['current_question'] + 1} из {len(questions)}:")
        update.message.reply_text(questions[context.user_data['current_question']])

        # Создаем клавиатуру с кнопкой для завершения теста
        keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Напиши цифру правильного ответа (1, 2, 3 или 4).", reply_markup=reply_markup)
        return ANSWER
    else:
        score = context.user_data['score']
        total_questions = len(questions)
        percentage = (score / total_questions) * 100
        # Оценка усвоенного материала
        if percentage >= 90:
            assessment = "Отлично! Ты прекрасно усвоил материал."
        elif percentage >= 70:
            assessment = "Хорошо! Ты неплохо усвоил материал, но есть над чем поработать."
        elif percentage >= 50:
            assessment = "Удовлетворительно. Рекомендуется повторить материал."
        else:
            assessment = "Неудовлетворительно. Тебе стоит изучить тему заново."
        update.message.reply_text(
            f"Тест завершен! Ты ответил правильно на {score} из {total_questions} вопросов ({percentage:.2f}%).\n{assessment}\n"
            "Выбери следующее действие:",
            reply_markup=main_menu()
        )
        return TOPIC

# Основная функция для запуска бота
def main():
    try:
        logger.info("Запуск бота и веб-сервера логов...")
        print("Начинаю запуск бота и веб-сервера логов...")
        
        # Проверка наличия необходимых модулей
        try:
            import flask
            print(f"Flask установлен, версия: {flask.__version__}")
            logger.info(f"Flask установлен, версия: {flask.__version__}")
        except ImportError:
            print("Flask не установлен, пытаюсь установить...")
            logger.warning("Flask не установлен, пытаюсь установить...")
            import subprocess
            try:
                subprocess.run(['pip', 'install', 'flask'], check=True)
                print("Flask успешно установлен")
                logger.info("Flask успешно установлен")
            except Exception as e:
                print(f"Ошибка при установке Flask: {e}")
                logger.error(f"Ошибка при установке Flask: {e}")

        # Запускаем Flask-сервер для отображения логов в отдельном потоке
        logger.info("Запуск Flask-сервера для отображения логов...")
        flask_thread = background.start_flask_server()
        logger.info(f"Flask-сервер запущен на http://0.0.0.0:8080")

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

        updater = Updater(TELEGRAM_TOKEN, use_context=True)
        dp = updater.dispatcher

        # Создаем ConversationHandler для управления диалогом
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                TOPIC: [
                    CallbackQueryHandler(button_handler)
                ],
                CHOOSE_TOPIC: [
                    CallbackQueryHandler(choose_topic),
                    MessageHandler(Filters.text & ~Filters.command, handle_custom_topic)
                ],
                TEST: [
                    CallbackQueryHandler(button_handler)
                ],
                ANSWER: [
                    MessageHandler(Filters.text & ~Filters.command, handle_answer),
                    CallbackQueryHandler(button_handler)  # Добавляем обработчик для кнопки завершения теста
                ]
            },
            fallbacks=[CommandHandler('start', start)]
        )

        # Добавляем обработчик ошибок
        def error_handler(update, context):
            """Обработчик ошибок: записывает их в журнал с комментариями и информирует пользователя"""
            error = context.error
            error_type = type(error).__name__

            # Используем расширенное логирование ошибок
            additional_info = f"в обновлении {update}" if update else ""
            log_error(error, additional_info)

            if update and update.effective_message:
                # Формируем информативное сообщение для пользователя
                error_message = f"Произошла ошибка: {error}"

                # Добавляем пользователю пояснение для известных типов ошибок
                if error_type in ERROR_DESCRIPTIONS:
                    error_message += f"\n{ERROR_DESCRIPTIONS[error_type]}"

                update.effective_message.replytext(error_message)

        dp.add_error_handler(error_handler)
        dp.add_handler(conv_handler)

        # Запускаем бота
        logger.info("Бот успешно запущен")
        updater.start_polling()
        updater.idle()

    except Exception as e:
        log_error(e, "Критическая ошибка при запуске бота")
        logger.critical("Бот не был запущен из-за критической ошибки")

if __name__ == '__main__':
    main()