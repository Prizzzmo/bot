import telegram
import re
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
from telegram.ext import ConversationHandler

class CommandHandlers:
    """Класс для обработки команд и взаимодействий с пользователем"""

    def __init__(self, ui_manager, api_client, message_manager, content_service, logger, config):
        self.ui_manager = ui_manager
        self.api_client = api_client
        self.message_manager = message_manager
        self.content_service = content_service
        self.logger = logger
        self.config = config
        self.history_map = None  # Будет установлено позже

        # Импортируем константы состояний из config
        from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION, MAP
        self.TOPIC = TOPIC
        self.CHOOSE_TOPIC = CHOOSE_TOPIC
        self.TEST = TEST
        self.ANSWER = ANSWER
        self.CONVERSATION = CONVERSATION
        self.MAP = MAP

    def start(self, update, context):
        """
        Обрабатывает команду /start, показывает приветствие и главное меню.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора

        Returns:
            int: Следующее состояние разговора
        """
        user = update.message.from_user
        self.logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")

        # Очищаем историю чата дважды для надежности
        self.message_manager.clear_chat_history(update, context)
        self.message_manager.clear_chat_history(update, context)

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
        self.message_manager.save_message_id(update, context, sent_message.message_id)

        # Отправляем основное меню
        sent_msg = update.message.reply_text(
            "Выберите действие в меню ниже, чтобы начать:",
            reply_markup=self.ui_manager.main_menu()
        )
        self.message_manager.save_message_id(update, context, sent_msg.message_id)
        return self.TOPIC

    def button_handler(self, update, context):
        """
        Обрабатывает нажатия на кнопки меню с оптимизацией.

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
            self.logger.warning(f"Не удалось подтвердить кнопку: {e}")

        user_id = query.from_user.id

        # Очищаем историю чата только один раз для экономии ресурсов
        self.message_manager.clean_all_messages_except_active(update, context)
        
        # Проверяем, нужно ли обрабатывать активные сообщения
        # Кэшируем результат data для предотвращения повторного доступа
        callback_data = query.data

        self.logger.info(f"Пользователь {user_id} нажал кнопку: {query.data}")

        if query.data == 'back_to_menu':
            query.edit_message_text(
                "Выберите действие в меню ниже:",
                reply_markup=self.ui_manager.main_menu()
            )
            return self.TOPIC
        elif query.data == 'project_info':
            # Загружаем информацию о проекте из файла
            try:
                with open('static/presentation.txt', 'r', encoding='utf-8') as file:
                    presentation_text = file.read()
            except Exception as e:
                self.logger.error(f"Ошибка при чтении файла presentation.txt: {e}")
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
                # Создаем клавиатуру с кнопками для первой части
                keyboard_first = [
                    [InlineKeyboardButton("📥 Скачать презентацию в Word", callback_data='download_detailed_presentation')],
                    [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
                ]

                # Отправляем первую часть с редактированием сообщения
                query.edit_message_text(
                    parts[0][:4000],  # Ограничиваем длину для безопасности
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard_first)
                )

                # Отправляем остальные части как новые сообщения
                for i, part in enumerate(parts[1:], 1):
                    # Добавляем кнопки к последней части
                    if i == len(parts[1:]):
                        keyboard_last = [
                            [InlineKeyboardButton("📥 Скачать презентацию в Word", callback_data='download_detailed_presentation')],
                            [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
                        ]
                        sent_msg = query.message.reply_text(
                            part[:4000],  # Ограничиваем длину для безопасности
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(keyboard_last)
                        )
                    else:
                        sent_msg = query.message.reply_text(
                            part[:4000],  # Ограничиваем длину для безопасности
                            parse_mode='Markdown'
                        )
                    # Сохраняем ID сообщения
                    self.message_manager.save_message_id(update, context, sent_msg.message_id)

                self.logger.info(f"Пользователь {user_id} просмотрел информацию о проекте")
            except telegram.error.BadRequest as e:
                self.logger.error(f"Ошибка при отправке информации о проекте: {e}")
                # Отправляем новое сообщение вместо редактирования
                for i, part in enumerate(parts):
                    # Добавляем кнопки к последней части
                    if i == len(parts) - 1:
                        keyboard = [
                            [InlineKeyboardButton("📥 Скачать презентацию в Word", callback_data='download_detailed_presentation')],
                            [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
                        ]
                        sent_msg = query.message.reply_text(
                            part[:4000],  # Ограничиваем длину для безопасности
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    else:
                        sent_msg = query.message.reply_text(
                            part[:4000],  # Ограничиваем длину для безопасности
                            parse_mode='Markdown'
                        )
                    # Сохраняем ID сообщения
                    self.message_manager.save_message_id(update, context, sent_msg.message_id)

            return self.TOPIC
        elif query.data == 'download_detailed_presentation':
            # Обработка кнопки скачивания подробной презентации
            try:
                # Показываем сообщение о подготовке файла
                query.edit_message_text(
                    "⏳ Подготавливаю подробную презентацию в формате Word...",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                )

                # Импортируем функцию для создания DOCX и создаём презентацию
                import sys
                sys.path.append('.')
                from create_presentation_doc import create_presentation_docx

                # Создаем Word документ
                docx_path = create_presentation_docx('detailed_presentation.md', 'История_России_подробная_презентация.docx')

                # Отправляем файл в формате DOCX
                with open(docx_path, 'rb') as docx_file:
                    context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=docx_file,
                        filename='История_России_подробная_презентация.docx',
                        caption="📚 Подробная иллюстрированная презентация бота по истории России в формате Word."
                    )

                # Также отправляем обычный текстовый файл для совместимости
                with open('detailed_presentation.md', 'rb') as md_file:
                    context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=md_file,
                        filename='История_России_подробная_презентация.md',
                        caption="📄 Версия презентации в текстовом формате Markdown."
                    )

                self.logger.info(f"Пользователь {user_id} скачал подробную презентацию в формате Word и текстовом формате")

                # Обновляем сообщение о успешной загрузке
                query.edit_message_text(
                    "✅ Презентация успешно отправлена в двух форматах:\n\n"
                    "1. DOCX (Word) - с иллюстрациями и форматированием\n"
                    "2. Markdown - текстовый формат для удобного просмотра\n\n"
                    "Выберите дальнейшее действие:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                )
            except Exception as e:
                self.logger.error(f"Ошибка при отправке файла презентации: {e}")
                query.edit_message_text(
                    f"К сожалению, произошла ошибка при создании или отправке презентации: {e}. Пожалуйста, попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                )
            return self.TOPIC
        elif query.data == 'history_map':
            # Обработка кнопки интерактивной карты
            user_id = query.from_user.id
            self.logger.info(f"Пользователь {user_id} запросил историческую карту")

            # Создаем клавиатуру для выбора категории событий на карте
            categories = self.history_map.get_categories()
            keyboard = []

            # Добавляем кнопки для каждой категории
            for category in categories:
                keyboard.append([InlineKeyboardButton(f"📍 {category}", callback_data=f'map_category_{category}')])

            # Добавляем кнопку для случайных событий и возврата в меню
            keyboard.append([InlineKeyboardButton("🎲 Случайные события", callback_data='map_random')])
            keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')])

            query.edit_message_text(
                "🗺️ *Интерактивная карта исторических событий*\n\n"
                "Выберите категорию исторических событий для отображения на карте или "
                "посмотрите случайные события из разных периодов истории России.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return self.MAP

        elif query.data.startswith('map_category_'):
            # Обработка выбора категории на карте
            category = query.data[13:]  # map_category_{category}
            user_id = query.from_user.id
            self.logger.info(f"Пользователь {user_id} выбрал категорию карты: {category}")

            # Генерируем URL для просмотра карты с выбранной категорией
            map_url = self.history_map.generate_map_url(category=category)

            # Создаем кнопки для просмотра карты и возврата к выбору категории
            keyboard = [
                [InlineKeyboardButton("🌐 Открыть карту в браузере", url=map_url)],
                [InlineKeyboardButton("⬅️ К выбору категории", callback_data='history_map')],
                [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
            ]

            query.edit_message_text(
                f"📍 *Категория: {category}*\n\n"
                f"Вы выбрали категорию исторических событий: *{category}*\n\n"
                f"Нажмите на кнопку ниже, чтобы открыть интерактивную карту с событиями этой категории.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return self.MAP

        elif query.data == 'map_random':
            # Обработка выбора случайных событий
            user_id = query.from_user.id
            self.logger.info(f"Пользователь {user_id} запросил случайные события на карте")

            # Получаем случайные события
            random_events = self.history_map.get_random_events(5)

            # Генерируем URL для просмотра карты со случайными событиями
            map_url = self.history_map.generate_map_url(events=random_events)

            # Формируем список событий для отображения
            events_list = "\n".join([f"• *{event['title']}* ({event.get('date', 'Дата неизвестна')})" for event in random_events])

            # Создаем кнопки для просмотра карты и возврата к выбору категории
            keyboard = [
                [InlineKeyboardButton("🌐 Открыть карту в браузере", url=map_url)],
                [InlineKeyboardButton("🎲 Другие случайные события", callback_data='map_random')],
                [InlineKeyboardButton("⬅️ К выбору категории", callback_data='history_map')],
                [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
            ]

            query.edit_message_text(
                "🎲 *Случайные исторические события*\n\n"
                "Для вас выбраны следующие события из истории России:\n"
                f"{events_list}\n\n"
                "Нажмите на кнопку ниже, чтобы увидеть эти события на интерактивной карте.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return self.MAP

        elif query.data == 'conversation':
            # Обработка кнопки беседы о истории России
            query.edit_message_text(
                "🗣️ *Беседа о истории России*\n\n"
                "Здесь вы можете задать вопрос или начать беседу на любую тему, связанную с историей России.\n\n"
                "Просто напишите вашу мысль или вопрос, и я отвечу вам на основе исторических данных.",
                parse_mode='Markdown'
            )
            return self.CONVERSATION
        elif query.data == 'topic':
            # Генерируем список тем с помощью ИИ
            prompt = "Составь список из 30 ключевых тем по истории России, которые могут быть интересны для изучения. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
            try:
                try:
                    query.edit_message_text("⏳ Загружаю список тем истории России...")
                except Exception as e:
                    self.logger.warning(f"Не удалось обновить сообщение о загрузке тем: {e}")
                    query.message.reply_text("⏳ Загружаю список тем истории России...")

                topics_text = self.api_client.ask_grok(prompt)

                # Парсим и сохраняем темы
                filtered_topics = self.ui_manager.parse_topics(topics_text)
                context.user_data['topics'] = filtered_topics

                # Создаем клавиатуру с темами
                reply_markup = self.ui_manager.create_topics_keyboard(filtered_topics)

                try:
                    query.edit_message_text(
                        "📚 *Темы по истории России*\n\nВыберите тему для изучения или введите свою:",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    self.logger.warning(f"Не удалось обновить сообщение со списком тем: {e}")
                    query.message.reply_text(
                        "📚 *Темы по истории России*\n\nВыберите тему для изучения или введите свою:",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )

                self.logger.info(f"Пользователю {user_id} показаны темы для изучения")
            except Exception as e:
                self.logger.log_error(e, f"Ошибка при генерации списка тем для пользователя {user_id}")
                query.edit_message_text(
                    f"Произошла ошибка при генерации списка тем: {e}. Попробуй еще раз.", 
                    reply_markup=self.ui_manager.main_menu()
                )
            return self.CHOOSE_TOPIC
        elif query.data == 'test':
            topic = context.user_data.get('current_topic', None)
            if not topic:
                query.edit_message_text(
                    "⚠️ Сначала выбери тему, нажав на кнопку 'Выбрать тему'.",
                    reply_markup=self.ui_manager.main_menu()
                )
                return self.TOPIC

            # Генерируем тест из вопросов
            query.edit_message_text(f"🧠 Генерирую тест по теме: *{topic}*...", parse_mode='Markdown')
            self.logger.info(f"Генерация теста по теме '{topic}' для пользователя {user_id}")

            try:
                # Получаем тест через сервис контента
                test_data = self.content_service.generate_test(topic)

                valid_questions = test_data['original_questions']
                display_questions = test_data['display_questions']

                context.user_data['questions'] = valid_questions
                context.user_data['current_question'] = 0
                context.user_data['score'] = 0

                # Сохраняем оригинальные вопросы для проверки ответов
                context.user_data['original_questions'] = valid_questions
                # Сохраняем очищенные вопросы для отображения
                context.user_data['display_questions'] = display_questions

                # Создаем кнопку для завершения теста
                keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                query.edit_message_text(
                    f"📝 *Тест по теме: {topic}*\n\nНачинаем тест из {len(valid_questions)} вопросов! Вот первый вопрос:",
                    parse_mode='Markdown'
                )
                query.message.reply_text(display_questions[0])
                query.message.reply_text(
                    "Напиши цифру правильного ответа (1, 2, 3 или 4).", 
                    reply_markup=reply_markup
                )
                self.logger.info(f"Тест по теме '{topic}' успешно сгенерирован для пользователя {user_id}")
            except Exception as e:
                self.logger.log_error(e, f"Ошибка при генерации вопросов для пользователя {user_id}")
                query.edit_message_text(
                    f"Произошла ошибка при генерации вопросов: {e}. Попробуй еще раз.", 
                    reply_markup=self.ui_manager.main_menu()
                )
            return self.ANSWER
        elif query.data == 'more_topics':
            # Генерируем новый список тем с помощью ИИ
            # Добавляем случайный параметр для получения разных тем
            random_seed = random.randint(1, 1000)
            prompt = f"Составь список из 30 новых и оригинальных тем по истории России, которые могут быть интересны для изучения. Сосредоточься на темах {random_seed}. Выбери темы, отличные от стандартных и ранее предложенных. Каждая тема должна быть емкой и конкретной (не более 6-7 слов). Перечисли их в виде нумерованного списка."
            try:
                query.edit_message_text("🔄 Генерирую новый список уникальных тем по истории России...")
                # Отключаем кэширование для получения действительно новых тем каждый раз
                topics = self.api_client.ask_grok(prompt, use_cache=False)

                # Парсим и сохраняем темы
                filtered_topics = self.ui_manager.parse_topics(topics)
                context.user_data['topics'] = filtered_topics

                # Создаем клавиатуру с темами
                reply_markup = self.ui_manager.create_topics_keyboard(filtered_topics)

                query.edit_message_text(
                    "📚 *Новые темы по истории России*\n\nВыберите одну из только что сгенерированных тем или введите свою:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                self.logger.info(f"Пользователю {user_id} показан новый список тем для изучения")
            except Exception as e:
                self.logger.log_error(e, f"Ошибка при генерации новых тем для пользователя {user_id}")
                query.edit_message_text(
                    f"Произошла ошибка при генерации списка тем: {e}. Попробуй еще раз.", 
                    reply_markup=self.ui_manager.main_menu()
                )
            return self.CHOOSE_TOPIC
        elif query.data == 'end_test' or query.data == 'cancel':
            if query.data == 'end_test':
                self.logger.info(f"Пользователь {user_id} досрочно завершил тест")
                query.edit_message_text("Тест завершен досрочно. Возвращаемся в главное меню.")
                query.message.reply_text("Выберите действие:", reply_markup=self.ui_manager.main_menu())
                return self.TOPIC
            else:
                self.logger.info(f"Пользователь {user_id} отменил действие")
                query.edit_message_text("Действие отменено. Нажми /start, чтобы начать заново.")
                return ConversationHandler.END
        elif query.data == 'custom_topic':
            query.edit_message_text("Напиши тему по истории России, которую ты хочешь изучить:")
            return self.CHOOSE_TOPIC

    def choose_topic(self, update, context):
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

            # Очищаем историю чата перед новым действием (двойной вызов)
            self.message_manager.clear_chat_history(update, context)
            self.message_manager.clear_chat_history(update, context)

            self.logger.info(f"Пользователь {user_id} выбирает тему через кнопку: {query.data}")

            # Если пользователь выбрал "Больше тем"
            if query.data == 'more_topics':
                return self.button_handler(update, context)

            # Если пользователь выбрал "Своя тема"
            elif query.data == 'custom_topic':
                query.edit_message_text("Напиши тему по истории России, которую ты хочешь изучить:")
                return self.CHOOSE_TOPIC

            # Если пользователь хочет вернуться в меню
            elif query.data == 'back_to_menu':
                return self.button_handler(update, context)

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
                        self.logger.info(f"Пользователь {user_id} выбрал тему: {topic}")

                        # Функция для обновления сообщения о загрузке
                        def update_message(text):
                            query.edit_message_text(text, parse_mode='Markdown')

                        # Получаем информацию о теме
                        messages = self.content_service.get_topic_info(topic, update_message)

                        # Отправляем сообщения, проверяя возможность редактирования
                        if messages:
                            try:
                                # Пробуем отредактировать первое сообщение
                                query.edit_message_text(messages[0], parse_mode='Markdown')
                            except Exception as e:
                                # Если редактирование не удалось, отправляем как новое сообщение
                                self.logger.warning(f"Не удалось отредактировать сообщение: {e}")
                                query.message.reply_text(messages[0], parse_mode='Markdown')

                            # Отправляем остальные сообщения как новые
                            for msg in messages[1:]:
                                query.message.reply_text(msg, parse_mode='Markdown')

                        query.message.reply_text("Выбери следующее действие:", reply_markup=self.ui_manager.main_menu())
                        self.logger.info(f"Пользователю {user_id} успешно отправлена информация по теме: {topic}")
                    else:
                        self.logger.warning(f"Пользователь {user_id} выбрал несуществующую тему с индексом {topic_index+1}")
                        query.edit_message_text(
                            f"Ошибка: Тема с индексом {topic_index+1} не найдена. Попробуйте выбрать другую тему.", 
                            reply_markup=self.ui_manager.main_menu()
                        )
                except Exception as e:
                    self.logger.log_error(e, f"Ошибка при обработке темы для пользователя {user_id}")
                    query.edit_message_text(
                        f"Произошла ошибка при загрузке темы: {e}. Попробуй еще раз.", 
                        reply_markup=self.ui_manager.main_menu()
                    )
                return self.TOPIC
        # Возвращаем CHOOSE_TOPIC, если не обработано другими условиями
        return self.CHOOSE_TOPIC

    def handle_custom_topic(self, update, context):
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

        # Очищаем историю чата перед обработкой новой темы (двойной вызов)
        self.message_manager.clear_chat_history(update, context)
        self.message_manager.clear_chat_history(update, context)

        self.logger.info(f"Пользователь {user_id} ввел свою тему: {topic}")

        try:
            update.message.reply_text(f"📝 Загружаю информацию по теме: *{topic}*...", parse_mode='Markdown')

            # Функция для обновления сообщения о загрузке
            def update_message(text):
                update.message.reply_text(text, parse_mode='Markdown')

            # Получаем информацию о теме
            messages = self.content_service.get_topic_info(topic, update_message)

            # Отправляем все сообщения
            for msg in messages:
                update.message.reply_text(msg, parse_mode='Markdown')

            update.message.reply_text("Выбери следующее действие:", reply_markup=self.ui_manager.main_menu())
            self.logger.info(f"Пользователю {user_id} успешно отправлена информация по теме: {topic}")
        except Exception as e:
            self.logger.log_error(e, f"Ошибка при обработке пользовательской темы для пользователя {user_id}")
            update.message.reply_text(f"Произошла ошибка: {e}. Попробуй еще раз.", reply_markup=self.ui_manager.main_menu())
        return self.TOPIC

    def handle_answer(self, update, context):
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

        # Очищаем историю чата перед ответом на новый вопрос (двойной вызов)
        self.message_manager.clear_chat_history(update, context)
        self.message_manager.clear_chat_history(update, context)

        questions = context.user_data.get('questions', [])
        current_question = context.user_data.get('current_question', 0)

        if not questions:
            self.logger.warning(f"Пользователь {user_id} пытается ответить на вопрос, но вопросы отсутствуют")
            update.message.reply_text(
                "Ошибка: вопросы не найдены. Начните тест заново.",
                reply_markup=self.ui_manager.main_menu()
            )
            return self.TOPIC

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
            self.logger.error(f"Ошибка при обработке ответа пользователя {user_id}: {e}")
            update.message.reply_text(
                "Ошибка в формате вопросов. Попробуй начать тест заново, нажав 'Пройти тест'.", 
                reply_markup=self.ui_manager.main_menu()
            )
            return self.TOPIC

        # Проверяем ответ пользователя
        if user_answer == correct_answer:
            context.user_data['score'] = context.user_data.get('score', 0) + 1
            sent_msg = update.message.reply_text("✅ Правильно!")
            self.message_manager.save_message_id(update, context, sent_msg.message_id)
            self.logger.info(f"Пользователь {user_id} ответил верно на вопрос {current_question+1}")
        else:
            # Не показываем правильный ответ
            sent_msg = update.message.reply_text("❌ Неправильно!")
            self.message_manager.save_message_id(update, context, sent_msg.message_id)
            self.logger.info(f"Пользователь {user_id} ответил неверно на вопрос {current_question+1}")

        # Переходим к следующему вопросу
        context.user_data['current_question'] = current_question + 1

        if context.user_data['current_question'] < len(display_questions):
            next_question = context.user_data['current_question'] + 1
            sent_msg1 = update.message.reply_text(f"Вопрос {next_question} из {len(display_questions)}:")
            self.message_manager.save_message_id(update, context, sent_msg1.message_id)

            sent_msg2 = update.message.reply_text(display_questions[context.user_data['current_question']])
            self.message_manager.save_message_id(update, context, sent_msg2.message_id)

            # Создаем клавиатуру с кнопкой для завершения теста
            keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            sent_msg3 = update.message.reply_text("Напиши цифру правильного ответа (1, 2, 3 или 4).", reply_markup=reply_markup)
            self.message_manager.save_message_id(update, context, sent_msg3.message_id)
            return self.ANSWER
        else:
            # Тест завершен, показываем результаты
            score = context.user_data.get('score', 0)
            total_questions = len(questions)
            percentage = (score / total_questions) * 100
            topic = context.user_data.get('current_topic', 'выбранной теме')

            # Оценка усвоенного материала
            if percentage >= 90:
                assessment = "🏆 Отлично! Ты прекрасно усвоил материал."
            elif percentage >= 70:
                assessment = "👍 Хорошо! Ты неплохо усвоил материал, но есть над чем поработать."
            elif percentage >= 50:
                assessment = "👌 Удовлетворительно. Рекомендуется повторить материал."
            else:
                assessment = "📚 Неудовлетворительно. Тебе стоит изучить тему заново."
                
            # Получаем рекомендации похожих тем
            similar_topics = self.recommend_similar_topics(topic, context)
            
            # Формируем сообщение с результатами
            result_message = f"🎯 Тест по теме '*{topic}*' завершен!\n\n"
            result_message += f"Ты ответил правильно на {score} из {total_questions} вопросов ({percentage:.1f}%).\n\n{assessment}\n\n"
            
            # Добавляем рекомендации, если они есть
            if similar_topics:
                result_message += "📚 *Рекомендуемые темы для изучения:*\n"
                for i, rec_topic in enumerate(similar_topics, 1):
                    result_message += f"{i}. {rec_topic}\n"
                result_message += "\n"
                
            result_message += "Выбери следующее действие:"
            
            update.message.reply_text(
                result_message,
                parse_mode='Markdown',
                reply_markup=self.ui_manager.main_menu()
            )
            self.logger.info(f"Пользователь {user_id} завершил тест с результатом {score}/{total_questions} ({percentage:.1f}%)")
            return self.TOPIC

    def handle_conversation(self, update, context):
        """
        Обрабатывает сообщения пользователя в режиме беседы с улучшенной оптимизацией.

        Также обрабатывает ввод ID нового администратора, если его ожидает админ-панель.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора

        Returns:
            int: Следующее состояние разговора
        """
        # Проверяем, ожидаем ли мы ввод ID нового администратора
        if hasattr(self, 'admin_panel') and 'waiting_for_admin_id' in context.user_data:
            self.admin_panel.process_new_admin_id(update, context)
            return self.CONVERSATION
            
        user_message = update.message.text
        user_id = update.message.from_user.id

        # Очищаем историю чата один раз для экономии ресурсов
        self.message_manager.clear_chat_history(update, context)

        # Логируем сообщение в сокращенном виде
        truncated_message = user_message[:50] + ('...' if len(user_message) > 50 else '')
        self.logger.info(f"Пользователь {user_id} отправил сообщение в режиме беседы: {truncated_message}")

        # Отправляем индикатор набора текста
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        try:
            # Простая эвристическая проверка на историческую тематику вместо отдельного API запроса
            # Ключевые слова и фразы для истории России
            history_keywords = [
                'россия', 'история', 'царь', 'императ', 'ссср', 'война', 'революц', 
                'рус', 'соверск', 'петр', 'екатерин', 'сталин', 'ленин', 'княз', 
                'династ', 'кремл', 'москв', 'киев', 'новгород', 'рюрик', 'романов',
                'советск', 'империя', 'монгол', 'битв', 'восстан', 'реформ', 'дума',
                'пётр', 'иван', 'павел', 'николай', 'александр', 'распутин', 'годы',
                'период', 'боярин', 'дворян', 'казак'
            ]
            
            # Проверка сообщения на соответствие исторической тематике
            msg_lower = user_message.lower()
            
            # Проверяем наличие ключевых слов
            is_history_related = any(keyword in msg_lower for keyword in history_keywords)
            
            # Если ключевых слов нет, но сообщение короткое и может быть запросом, предполагаем, что это исторический вопрос
            if not is_history_related and len(user_message) < 100 and ('?' in user_message or 'расскажи' in msg_lower):
                is_history_related = True

            # В зависимости от результата проверки формируем запрос к API
            if is_history_related:
                # Краткий системный промпт для экономии токенов и ускорения ответа
                prompt = f"""Ответь на исторический вопрос о России: "{user_message}"
Отвечай кратко, основываясь на исторических фактах.
Максимум 250 слов."""
                
                # Получаем ответ от API с индикатором набора текста
                context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                # Ограничиваем размер ответа для экономии ресурсов
                response = self.api_client.ask_grok(prompt, max_tokens=800, temp=0.1)
            else:
                # Стандартный ответ для неисторических вопросов
                response = ("Я специализируюсь на вопросах, связанных с историей России. "
                           "Пожалуйста, задайте вопрос на историческую тему, например: "
                           "'Когда была Куликовская битва?' или 'Расскажи о правлении Екатерины II'.")

            # Отправляем ответ пользователю
            sent_msg = update.message.reply_text(response)
            self.message_manager.save_message_id(update, context, sent_msg.message_id)
            
            # Кнопка возврата в меню
            keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем кнопку возврата отдельным сообщением
            nav_msg = update.message.reply_text(
                "Вы можете задать еще один вопрос или вернуться в главное меню:",
                reply_markup=reply_markup
            )
            self.message_manager.save_message_id(update, context, nav_msg.message_id)
            
        except Exception as e:
            self.logger.log_error(e, f"Ошибка при обработке беседы для пользователя {user_id}")
            
            # Отправляем сообщение об ошибке с кнопкой возврата
            error_msg = update.message.reply_text(
                "К сожалению, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже или вернитесь в меню.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
            )
            self.message_manager.save_message_id(update, context, error_msg.message_id)

        return self.CONVERSATION

    def recommend_similar_topics(self, current_topic, context):
        """
        Рекомендует пользователю похожие темы на основе текущей темы.
        
        Args:
            current_topic (str): Текущая тема пользователя
            context: Контекст разговора
            
        Returns:
            list: Список рекомендованных тем
        """
        try:
            # Формируем запрос на рекомендацию
            prompt = f"На основе темы '{current_topic}' предложи 3 связанные темы по истории России, которые могут заинтересовать пользователя. Перечисли их в формате нумерованного списка без дополнительных пояснений."
            
            # Получаем ответ от API
            similar_topics_text = self.api_client.ask_grok(prompt, max_tokens=150, temp=0.4)
            
            # Парсим темы
            similar_topics = []
            for line in similar_topics_text.split('\n'):
                # Ищем строки с форматом "1. Тема" или "- Тема"
                if (line.strip().startswith(('1.', '2.', '3.', '-'))):
                    # Удаляем префикс и лишние пробелы
                    topic = re.sub(r'^[\d\.\-\s]+', '', line).strip()
                    if topic:
                        similar_topics.append(topic)
            
            return similar_topics[:3]  # Возвращаем максимум 3 темы
        except Exception as e:
            self.logger.warning(f"Не удалось сгенерировать похожие темы: {e}")
            return []
            
    def admin_command(self, update, context):
        """
        Обрабатывает команду /admin для доступа к административной панели.
        
        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        # Передаем управление в модуль админ-панели
        if hasattr(self, 'admin_panel'):
            self.admin_panel.handle_admin_command(update, context)
        else:
            update.message.reply_text("Административная панель недоступна")

    def admin_callback(self, update, context):
        """
        Обрабатывает нажатия на кнопки в административной панели.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        query = update.callback_query

        # Проверяем наличие и передаем обработку в админ-панель
        if hasattr(self, 'admin_panel'):
            # Обрабатываем все callback-запросы, начинающиеся с admin_
            if query.data.startswith('admin_'):
                # Проверяем, это удаление админа или нет
                if query.data.startswith('admin_delete_'):
                    # Извлекаем ID админа для удаления
                    admin_id = int(query.data.split('_')[2])
                    self.admin_panel.handle_delete_admin_callback(update, context, admin_id)
                else:
                    # Обычный admin callback
                    self.admin_panel.handle_admin_callback(update, context)
                return True
        return False

    def error_handler(self, update, context):
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

        self.logger.log_error(error, additional_info)

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