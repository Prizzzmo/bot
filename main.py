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
            topics = ask_grok(prompt)

            # Очищаем и форматируем полученные темы
            filtered_topics = []
            for line in topics.split('\n'):
                line = line.strip()
                if line and ('.' in line or ':' in line):
                    # Извлекаем текст темы после номера или двоеточия
                    parts = line.split('.', 1) if '.' in line else line.split(':', 1)
                    if len(parts) > 1:
                        filtered_topics.append(parts[1].strip())

            # Если после фильтрации не осталось тем, берем исходные строки
            if not filtered_topics:
                filtered_topics = [line.strip() for line in topics.split('\n') if line.strip()]

            # Ограничиваем до 30 тем
            filtered_topics = filtered_topics[:30]

            context.user_data['topics'] = filtered_topics
            keyboard = []

            # Создаем красивые кнопки с темами
            for i, topic in enumerate(filtered_topics, 1):
                # Ограничиваем длину темы в кнопке
                display_topic = topic[:30] + '...' if len(topic) > 30 else topic
                keyboard.append([InlineKeyboardButton(f"{i}. {display_topic}", callback_data=f'topic_{i}')])

            # Добавляем только кнопку для ввода своей темы
            bottom_row = [InlineKeyboardButton("Своя тема", callback_data='custom_topic')]
            keyboard.append(bottom_row)

            reply_markup = InlineKeyboardMarkup(keyboard)
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
        # Генерируем 10 вопросов с вариантами ответа (уменьшаем количество до 10 для лучшей работы с API)
        prompt = f"Составь 10 вопросов с вариантами ответа (1, 2, 3, 4) по теме '{topic}' в истории России. После каждого вопроса с вариантами ответов укажи правильный ответ в формате 'Правильный ответ: <цифра>'. Каждый вопрос должен заканчиваться строкой '---'."
        try:
            questions = ask_grok(prompt)
            context.user_data['questions'] = questions.split('---')  # Разделяем вопросы
            context.user_data['current_question'] = 0
            context.user_data['score'] = 0
            query.edit_message_text("Начинаем тест из 10 вопросов! Вот первый вопрос:")
            query.message.reply_text(context.user_data['questions'][0])
            query.message.reply_text("Напиши цифру правильного ответа (1, 2, 3 или 4).")
        except Exception as e:
            query.edit_message_text(f"Произошла ошибка при генерации вопросов: {e}. Попробуй еще раз.", reply_markup=main_menu())
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
                if line and ('.' in line or ':' in line):
                    # Извлекаем текст темы после номера или двоеточия
                    parts = line.split('.', 1) if '.' in line else line.split(':', 1)
                    if len(parts) > 1:
                        filtered_topics.append(parts[1].strip())

            # Если после фильтрации не осталось тем, берем исходные строки
            if not filtered_topics:
                filtered_topics = [line.strip() for line in topics.split('\n') if line.strip()]

            # Ограничиваем до 30 тем
            filtered_topics = filtered_topics[:30]

            context.user_data['topics'] = filtered_topics
            keyboard = []

            # Создаем красивые кнопки с темами
            for i, topic in enumerate(filtered_topics, 1):
                # Ограничиваем длину темы в кнопке
                display_topic = topic[:30] + '...' if len(topic) > 30 else topic
                keyboard.append([InlineKeyboardButton(f"{i}. {display_topic}", callback_data=f'topic_{i}')])

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

                # Разбиваем запрос на несколько частей для получения полной информации
                prompts = [
                    f"Расскажи о {topic} в истории России (часть 1). Дай введение и начальную историю. Используй структурированное изложение. Не пиши 'продолжение следует'.",
                    f"Расскажи о {topic} в истории России (часть 2). Опиши основные события и развитие. Не делай вступление, продолжай повествование с основной части. Не пиши 'продолжение следует'.",
                    f"Расскажи о {topic} в истории России (часть 3). Опиши заключительные события, итоги и значение. Не делай вступление, заверши повествование."
                ]

                # Получаем информацию по частям
                all_responses = []
                for i, prompt in enumerate(prompts, 1):
                    query.edit_message_text(f"📝 Загружаю часть {i} из {len(prompts)} по теме: *{topic}*...", parse_mode='Markdown')
                    response = ask_grok(prompt)
                    all_responses.append(response)

                # Объединяем ответы
                combined_responses = "\n\n".join(all_responses)

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

                # Отправляем первое сообщение с тем же ID (edit)
                if messages:
                    query.edit_message_text(messages[0])

                # Отправляем остальные сообщения как новые
                for msg in messages[1:]:
                    query.message.reply_text(msg)

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
    # Разбиваем запрос на несколько частей для получения полной информации
    prompts = [
        f"Расскажи о {topic} в истории России (часть 1). Дай введение и начальную историю. Используй структурированное изложение. Не пиши 'продолжение следует'.",
        f"Расскажи о {topic} в истории России (часть 2). Опиши основные события и развитие. Не делай вступление, продолжай повествование с основной части. Не пиши 'продолжение следует'.",
        f"Расскажи о {topic} в истории России (часть 3). Опиши заключительные события, итоги и значение. Не делай вступление, заверши повествование."
    ]

    try:
        update.message.reply_text(f"📝 Загружаю информацию по теме: *{topic}*...", parse_mode='Markdown')

        # Получаем информацию по частям
        all_responses = []
        for i, prompt in enumerate(prompts, 1):
            update.message.reply_text(f"📝 Загружаю часть {i} из {len(prompts)}...")
            response = ask_grok(prompt)
            all_responses.append(response)

        # Объединяем ответы
        combined_responses = "\n\n".join(all_responses)

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

        # Отправляем все сообщения
        for msg in messages:
            update.message.reply_text(msg)

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

    dp.add_handler(conv_handler)

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()