
import os
import json
import time
import logging
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(f"logs/bot_log_{time.strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Получение токенов из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Создание директории для логов, если она не существует
os.makedirs('logs', exist_ok=True)

# Инициализация кэша API
CACHE_FILE = "api_cache.json"

def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки кэша: {e}")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
    except Exception as e:
        logger.error(f"Ошибка сохранения кэша: {e}")

def get_cached_response(prompt, ttl=86400):  # TTL в секундах (по умолчанию 24 часа)
    cache = load_cache()
    cache_key = hash_string(prompt)
    
    if cache_key in cache:
        entry = cache[cache_key]
        # Проверяем, не истекло ли время жизни кэша
        if time.time() - entry.get("last_accessed", 0) < entry.get("ttl", ttl):
            # Обновляем время последнего доступа
            cache[cache_key]["last_accessed"] = time.time()
            save_cache(cache)
            return entry["value"]
    
    return None

def cache_response(prompt, response, ttl=86400):
    cache = load_cache()
    cache_key = hash_string(prompt)
    
    cache[cache_key] = {
        "value": response,
        "last_accessed": time.time(),
        "created_at": time.time(),
        "ttl": ttl
    }
    
    save_cache(cache)

def hash_string(text):
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_history_response(prompt):
    try:
        # Проверяем кэш перед запросом к API
        cached_response = get_cached_response(prompt)
        if cached_response:
            return cached_response
        
        # Подготовка запроса к Gemini с проверкой на историческую тематику
        context_prompt = (
            "Ты исторический помощник, специализирующийся на истории России. "
            "Отвечай только на вопросы, связанные с историей России. "
            "Если вопрос не относится к истории России, вежливо объясни, что "
            "ты можешь отвечать только на исторические вопросы о России."
        )
        
        # Полный запрос с контекстом
        full_prompt = f"{context_prompt}\n\nЗапрос пользователя: {prompt}"
        
        # Делаем запрос к API
        response = model.generate_content(full_prompt)
        
        # Извлекаем текст ответа
        response_text = response.text
        
        # Кэшируем результат
        cache_response(prompt, response_text)
        
        return response_text
    
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {str(e)}")
        return "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("Темы по истории России", callback_data='history_topics')],
        [InlineKeyboardButton("О проекте", callback_data='about')],
        [InlineKeyboardButton("Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "👋 Добро пожаловать в Исторического помощника!\n\n"
        "Я специализируюсь на истории России и могу ответить на ваши вопросы "
        "по этой теме. Используйте меню ниже или просто напишите свой вопрос.",
        reply_markup=reply_markup
    )

def button_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'history_topics':
        response = generate_history_response("Предложи список из 30 ключевых тем по истории России, интересных для изучения")
        
        # Создаем кнопки для выбора темы (первые 5 тем)
        topics = [topic.strip() for topic in response.split('\n') if topic.strip() and not topic.strip().startswith('Вот')]
        
        keyboard = []
        for i, topic in enumerate(topics[:5]):
            # Убираем номера, если они есть
            clean_topic = topic
            if '.' in topic[:3]:
                clean_topic = topic.split('.', 1)[1].strip()
            keyboard.append([InlineKeyboardButton(clean_topic, callback_data=f'topic_{i+1}')])
        
        keyboard.append([InlineKeyboardButton("Назад в меню", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            text="Выберите тему для изучения:",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith('topic_'):
        topic_id = int(query.data.split('_')[1])
        response = generate_history_response("Предложи список из 30 ключевых тем по истории России, интересных для изучения")
        topics = [topic.strip() for topic in response.split('\n') if topic.strip() and not topic.strip().startswith('Вот')]
        
        if topic_id <= len(topics):
            selected_topic = topics[topic_id-1]
            if '.' in selected_topic[:3]:
                selected_topic = selected_topic.split('.', 1)[1].strip()
            
            # Получаем подробную информацию о выбранной теме
            topic_info = generate_history_response(f"Расскажи о теме '{selected_topic}' в истории России")
            
            keyboard = [
                [InlineKeyboardButton("Узнать больше", callback_data=f'more_{topic_id}')],
                [InlineKeyboardButton("Тестирование по теме", callback_data=f'test_{topic_id}')],
                [InlineKeyboardButton("Назад к темам", callback_data='history_topics')],
                [InlineKeyboardButton("Главное меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                text=f"*{selected_topic}*\n\n{topic_info[:800]}...",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data.startswith('more_'):
        topic_id = int(query.data.split('_')[1])
        response = generate_history_response("Предложи список из 30 ключевых тем по истории России, интересных для изучения")
        topics = [topic.strip() for topic in response.split('\n') if topic.strip() and not topic.strip().startswith('Вот')]
        
        if topic_id <= len(topics):
            selected_topic = topics[topic_id-1]
            if '.' in selected_topic[:3]:
                selected_topic = selected_topic.split('.', 1)[1].strip()
            
            # Получаем дополнительную информацию
            additional_info = generate_history_response(f"Расскажи подробнее о внешней политике и международном влиянии в контексте темы '{selected_topic}' в истории России")
            
            keyboard = [
                [InlineKeyboardButton("Вернуться к теме", callback_data=f'topic_{topic_id}')],
                [InlineKeyboardButton("Главное меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                text=f"*{selected_topic}: дополнительная информация*\n\n{additional_info[:800]}...",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data.startswith('test_'):
        topic_id = int(query.data.split('_')[1])
        response = generate_history_response("Предложи список из 30 ключевых тем по истории России, интересных для изучения")
        topics = [topic.strip() for topic in response.split('\n') if topic.strip() and not topic.strip().startswith('Вот')]
        
        if topic_id <= len(topics):
            selected_topic = topics[topic_id-1]
            if '.' in selected_topic[:3]:
                selected_topic = selected_topic.split('.', 1)[1].strip()
            
            # Генерируем тест по выбранной теме
            test_prompt = f"Придумай 15 вопросов с вариантами ответа по теме \"{selected_topic}\" в истории России. Для каждого вопроса укажи правильный ответ."
            test_questions = generate_history_response(test_prompt)
            
            keyboard = [
                [InlineKeyboardButton("Вернуться к теме", callback_data=f'topic_{topic_id}')],
                [InlineKeyboardButton("Главное меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Разбиваем тест на части, если он слишком длинный
            if len(test_questions) > 4000:
                parts = [test_questions[i:i+4000] for i in range(0, len(test_questions), 4000)]
                query.edit_message_text(
                    text=f"*Тестирование по теме: {selected_topic}*\n\nЧасть 1:\n\n{parts[0]}...",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                # Отправляем остальные части отдельными сообщениями
                for i, part in enumerate(parts[1:], 2):
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Часть {i}:\n\n{part}",
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                query.edit_message_text(
                    text=f"*Тестирование по теме: {selected_topic}*\n\n{test_questions}",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
    
    elif query.data == 'about':
        keyboard = [[InlineKeyboardButton("Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            text=(
                "*О проекте*\n\n"
                "Этот бот использует модель Gemini от Google для ответов на вопросы по истории России. "
                "Он предоставляет информацию о ключевых событиях, личностях и периодах "
                "российской истории.\n\n"
                "Бот имеет систему кэширования для быстрых ответов на повторяющиеся вопросы "
                "и может генерировать тесты для проверки знаний."
            ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == 'help':
        keyboard = [[InlineKeyboardButton("Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            text=(
                "*Как пользоваться ботом:*\n\n"
                "1. Просто задайте вопрос по истории России\n"
                "2. Используйте кнопку 'Темы по истории России' для выбора интересующих тем\n"
                "3. Для каждой темы доступна подробная информация и тесты\n\n"
                "Примеры вопросов:\n"
                "• Когда была Куликовская битва?\n"
                "• Расскажи о Петре I\n"
                "• Что такое Смутное время?\n"
                "• Причины революции 1917 года"
            ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("Темы по истории России", callback_data='history_topics')],
            [InlineKeyboardButton("О проекте", callback_data='about')],
            [InlineKeyboardButton("Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            text=(
                "👋 Добро пожаловать в Исторического помощника!\n\n"
                "Я специализируюсь на истории России и могу ответить на ваши вопросы "
                "по этой теме. Используйте меню ниже или просто напишите свой вопрос."
            ),
            reply_markup=reply_markup
        )

def handle_message(update: Update, context: CallbackContext) -> None:
    """Обработчик текстовых сообщений"""
    user_text = update.message.text
    
    # Проверка, не является ли сообщение командой
    if user_text.startswith('/'):
        update.message.reply_text("Неизвестная команда. Используйте /start для начала работы.")
        return
    
    # Отправляем сообщение "печатает..."
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Генерируем ответ
    response = generate_history_response(user_text)
    
    # Создаем клавиатуру для дополнительных действий
    keyboard = [
        [InlineKeyboardButton("Расширенный ответ", callback_data='extended_' + hash_string(user_text)[:10])],
        [InlineKeyboardButton("Меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем ответ
    update.message.reply_text(
        response,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def error_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")
    
    try:
        # Если возможно, отправляем сообщение пользователю
        if update and update.effective_chat:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

def main() -> None:
    """Основная функция запуска бота"""
    try:
        # Создаем обновление и передаем ему токен бота
        updater = Updater(TELEGRAM_TOKEN)
        
        # Получаем диспетчер для регистрации обработчиков
        dispatcher = updater.dispatcher
        
        # Регистрируем обработчики команд
        dispatcher.add_handler(CommandHandler("start", start))
        
        # Регистрируем обработчик для кнопок
        dispatcher.add_handler(CallbackQueryHandler(button_callback))
        
        # Регистрируем обработчик для текстовых сообщений
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        
        # Регистрируем обработчик ошибок
        dispatcher.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("Бот запущен")
        updater.start_polling()
        
        # Бот работает, пока не нажмем Ctrl-C
        updater.idle()
    
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
