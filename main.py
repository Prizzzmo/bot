
import os
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем ключи API из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Используем Google Gemini API

# Состояния для ConversationHandler
TOPIC, CHOOSE_TOPIC, TEST, ANSWER = range(4)

# Функция для запросов к Google Gemini API
def ask_grok(prompt):
    # Упрощаем запрос для снижения вероятности ошибок
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Проверка на ошибки HTTP
        
        # Вывод для отладки
        print("Ответ от API успешно получен")
        
        # Проверяем структуру ответа
        response_json = response.json()
        
        # Вывод для отладки
        print(f"Структура ответа: {response_json.keys()}")
        
        if "candidates" not in response_json or not response_json["candidates"]:
            print(f"Ответ не содержит 'candidates': {response_json}")
            return "API вернул ответ без содержимого. Возможно, запрос был заблокирован фильтрами безопасности."
            
        if "content" not in response_json["candidates"][0]:
            print(f"Ответ не содержит 'content': {response_json['candidates'][0]}")
            return "API вернул неверный формат ответа."
            
        if "parts" not in response_json["candidates"][0]["content"] or not response_json["candidates"][0]["content"]["parts"]:
            print(f"Ответ не содержит 'parts': {response_json['candidates'][0]['content']}")
            return "API вернул пустой ответ."
            
        return response_json["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Ошибка: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Статус код: {e.response.status_code}")
            print(f"Ответ сервера: {e.response.text}")
        return f"Ошибка HTTP при запросе к Google Gemini: {e}"
    except requests.exceptions.ConnectionError as e:
        print(f"Ошибка соединения: {e}")
        return "Ошибка соединения с API Google Gemini. Проверьте подключение к интернету."
    except requests.exceptions.Timeout as e:
        print(f"Ошибка таймаута: {e}")
        return "Превышено время ожидания ответа от API Google Gemini."
    except ValueError as e:
        print(f"Ошибка при разборе JSON: {e}")
        return "Ошибка при обработке ответа от API Google Gemini."
    except Exception as e:
        print(f"Неожиданная ошибка API: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Ответ сервера: {e.response.text}")
        return f"Неизвестная ошибка при запросе к Google Gemini: {e}"

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
        f"Привет, {user.first_name}! Я бот, который поможет тебе изучить историю России. "
        "Выбери действие в меню ниже:",
        reply_markup=main_menu()
    )
    return TOPIC

# Обработка нажатий на кнопки меню
def button_handler(update, context):
    query = update.callback_query
    query.answer()  # Подтверждаем нажатие кнопки

    if query.data == 'topic':
        # Генерируем список тем с помощью ИИ
        prompt = "Составь список из 10 популярных тем по истории России, которые могут быть интересны для изучения. Перечисли их в виде нумерованного списка."
        try:
            topics = ask_grok(prompt)
            context.user_data['topics'] = topics.split('\n')  # Сохраняем темы в виде списка
            keyboard = []
            for i, topic in enumerate(context.user_data['topics'], 1):
                keyboard.append([InlineKeyboardButton(f"{i}. {topic}", callback_data=f'topic_{i}')])
            keyboard.append([InlineKeyboardButton("Ввести свою тему", callback_data='custom_topic')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                "Выбери тему из списка или введи свою:",
                reply_markup=reply_markup
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
        # Генерируем 10 вопросов с вариантами ответа (уменьшаем количество до 10 для лучшей работы с API)
        prompt = f"Составь 10 вопросов с вариантами ответа (a, b, c, d) по теме '{topic}' в истории России. После каждого вопроса с вариантами ответов укажи правильный ответ в формате 'Правильный ответ: <буква>'. Каждый вопрос должен заканчиваться строкой '---'."
        try:
            questions = ask_grok(prompt)
            context.user_data['questions'] = questions.split('---')  # Разделяем вопросы
            context.user_data['current_question'] = 0
            context.user_data['score'] = 0
            query.edit_message_text("Начинаем тест из 10 вопросов! Вот первый вопрос:")
            query.message.reply_text(context.user_data['questions'][0])
            query.message.reply_text("Напиши букву правильного ответа (a, b, c или d).")
        except Exception as e:
            query.edit_message_text(f"Произошла ошибка при генерации вопросов: {e}. Попробуй еще раз.", reply_markup=main_menu())
        return ANSWER
    elif query.data == 'cancel':
        query.edit_message_text("Действие отменено. Нажми /start, чтобы начать заново.")
        return ConversationHandler.END

# Обработка выбора темы из списка или ввода своей темы
def choose_topic(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'custom_topic':
        query.edit_message_text("Напиши тему по истории России, которую ты хочешь изучить.")
        return CHOOSE_TOPIC
    elif query.data.startswith('topic_'):
        topic_index = int(query.data.split('_')[1]) - 1
        topic = context.user_data['topics'][topic_index].split('. ', 1)[1]  # Убираем номер из темы
        context.user_data['current_topic'] = topic
        prompt = f"Расскажи подробно о {topic} в истории России. Используй простой и понятный язык."
        try:
            response = ask_grok(prompt)
            query.edit_message_text(response)
            query.message.reply_text("Выбери следующее действие:", reply_markup=main_menu())
        except Exception as e:
            query.edit_message_text(f"Произошла ошибка: {e}. Попробуй еще раз.", reply_markup=main_menu())
        return TOPIC

# Обработка ввода своей темы
def handle_custom_topic(update, context):
    topic = update.message.text
    context.user_data['current_topic'] = topic
    prompt = f"Расскажи подробно о {topic} в истории России. Используй простой и понятный язык."
    try:
        response = ask_grok(prompt)
        update.message.reply_text(response)
        update.message.reply_text("Выбери следующее действие:", reply_markup=main_menu())
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {e}. Попробуй еще раз.", reply_markup=main_menu())
    return TOPIC

# Обработка ответов на тест
def handle_answer(update, context):
    user_answer = update.message.text.lower()
    questions = context.user_data['questions']
    current_question = context.user_data['current_question']
    
    # Парсим правильный ответ из текста вопроса
    try:
        correct_answer = questions[current_question].split("Правильный ответ: ")[1][0].lower()
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
        update.message.reply_text("Напиши букву правильного ответа (a, b, c или d).")
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
                MessageHandler(Filters.text & ~Filters.command, handle_answer)
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    dp.add_handler(conv_handler)

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
