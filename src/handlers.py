import telegram
import re
import time
import random
import os
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

        # Инициализируем сервисы
        from src.test_service import TestService
        from src.topic_service import TopicService
        self.test_service = TestService(api_client, logger)
        self.topic_service = TopicService(api_client, logger)

        # Импортируем константы состояний из config
        from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION
        self.TOPIC = TOPIC
        self.CHOOSE_TOPIC = CHOOSE_TOPIC
        self.TEST = TEST
        self.ANSWER = ANSWER
        self.CONVERSATION = CONVERSATION

        # Кэш для предотвращения повторных нажатий кнопок
        self.callback_cache = {}
        self.callback_cache_ttl = 2  # Время жизни записи в кэше (секунды)

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

        # История чата сохраняется
        chat_id = update.effective_chat.id

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
        Включает механизм защиты от дублирования запросов.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора

        Returns:
            int: Следующее состояние разговора
        """
        query = update.callback_query
        try:
            query.answer()  # Подтверждаем нажатие кнопки
        except telegram.error.BadRequest as e:
            if "query is too old" in str(e).lower():
                # Запрос устарел, это нормально для старых кнопок
                self.logger.info(f"Старый запрос кнопки, пропуск подтверждения: {e}")
            else:
                self.logger.warning(f"Не удалось подтвердить кнопку: {e}")
        except Exception as e:
            self.logger.warning(f"Не удалось подтвердить кнопку: {e}")

        user_id = query.from_user.id
        query_data = query.data

        # Проверка на дублирование запросов с защитой от повторных нажатий
        import time
        current_time = time.time()
        cache_key = (user_id, query_data)

        if cache_key in self.callback_cache:
            last_time = self.callback_cache[cache_key]
            # Если с момента последнего нажатия прошло меньше TTL секунд
            if current_time - last_time < self.callback_cache_ttl:
                self.logger.info(f"Игнорирование повторного нажатия кнопки {query_data} пользователем {user_id}")
                return None  # Игнорируем повторное нажатие

        # Обновляем время последнего нажатия
        self.callback_cache[cache_key] = current_time

        # Очистка устаревших записей из кэша (каждые 100 запросов)
        if len(self.callback_cache) > 100:
            # Удаляем записи старше TTL
            old_keys = [k for k, v in self.callback_cache.items() if current_time - v > self.callback_cache_ttl]
            for k in old_keys:
                del self.callback_cache[k]

        self.logger.info(f"Пользователь {user_id} нажал кнопку: {query_data}")

        if query_data == 'back_to_menu':
            query.edit_message_text(
                "Выберите действие в меню ниже:",
                reply_markup=self.ui_manager.main_menu()
            )
            return self.TOPIC
        elif query_data == 'project_info':
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
                # Создаем клавиатуру только с кнопкой возврата в меню
                keyboard = [
                    [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
                ]

                # Отправляем первую часть с редактированием сообщения
                query.edit_message_text(
                    parts[0][:4000],  # Ограничиваем длину для безопасности
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

                # Отправляем остальные части как новые сообщения
                for i, part in enumerate(parts[1:], 1):
                    sent_msg = query.message.reply_text(
                        part[:4000],  # Ограничиваем длину для безопасности
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard) if i == len(parts[1:]) else None
                    )
                    # Сохраняем ID сообщения
                    self.message_manager.save_message_id(update, context, sent_msg.message_id)

                # Подготавливаем презентации заранее
                import sys
                sys.path.append('.')
                from create_presentation_doc import create_presentation_docx

                # Создаем Word документ если он не существует
                docx_path = 'История_России_подробная_презентация.docx'
                if not os.path.exists(docx_path):
                    docx_path = create_presentation_docx('detailed_presentation.md', docx_path)

                # Отправляем отдельное сообщение со ссылками на скачивание
                download_message = "📥 *Скачать презентацию:*\n\n"

                # Проверяем наличие Replit Object Storage и инициализируем
                try:
                    from replit.object_storage import Client
                    obj_storage_available = True
                    self.logger.info("Инициализация Object Storage для хранения презентаций")
                    storage_client = Client()
                except ImportError:
                    obj_storage_available = False
                    self.logger.warning("Replit Object Storage не доступен. Будет использоваться локальное хранение.")
                except Exception as storage_init_error:
                    obj_storage_available = False
                    self.logger.error(f"Ошибка при инициализации Object Storage: {storage_init_error}")

                # Проверяем, есть ли файл в Object Storage (если доступно)
                docx_in_storage = False
                if obj_storage_available:
                    try:
                        # Проверяем наличие файла в Object Storage
                        docx_in_storage = storage_client.exists('История_России_подробная_презентация.docx')
                        self.logger.info(f"Файл презентации в Object Storage: {docx_in_storage}")
                    except Exception as storage_check_error:
                        self.logger.error(f"Ошибка при проверке файла в Object Storage: {storage_check_error}")

                # Отправляем файл, используя оптимальную стратегию
                try:
                    # Сначала пытаемся отправить из Object Storage, если возможно
                    if obj_storage_available and docx_in_storage:
                        self.logger.info("Отправка презентации из Object Storage")
                        try:
                            # Загружаем из Object Storage во временный буфер
                            from io import BytesIO
                            file_buffer = BytesIO()
                            storage_client.download_to_file('История_России_подробная_презентация.docx', file_buffer)
                            file_buffer.seek(0)

                            # Проверяем размер файла
                            if file_buffer.getbuffer().nbytes > 0:
                                # Отправляем из буфера
                                file_buffer.name = 'История_России_подробная_презентация.docx'
                                sent_doc = context.bot.send_document(
                                    chat_id=update.effective_chat.id,
                                    document=file_buffer,
                                    filename='История_России_подробная_презентация.docx',
                                    caption="📚 Подробная иллюстрированная презентация бота по истории России в формате Word.",
                                    timeout=60
                                )
                                self.message_manager.save_message_id(update, context, sent_doc.message_id)
                                self.logger.info("Презентация успешно отправлена из Object Storage")

                            else:
                                raise ValueError("Файл из Object Storage пуст")

                        except Exception as storage_send_error:
                            self.logger.error(f"Ошибка при отправке из Object Storage: {storage_send_error}")
                            # Переходим к обычному методу отправки
                            raise ValueError("Не удалось отправить из Object Storage")

                    # Если не удалось отправить из Object Storage, пробуем из локального файла
                    if os.path.exists(docx_path) and os.path.getsize(docx_path) > 0:
                        self.logger.info("Отправка презентации из локального файла")
                        with open(docx_path, 'rb') as docx_file:
                            # Читаем содержимое файла
                            file_content = docx_file.read()

                            # Проверяем, что содержимое не пустое
                            if len(file_content) > 0:
                                # Отправляем документ из буфера памяти
                                from io import BytesIO
                                file_obj = BytesIO(file_content)
                                file_obj.name = 'История_России_подробная_презентация.docx'

                                # Попытка отправить с установленным таймаутом
                                sent_doc = context.bot.send_document(
                                    chat_id=update.effective_chat.id,
                                    document=file_obj,
                                    filename='История_России_подробная_презентация.docx',
                                    caption="📚 Подробная иллюстрированная презентация бота по истории России в формате Word.",
                                    timeout=60  # Увеличенный таймаут
                                )
                                self.message_manager.save_message_id(update, context, sent_doc.message_id)
                                self.logger.info("Презентация успешно отправлена из локального файла")

                                # Сохраняем в Object Storage для будущего использования, если он доступен
                                if obj_storage_available and not docx_in_storage:
                                    try:
                                        with open(docx_path, 'rb') as f:
                                            storage_client.upload_from_file('История_России_подробная_презентация.docx', f)
                                        self.logger.info("Презентация сохранена в Object Storage после успешной отправки")
                                    except Exception as backup_error:
                                        self.logger.error(f"Не удалось сохранить файл в Object Storage: {backup_error}")
                            else:
                                raise ValueError("Локальный файл презентации пуст")
                    else:
                        raise ValueError(f"Локальный файл не существует или пуст: {docx_path}")

                except Exception as docx_err:
                    self.logger.error(f"Ошибка при отправке DOCX файла: {docx_err}")

                    # Создаем новую презентацию и пробуем отправить еще раз
                    try:
                        self.logger.info("Пересоздание презентации после ошибки")
                        # Пересоздаем презентацию
                        from create_presentation_doc import create_presentation_docx
                        new_docx_path = create_presentation_docx('detailed_presentation.md', 'История_России_новая_презентация.docx')

                        # Сохраняем в Object Storage, если доступно
                        if obj_storage_available:
                            try:
                                with open(new_docx_path, 'rb') as f:
                                    storage_client.upload_from_file('История_России_подробная_презентация.docx', f)
                                self.logger.info("Новая презентация успешно сохранена в Object Storage")
                            except Exception as storage_err:
                                self.logger.error(f"Ошибка при сохранении файла в Object Storage: {storage_err}")

                        # Отправляем документ
                        self.logger.info("Отправка пересозданной презентации")
                        with open(new_docx_path, 'rb') as new_docx_file:
                            sent_doc = context.bot.send_document(
                                chat_id=update.effective_chat.id,
                                document=new_docx_file,
                                filename='История_России_подробная_презентация.docx',
                                caption="📚 Подробная иллюстрированная презентация бота по истории России в формате Word.",
                                timeout=60  # Увеличенный таймаут
                            )
                            self.message_manager.save_message_id(update, context, sent_doc.message_id)
                            self.logger.info("Пересозданная презентация успешно отправлена")

                    except Exception as retry_err:
                        self.logger.error(f"Повторная ошибка при создании и отправке DOCX: {retry_err}")
                        # Информируем пользователя о проблеме и предлагаем ссылку на меню
                        query.message.reply_text(
                            "К сожалению, произошла ошибка при отправке файла презентации. Пожалуйста, попробуйте позже.",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                        )

                # Также отправляем обычный текстовый файл для совместимости
                try:
                    md_path = 'detailed_presentation.md'
                    md_in_storage = False

                    # Проверяем наличие MD-файла в Object Storage
                    if obj_storage_available:
                        try:
                            md_in_storage = storage_client.exists(md_path)
                            self.logger.info(f"MD-файл в Object Storage: {md_in_storage}")
                        except Exception as md_check_error:
                            self.logger.error(f"Ошибка при проверке MD-файла в Object Storage: {md_check_error}")

                    # Пытаемся отправить из Object Storage если возможно
                    if obj_storage_available and md_in_storage:
                        self.logger.info("Отправка MD-файла из Object Storage")
                        try:
                            # Загружаем из Object Storage во временный буфер
                            from io import BytesIO
                            md_buffer = BytesIO()
                            storage_client.download_to_file(md_path, md_buffer)
                            md_buffer.seek(0)

                            # Проверяем размер файла
                            if md_buffer.getbuffer().nbytes > 0:
                                # Отправляем из буфера
                                md_buffer.name = 'История_России_подробная_презентация.md'
                                sent_md = context.bot.send_document(
                                    chat_id=update.effective_chat.id,
                                    document=md_buffer,
                                    filename='История_России_подробная_презентация.md',
                                    caption="📄 Версия презентации в текстовом формате Markdown.",
                                    timeout=30
                                )
                                self.message_manager.save_message_id(update, context, sent_md.message_id)
                                self.logger.info("MD-файл успешно отправлен из Object Storage")
                            else:
                                raise ValueError("MD-файл из Object Storage пуст")

                        except Exception as md_storage_send_error:
                            self.logger.error(f"Ошибка при отправке MD-файла из Object Storage: {md_storage_send_error}")
                            # Переходим к обычному методу отправки
                            raise ValueError("Не удалось отправить MD-файл из Object Storage")

                    # Если не удалось отправить из Object Storage, пробуем из локального файла
                    if os.path.exists(md_path) and os.path.getsize(md_path) > 0:
                        self.logger.info("Отправка MD-файла из локального хранилища")
                        with open(md_path, 'rb') as md_file:
                            sent_md = context.bot.send_document(
                                chat_id=update.effective_chat.id,
                                document=md_file,
                                filename='История_России_подробная_презентация.md',
                                caption="📄 Версия презентации в текстовом формате Markdown.",
                                timeout=30
                            )
                            self.message_manager.save_message_id(update, context, sent_md.message_id)

                            # Сохраняем в Object Storage для будущего использования, если он доступен
                            if obj_storage_available and not md_in_storage:
                                try:
                                    with open(md_path, 'rb') as f:
                                        storage_client.upload_from_file(md_path, f)
                                    self.logger.info("MD-файл сохранен в Object Storage после успешной отправки")
                                except Exception as md_backup_error:
                                    self.logger.error(f"Не удалось сохранить MD-файл в Object Storage: {md_backup_error}")
                    else:
                        raise ValueError(f"Локальный MD-файл не существует или пуст: {md_path}")

                except Exception as md_err:
                    self.logger.error(f"Ошибка при отправке MD файла: {md_err}")
                    query.message.reply_text(
                        "Не удалось отправить текстовую версию презентации. Попробуйте позже.", 
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                    )

                self.logger.info(f"Пользователь {user_id} просмотрел информацию о проекте и получил файлы презентации")
            except telegram.error.BadRequest as e:
                self.logger.error(f"Ошибка при отправке информации о проекте: {e}")
                # Отправляем новое сообщение вместо редактирования
                for i, part in enumerate(parts):
                    keyboard = [
                        [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
                    ]
                    sent_msg = query.message.reply_text(
                        part[:4000],  # Ограничиваем длину для безопасности
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard) if i == len(parts) - 1 else None
                    )
                    # Сохраняем ID сообщения
                    self.message_manager.save_message_id(update, context, sent_msg.message_id)

                # Пробуем отправить файлы презентации
                try:
                    # Создаем Word документ если он не существует
                    docx_path = 'История_России_подробная_презентация.docx'
                    if not os.path.exists(docx_path):
                        from create_presentation_doc import create_presentation_docx
                        docx_path = create_presentation_docx('detailed_presentation.md', docx_path)

                    # Отправляем файлы напрямую как документы
                    with open(docx_path, 'rb') as docx_file:
                        sent_doc = context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=docx_file,
                            filename='История_России_подробная_презентация.docx',
                            caption="📚 Подробная иллюстрированная презентация бота по истории России в формате Word."
                        )
                        self.message_manager.save_message_id(update, context, sent_doc.message_id)

                    # Также отправляем обычный текстовый файл для совместимости
                    with open('detailed_presentation.md', 'rb') as md_file:
                        sent_md = context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=md_file,
                            filename='История_России_подробная_презентация.md',
                            caption="📄 Версия презентации в текстовом формате Markdown."
                        )
                        self.message_manager.save_message_id(update, context, sent_md.message_id)
                except Exception as file_err:
                    self.logger.error(f"Ошибка при отправке файлов презентации: {file_err}")
                    sent_err = query.message.reply_text(
                        "К сожалению, произошла ошибка при отправке файлов презентации. Пожалуйста, попробуйте позже.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                    )
                    self.message_manager.save_message_id(update, context, sent_err.message_id)

            return self.TOPIC
        elif query_data == 'conversation':
            # Обработка кнопки беседы о истории России
            query.edit_message_text(
                "🗣️ *Беседа о истории России*\n\n"
                "Здесь вы можете задать вопрос или начать беседу на любую тему, связанную с историей России.\n\n"
                "Просто напишите вашу мысль или вопрос, и я отвечу вам на основе исторических данных.",
                parse_mode='Markdown'
            )
            return self.CONVERSATION
        elif query_data == 'topic':
            # Генерируем список тем с помощью сервиса тем
            try:
                try:
                    query.edit_message_text("⏳ Загружаю список тем истории России...")
                except Exception as e:
                    self.logger.warning(f"Не удалось обновить сообщение о загрузке тем: {e}")
                    query.message.reply_text("⏳ Загружаю список тем истории России...")

                # Получаем список тем через сервис
                filtered_topics = self.topic_service.generate_topics_list()
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
        elif query_data == 'test':
            topic = context.user_data.get('current_topic', None)
            if not topic:
                query.edit_message_text(
                    "⚠️ Сначала выбери тему, нажав на кнопку 'Выбрать тему'.",
                    reply_markup=self.ui_manager.main_menu()
                )
                return self.TOPIC

            # Генерируем тест из вопросов
            query.edit_message_text(f"🧠 Генерирую тест по теме: *{topic}*...\n\nПодготовка 20 вопросов может занять некоторое время. Пожалуйста, подождите.", parse_mode='Markdown')
            self.logger.info(f"Генерация теста по теме '{topic}' для пользователя {user_id}")

            try:
                # Отправляем индикатор печати, пока генерируются вопросы
                context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)

                # Получаем тест через сервис тестирования
                test_data = self.test_service.generate_test(topic)

                # Получаем вопросы из теста
                valid_questions = test_data.get('original_questions', [])
                display_questions = test_data.get('display_questions', [])

                if not valid_questions:
                    raise ValueError("Не удалось получить вопросы для теста")

                # Сохраняем данные в контексте пользователя
                context.user_data['questions'] = valid_questions
                context.user_data['current_question'] = 0
                context.user_data['score'] = 0
                context.user_data['total_questions'] = len(valid_questions)

                # Сохраняем оригинальные вопросы для проверки ответов
                context.user_data['original_questions'] = valid_questions
                # Сохраняем очищенные вопросы для отображения
                context.user_data['display_questions'] = display_questions

                # Создаем кнопку для завершения теста
                keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Отправляем сообщение с началом теста без форматирования Markdown
                query.edit_message_text(
                    f"📝 Тест по теме: {topic}\n\nНачинаем тест из {len(valid_questions)} вопросов! Это позволит всесторонне проверить ваши знания по данной теме. Вот первый вопрос:"
                )

                # Проверяем существование первого вопроса
                if len(display_questions) > 0:
                    # Форматируем текст первого вопроса для лучшего отображения
                    question_text = display_questions[0]

                    # Форматируем вопрос и варианты ответов с помощью TestService
                    formatted_question = self.test_service.format_question_text(question_text)
                    main_question_text = formatted_question['main_question']
                    options_text = "\n".join(formatted_question['options'])

                    # Создаем форматированный текст с вопросом и вариантами
                    formatted_text = f"{main_question_text}\n\n{options_text}"

                    # Отправляем инфо о начале теста
                    query.message.reply_text(f"🧠 Вопрос 1 из {len(display_questions)}:")

                    # Отправляем отформатированный текст вопроса
                    query.message.reply_text(formatted_text)

                    # Отправляем инструкцию для ответа
                    query.message.reply_text(
                        "Напиши цифру правильного ответа (1, 2, 3 или 4).", 
                        reply_markup=reply_markup
                    )
                    self.logger.info(f"Тест по теме '{topic}' успешно сгенерирован для пользователя {user_id}")
                else:
                    raise ValueError("Не удалось получить вопросы для теста")

            except Exception as e:
                self.logger.log_error(e, f"Ошибка при генерации вопросов для пользователя {user_id}")
                query.edit_message_text(
                    f"Произошла ошибка при генерации теста: {str(e)}. Пожалуйста, попробуйте еще раз.", 
                    reply_markup=self.ui_manager.main_menu()
                )
            return self.ANSWER
        elif query_data == 'more_topics':
            # Генерируем новый список тем с помощью сервиса тем
            try:
                query.edit_message_text("🔄 Генерирую новый список уникальных тем по истории России...")

                # Получаем новый список тем через сервис
                filtered_topics = self.topic_service.generate_new_topics_list()
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
        elif query_data == 'clear_chat_retry':
            # Обработка запроса на очистку чата через callback (функциональность отключена)
            self.logger.info(f"Пользователь {user_id} запросил очистку чата (функция отключена)")
            query.answer("Функция очистки чата отключена")

            # Создаем клавиатуру для дополнительных действий
            keyboard = [
                [InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Обновляем сообщение
            query.edit_message_text(
                "⚠️ Функция очистки чата отключена в текущей версии.",
                reply_markup=reply_markup
            )

            # Отправляем новое сообщение с главным меню
            sent_msg = query.message.reply_text(
                "Выберите другое действие:", 
                reply_markup=self.ui_manager.main_menu()
            )
            self.message_manager.save_message_id(update, context, sent_msg.message_id)
            return self.TOPIC

        elif query_data == 'admin_clear_all_chats' and hasattr(self, 'admin_panel'):
            # Проверяем права администратора
            if self.admin_panel.is_admin(user_id):
                query.answer("Эта функция будет реализована в будущем")
                query.edit_message_text(
                    "⚙️ Функция очистки всех чатов находится в разработке. Текущая версия поддерживает очистку только текущего чата.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                )
                return self.TOPIC
            else:
                query.answer("У вас нет прав администратора")
                return self.TOPIC

        elif query_data == 'cancel' or query_data == 'end_test':
            if query_data == 'end_test':
                self.logger.info(f"Пользователь {user_id} досрочно завершил тест")
                query.edit_message_text("Тест завершен досрочно. Возвращаемся в главное меню.")
                query.message.reply_text("Выберите действие:", reply_markup=self.ui_manager.main_menu())
            return self.TOPIC
            else:
                self.logger.info(f"Пользователь {user_id} отменил действие")
                query.edit_message_text("Действие отменено. Нажми /start, чтобы начать заново.")
                return ConversationHandler.END
        elif query_data == 'custom_topic':
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
                        def update_message(message):
                            try:
                                query.edit_message_text(message, parse_mode='Markdown')
                            except Exception as e:
                                self.logger.warning(f"Не удалось обновить сообщение о загрузке: {e}")
                                query.message.reply_text(message, parse_mode='Markdown')

                        # Получаем информацию о теме через сервис тем (возвращает список сообщений)
                        messages = self.topic_service.get_topic_info(topic, update_message)

                        # Проверяем, что мы получили список сообщений
                        if isinstance(messages, list) and messages:
                            try:
                                # Сначала отправляем оглавление (первое сообщение)
                                query.edit_message_text(
                                    messages[0],
                                    parse_mode='Markdown',
                                    disable_web_page_preview=True
                                )

                                # Отправляем каждую главу как отдельное сообщение
                                import time
                                for i, msg in enumerate(messages[1:], 1):
                                    try:
                                        # Проверяем размер сообщения и разбиваем его при необходимости
                                        if len(msg) > 4000:
                                            # Сначала извлекаем заголовок с эмодзи и форматом главы
                                            header_match = re.match(r'^(.+?ГЛАВА \d+:.+?\*)\n\n(┈+)\n\n', msg)
                                            if header_match:
                                                header = header_match.group(1) + "\n\n" + header_match.group(2) + "\n\n"
                                                content = msg[len(header):]

                                                # Ищем футер с навигацией
                                                footer_match = re.search(r'\n\n(•┈+•)\n\n(➡️.+|📝.+)$', msg)
                                                footer = ""
                                                if footer_match:
                                                    footer = "\n\n" + footer_match.group(1) + "\n\n" + footer_match.group(2)
                                                    content = content[:-(len(footer))]

                                                # Разбиваем контент на части по 3500 символов (с запасом)
                                                chunks = []
                                                current_length = 0
                                                current_chunk = ""

                                                # Разбиваем по абзацам
                                                paragraphs = content.split('\n\n')
                                                for paragraph in paragraphs:
                                                    if current_length + len(paragraph) + 4 <= 3500:
                                                        if current_chunk:
                                                            current_chunk += "\n\n" + paragraph
                                                        else:
                                                            current_chunk = paragraph
                                                        current_length += len(paragraph) + 4
                                                    else:
                                                        chunks.append(current_chunk)
                                                        current_chunk = paragraph
                                                        current_length = len(paragraph)

                                                if current_chunk:
                                                    chunks.append(current_chunk)

                                                # Определяем, из какой главы это сообщение
                                                chapter_match = re.search(r'ГЛАВА (\d+):', header)
                                                chapter_num = int(chapter_match.group(1)) if chapter_match else i

                                                # Отправляем части сообщения
                                                for j, chunk in enumerate(chunks, 1):
                                                    # Добавляем информацию о части к заголовку
                                                    part_header = header.replace("*\n\n", f"* (часть {j}/{len(chunks)})\n\n")

                                                    # Для последней части добавляем футер, для остальных - примечание о продолжении
                                                    if j == len(chunks):
                                                        full_msg = part_header + chunk + footer
                                                    else:
                                                        full_msg = part_header + chunk + "\n\n_(продолжение следует...)_"

                                                    # Добавляем задержку между сообщениями
                                                    if i > 1 or j > 1:
                                                        time.sleep(0.5)

                                                    sent_msg = query.message.reply_text(
                                                        full_msg, 
                                                        parse_mode='Markdown',
                                                        disable_web_page_preview=True
                                                    )
                                                    # Сохраняем ID сообщения
                                                    self.message_manager.save_message_id(update, context, sent_msg.message_id)
                                            else:
                                                # Если не удалось извлечь заголовок, отправляем сообщение частями
                                                chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
                                                for chunk in chunks:
                                                    sent_msg = query.message.reply_text(
                                                        chunk, 
                                                        parse_mode='Markdown',
                                                        disable_web_page_preview=True
                                                    )
                                                    self.message_manager.save_message_id(update, context, sent_msg.message_id)
                                                    time.sleep(0.5)
                                        else:
                                            # Если сообщение не превышает лимит, отправляем его как есть
                                            # Добавляем небольшую задержку между сообщениями
                                            if i > 1:
                                                time.sleep(0.5)

                                            sent_msg = query.message.reply_text(
                                                msg, 
                                                parse_mode='Markdown',
                                                disable_web_page_preview=True
                                            )
                                            # Сохраняем ID сообщения
                                            self.message_manager.save_message_id(update, context, sent_msg.message_id)
                                    except telegram.error.RetryAfter as e:
                                        # Обработка ошибки превышения лимита запросов
                                        self.logger.warning(f"Превышен лимит запросов. Ожидание {e.retry_after} секунд")
                                        time.sleep(e.retry_after)
                                        # Повторная попытка отправки
                                        sent_msg = query.message.reply_text(
                                            msg, 
                                            parse_mode='Markdown',
                                            disable_web_page_preview=True
                                        )
                                        self.message_manager.save_message_id(update, context, sent_msg.message_id)
                                    except Exception as e:
                                        self.logger.error(f"Ошибка при отправке части сообщения: {e}")
                                        # Пробуем отправить без форматирования
                                        try:
                                            sent_msg = query.message.reply_text(
                                                msg, 
                                                parse_mode=None,
                                                disable_web_page_preview=True
                                            )
                                            self.message_manager.save_message_id(update, context, sent_msg.message_id)
                                        except Exception as e2:
                                            self.logger.error(f"Вторая ошибка при отправке сообщения: {e2}")

                                self.logger.info(f"Отправлено {len(messages) + sum(1 for m in messages[1:] if len(m) > 4000)} сообщений по теме '{topic}'")
                            except Exception as e:
                                self.logger.error(f"Ошибка при отправке сообщения: {e}")
                                # В случае ошибки пробуем отправить как простой текст
                                query.edit_message_text(
                                    f"📚 Тема: {topic}\n\nПроизошла ошибка форматирования. Вот информация в упрощенном виде:",
                                    parse_mode=None
                                )

                                # Отправляем сообщения без форматирования
                                for msg in messages:
                                    try:
                                        query.message.reply_text(msg[:4000], parse_mode=None)
                                        if len(msg) > 4000:
                                            for i in range(4000, len(msg), 4000):
                                                query.message.reply_text(msg[i:i+4000], parse_mode=None)
                                                time.sleep(0.5)
                                    except Exception as e_msg:
                                        self.logger.error(f"Ошибка при отправке текста без форматирования: {e_msg}")
                        else:
                            # Обработка случая, когда messages не список или пустой
                            self.logger.warning(f"Некорректный формат ответа для темы: {topic}")
                            query.edit_message_text(
                                f"К сожалению, не удалось получить информацию по теме *{topic}*. Пожалуйста, попробуйте выбрать другую тему.",
                                parse_mode='Markdown'
                            )

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

        self.logger.info(f"Пользователь {user_id} ввел свою тему: {topic}")

        try:
            update.message.reply_text(f"📝 Загружаю информацию по теме: *{topic}*...", parse_mode='Markdown')

            # Функция для обновления сообщения о загрузке
            def update_message(message):
                update.message.reply_text(message, parse_mode='Markdown')

            # Получаем информацию о теме через сервис тем (теперь всегда возвращает список сообщений)
            messages = self.topic_service.get_topic_info(topic, update_message)

            # Проверяем, что мы получили список сообщений
            if isinstance(messages, list) and messages:
                try:
                    # Отправляем оглавление с информацией о теме
                    update.message.reply_text(
                        messages[0],
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )

                    # Отправляем каждую главу как отдельное сообщение с задержкой
                    import time
                    for i, msg in enumerate(messages[1:], 1):
                        try:
                            # Добавляем небольшую задержку между сообщениями для предотвращения лимитов API
                            if i > 1 and i % 3 == 0:  # Делаем паузу после каждого 3-го сообщения
                                time.sleep(0.5)

                            sent_msg = update.message.reply_text(
                                msg, 
                                parse_mode='Markdown',
                                disable_web_page_preview=True
                            )
                            # Сохраняем ID сообщения для возможности последующего удаления
                            self.message_manager.save_message_id(update, context, sent_msg.message_id)
                        except telegram.error.RetryAfter as e:
                            # Обработка ошибки превышения лимита запросов
                            self.logger.warning(f"Превышен лимит запросов. Ожидание {e.retry_after} секунд")
                            time.sleep(e.retry_after)
                            # Повторная попытка отправки
                            sent_msg = update.message.reply_text(
                                msg, 
                                parse_mode='Markdown',
                                disable_web_page_preview=True
                            )
                            self.message_manager.save_message_id(update, context, sent_msg.message_id)
                        except Exception as e:
                            self.logger.error(f"Ошибка при отправке части сообщения: {e}")

                    self.logger.info(f"Отправлено {len(messages)} сообщений по теме '{topic}'")
                except Exception as e:
                    self.logger.error(f"Ошибка при отправке сообщения: {e}")
                    # В случае ошибки пробуем отправить как простой текст
                    update.message.reply_text(
                        f"📚 Тема: {topic}\n\nПроизошла ошибка форматирования. Вот информация в упрощенном виде:"
                    )

                    # Отправляем сообщения без форматирования Markdown
                    for msg in messages:
                        update.message.reply_text(msg, parse_mode=None)
            else:
                # Обработка случая, когда messages не список или пустой
                self.logger.warning(f"Некорректный формат ответа для темы: {topic}")
                update.message.reply_text(
                    f"К сожалению, не удалось получить информацию по теме *{topic}*. Пожалуйста, попробуйте выбрать другую тему.",
                    parse_mode='Markdown'
                )

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

        # Получаем сохраненные данные теста
        questions = context.user_data.get('questions', [])
        current_question = context.user_data.get('current_question', 0)

        # Проверка наличия вопросов
        if not questions or current_question >= len(questions):
            self.logger.warning(f"Пользователь {user_id} пытается ответить на вопрос, но вопросы отсутствуют или индекс вне диапазона")
            update.message.reply_text(
                "Ошибка: вопросы не найдены или тест завершен. Начните тест заново.",
                reply_markup=self.ui_manager.main_menu()
            )
            return self.TOPIC

        # Получаем оригинальные вопросы с правильными ответами и вопросы для отображения
        original_questions = context.user_data.get('original_questions', questions)
        display_questions = context.user_data.get('display_questions', questions)

        # Проверка валидности пользовательского ввода
        if not user_answer.isdigit() or int(user_answer) < 1 or int(user_answer) > 4:
            sent_msg = update.message.reply_text(
                "⚠️ Пожалуйста, введите номер ответа (от 1 до 4).\n"
                "Попробуйте снова:"
            )
            self.message_manager.save_message_id(update, context, sent_msg.message_id)
            return self.ANSWER

        # Используем сервис тестирования для получения правильного ответа
        try:
            correct_answer = self.test_service.parse_correct_answer(original_questions[current_question])

            if not correct_answer:
                raise ValueError("Формат правильного ответа не найден")

            # Проверка валидности правильного ответа
            if int(correct_answer) < 1 or int(correct_answer) > 4:
                self.logger.warning(f"Некорректный правильный ответ {correct_answer} в вопросе {current_question+1}")
                correct_answer = "1"  # Установка значения по умолчанию

        except (IndexError, ValueError) as e:
            self.logger.error(f"Ошибка при обработке ответа пользователя {user_id} на вопрос {current_question+1}: {e}")
            update.message.reply_text(
                "Обнаружена ошибка в формате вопроса. Переходим к следующему вопросу или завершаем тест.", 
                reply_markup=self.ui_manager.main_menu()
            )
            # Переходим к следующему вопросу без учета этого
            context.user_data['current_question'] = current_question + 1

            # Если остались вопросы, показываем следующий
            if context.user_data['current_question'] < len(display_questions):
                return self._show_next_question(update, context, display_questions)
            else:
                return self._show_test_results(update, context, questions)

        # Проверяем ответ пользователя
        is_correct = user_answer == correct_answer
        if is_correct:
            # Увеличиваем счетчик правильных ответов
            context.user_data['score'] = context.user_data.get('score', 0) + 1
            sent_msg = update.message.reply_text("✅ Правильно!")
            self.message_manager.save_message_id(update, context, sent_msg.message_id)
            self.logger.info(f"Пользователь {user_id} ответил верно на вопрос {current_question+1}")
        else:
            sent_msg = update.message.reply_text(f"❌ Неправильно! Правильный ответ: {correct_answer}")
            self.message_manager.save_message_id(update, context, sent_msg.message_id)
            self.logger.info(f"Пользователь {user_id} ответил неверно на вопрос {current_question+1}")

        # Переходим к следующему вопросу
        context.user_data['current_question'] = current_question + 1

        # Если остались вопросы, показываем следующий
        if context.user_data['current_question'] < len(display_questions):
            return self._show_next_question(update, context, display_questions)
        else:
            return self._show_test_results(update, context, questions)

    def _show_next_question(self, update, context, display_questions):
        """
        Показывает следующий вопрос теста с форматированным отображением вариантов ответов.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            display_questions (list): Список вопросов для отображения

        Returns:
            int: Следующее состояние разговора
        """
        try:
            current_question = context.user_data.get('current_question', 0)
            total_questions = len(display_questions)

            # Получаем текст вопроса
            question_text = display_questions[current_question]

            # Форматируем вопрос и варианты ответов с помощью TestService
            formatted_question = self.test_service.format_question_text(question_text)
            main_question_text = formatted_question['main_question']
            options_text = "\n".join(formatted_question['options'])

            # Создаем форматированный текст с вопросом и вариантами
            formatted_text = f"{main_question_text}\n\n{options_text}"

            # Получаем основной вопрос и варианты ответов

            # Отправляем несколько сообщений для лучшего форматирования

            # Вычисляем процент выполнения теста
            completion_percent = int((current_question / total_questions) * 100)
            progress_bar = "▓" * (completion_percent // 5) + "░" * (20 - (completion_percent // 5))

            # 1. Сообщение с информацией о прогрессе теста
            progress_text = (f"🧠 Вопрос {current_question+1} из {total_questions}\n"
                            f"{progress_bar} {completion_percent}%\n"
                            f"Правильно отвечено: {context.user_data.get('score', 0)} из {current_question}")
            sent_msg1 = update.message.reply_text(progress_text)
            self.message_manager.save_message_id(update, context, sent_msg1.message_id)

            # 2. Сообщение с текстом вопроса
            sent_msg2 = update.message.reply_text(main_question_text)
            self.message_manager.save_message_id(update, context, sent_msg2.message_id)

            # 3. Отдельное сообщение с вариантами ответов
            sent_msg3 = update.message.reply_text(options_text)
            self.message_manager.save_message_id(update, context, sent_msg3.message_id)


            # 4. Сообщение с инструкцией и кнопкой для завершения
            keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            sent_msg4 = update.message.reply_text(
                "Напиши цифру правильного ответа (1, 2, 3 или 4).", 
                reply_markup=reply_markup
            )
            self.message_manager.save_message_id(update, context, sent_msg4.message_id)

            return self.ANSWER

        except Exception as e:
            self.logger.error(f"Ошибка при отображении следующего вопроса: {e}")
            update.message.reply_text(
                "Произошла ошибка при отображении вопроса. Завершаем тест.", 
                reply_markup=self.ui_manager.main_menu()
            )
            return self._show_test_results(update, context, display_questions)

    def _show_test_results(self, update, context, questions):
        """
        Показывает результаты теста.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            questions (list): Список вопросов

        Returns:
            int: Следующее состояние разговора
        """
        try:
            user_id = update.message.from_user.id
            score = context.user_data.get('score', 0)
            total_questions = len(questions)

            # Защита от деления на ноль
            if total_questions > 0:
                percentage = (score / total_questions) * 100
            else:
                percentage = 0

            topic = context.user_data.get('current_topic', 'выбранной теме')

            # Оценка усвоенного материала с дополнительными категориями для 20 вопросов
            if percentage >= 90:
                assessment = "🏆 Отлично! Ты прекрасно усвоил материал."
                grade = "Превосходно"
            elif percentage >= 80:
                assessment = "🥇 Очень хорошо! Ты хорошо знаешь эту тему."
                grade = "Отлично"
            elif percentage >= 70:
                assessment = "👍 Хорошо! Ты неплохо усвоил материал, но есть над чем поработать."
                grade = "Хорошо" 
            elif percentage >= 60:
                assessment = "🎓 Выше среднего. Основы темы освоены, но требуется углубление знаний."
                grade = "Выше среднего"
            elif percentage >= 50:
                assessment = "👌 Удовлетворительно. Рекомендуется повторить материал."
                grade = "Удовлетворительно"
            elif percentage >= 40:
                assessment = "📖 Ниже среднего. Требуется серьезное повторение материала."
                grade = "Ниже среднего"
            else:
                assessment = "📚 Неудовлетворительно. Тебе стоит изучить тему заново."
                grade = "Неудовлетворительно"

            # Определение уровня знаний по 20-балльной шкале для более точной оценки
            if total_questions == 20:
                if score >= 18:  # 90-100%
                    level = "Экспертный уровень"
                elif score >= 16:  # 80-89%
                    level = "Продвинутый уровень"
                elif score >= 14:  # 70-79%
                    level = "Хороший уровень"
                elif score >= 12:  # 60-69%
                    level = "Средний уровень"
                elif score >= 10:  # 50-59%
                    level = "Базовый уровень"
                else:  # < 50%
                    level = "Начальный уровень"

                # Добавляем уровень знаний к оценке
                assessment = f"{assessment}\n\nУровень знаний: *{level}*"

            # Получаем рекомендации похожих тем
            similar_topics = self.recommend_similar_topics(topic, context)

            # Формируем сообщение с результатами
            result_message = f"🎯 Тест по теме '*{topic}*' завершен!\n\n"
            result_message += f"Ты ответил правильно на {score} из {total_questions} вопросов ({percentage:.1f}%).\n\n"
            result_message += f"*Оценка:* {grade}\n\n"
            result_message += f"{assessment}\n\n"

            # Добавляем рекомендации, если они есть
            if similar_topics:
                result_message += "📚 *Рекомендуемые темы для изучения:*\n"
                for i, rec_topic in enumerate(similar_topics, 1):
                    result_message += f"{i}. {rec_topic}\n"
                result_message += "\n"

            result_message += "Выбери следующее действие:"

            # Отправляем результаты теста
            update.message.reply_text(
                result_message,
                parse_mode='Markdown',
                reply_markup=self.ui_manager.main_menu()
            )

            self.logger.info(f"Пользователь {user_id} завершил тест с результатом {score}/{total_questions} ({percentage:.1f}%)")

            # Очищаем данные теста
            context.user_data.pop('questions', None)
            context.user_data.pop('current_question', None)
            context.user_data.pop('score', None)
            context.user_data.pop('original_questions', None)
            context.user_data.pop('display_questions', None)

            return self.TOPIC

        except Exception as e:
            self.logger.error(f"Ошибка при отображении результатов теста: {e}")
            update.message.reply_text(
                f"Произошла ошибка при формировании результатов теста: {e}",
                reply_markup=self.ui_manager.main_menu()
            )
            return self.TOPIC

    def _sanitize_markdown(self, text):
        """
        Sanitizes text to prevent Markdown parsing errors.

        Args:
            text (str): The text to sanitize

        Returns:
            str: Sanitized text
        """
        if not text:
            return ""

        # Replace problematic characters that could break Markdown parsing
        replacements = {
            '*': '\\*',
            '_': '\\_',
            '`': '\\`',
            '[': '\\[',
            ']': '\\]',
            '(': '\\(',
            ')': '\\)',
            '#': '\\#',
            '>': '\\>',
            '+': '\\+',
            '-': '\\-',
            '=': '\\=',
            '|': '\\|',
            '{': '\\{',
            '}': '\\}',
            '.': '\\.',
            '!': '\\!'
        }

        sanitized_text = ""
        # Process one character at a time for better control
        for char in text:
            if char in replacements:
                sanitized_text += replacements[char]
            else:
                sanitized_text += char

        return sanitized_text

    # Метод _normalize_russian_input перенесен в ConversationService

    def handle_conversation(self, update, context):
        """
        Обрабатывает сообщения пользователя в режиме беседы с использованием
        отдельного сервиса для обработки сообщений. Используется улучшенный подход
        без редактирования сообщений для предотвращения ошибок.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора

        Returns:
            int: Следующее состояние разговора
        """
        # Проверка входных параметров
        if not update or not update.effective_user:
            self.logger.error("Получен некорректный объект обновления")
            return self.CONVERSATION

        user_id = update.effective_user.id
        self.logger.info(f"Обработка сообщения в режиме беседы от пользователя {user_id}")

        # Обработка ввода ID нового администратора
        if hasattr(self, 'admin_panel') and context.user_data.get('waiting_for_admin_id', False):
            self.admin_panel.process_new_admin_id(update, context)
            return self.CONVERSATION

        # Используем ConversationService для обработки остальных сообщений
        try:
            from src.conversation_service import ConversationService

            # Инициализируем сервис, если он еще не создан
            if not hasattr(self, 'conversation_service'):
                self.logger.info("Инициализация ConversationService")
                self.conversation_service = ConversationService(
                    api_client=self.api_client, 
                    logger=self.logger
                )

            # Обрабатываем сообщение и получаем результат
            self.logger.debug(f"Передача сообщения в ConversationService для пользователя {user_id}")
            self.conversation_service.handle_conversation(update, context, self.message_manager)

            # Если ожидаем тему для карты, возвращаем состояние MAP
            if context.user_data.get('waiting_for_map_topic', False):
                self.logger.info(f"Переход в режим карты для пользователя {user_id}")
                return self.MAP

            # В остальных случаях остаемся в режиме беседы
            return self.CONVERSATION

        except Exception as e:
            self.logger.error(f"Ошибка при обработке беседы: {str(e)}")
            try:
                # Отправляем простое сообщение об ошибке без редактирования старого
                error_msg = update.message.reply_text(
                    "Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте задать другой вопрос или вернитесь в меню.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
                )
                self.message_manager.save_message_id(update, context, error_msg.message_id)
            except Exception as reply_error:
                self.logger.error(f"Критическая ошибка: не удалось отправить сообщение об ошибке: {reply_error}")

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
        # Используем сервис тестирования для получения рекомендаций
        return self.test_service.recommend_similar_topics(current_topic, self.api_client)

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

    def clear_chat_command(self, update, context):
        """
        Обрабатывает команду /clear для полной очистки чата.
        Функциональность удаления сообщений отключена.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        user = update.message.from_user

        # Отправляем сообщение о том, что функциональность отключена
        update.message.reply_text("⚠️ Функция очистки чата отключена в текущей версии.")

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
        # Словарь с описаниями распространенных ошибок
        self.ERROR_DESCRIPTIONS = {
            'BadRequest': 'Ошибка в запросе к Telegram API. Возможно, слишком длинное сообщение.',
            'Unauthorized': 'Ошибка авторизации бота. Проверьте токен бота.',
            'TimedOut': 'Превышено время ожидания ответа от Telegram API. Попробуйте позже.',
            'NetworkError': 'Проблемы с сетевым подключением. Проверьте интернет.',
            'ChatMigrated': 'Чат был перенесен на другой сервер.',
            'TelegramError': 'Общая ошибка Telegram API.',
            'AttributeError': 'Ошибка доступа к атрибуту объекта.',
            'TypeError': 'Ошибка типа данных.',
            'ValueError': 'Ошибка значения переменной.',
            'KeyError': 'Ошибка доступа по ключу.',
            'IndexError': 'Ошибка индекса списка.'
        }

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
            if error_type in self.ERROR_DESCRIPTIONS:
                error_message += f"\n{self.ERROR_DESCRIPTIONS[error_type]}"

            update.effective_message.reply_text(
                error_message,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')]])
            )
    def _send_topic_info(self, update, context, topic):
        """Отправляет информацию по теме"""
        try:
            # Создаем функцию обратного вызова для обновления статуса
            def status_callback(message):
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown'
                )

            # Отправляем начальное сообщение о подготовке материала
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔎 *Готовлю информацию по теме:* {topic}\n\nМатериал будет разделен на 5 глав, каждая глава будет отправлена отдельным сообщением.",
                parse_mode='Markdown'
            )

            # Получаем информацию из сервиса
            messages = context.bot_data['topic_service'].get_topic_info(topic, status_callback)

            # Проверяем, есть ли содержимое
            if not messages or len(messages) <= 1:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ Не удалось получить полную информацию по теме '{topic}'. Пожалуйста, попробуйте другую тему.",
                    parse_mode='Markdown'
                )
                return self.back_to_menu(update, context)

            # Отправляем сообщение о начале передачи глав
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📚 *Начинаю отправку глав по теме:* {topic}",
                parse_mode='Markdown'
            )

            # Отправляем каждую главу с небольшой задержкой
            import time
            for i, message in enumerate(messages):
                # Отправляем сообщение
                sent_message = context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True  # Отключаем предпросмотр ссылок
                )

                # Добавляем задержку между сообщениями, чтобы они приходили по порядку
                if i < len(messages) - 1:
                    time.sleep(1)  # 1 секунда между сообщениями

                # Сохраняем ID последнего сообщения в каждой главе для возможности последующей навигации
                context.user_data.setdefault('chapter_messages', {})
                if i > 0:  # Пропускаем оглавление (первое сообщение)
                    context.user_data['chapter_messages'][i] = sent_message.message_id

            # Отправляем кнопки для навигации и взаимодействия
            buttons = [
                [InlineKeyboardButton("📝 Пройти тест по теме", callback_data=f"start_test_{topic}")],
                [InlineKeyboardButton("📊 Сохранить в изученные", callback_data=f"mark_as_learned_{topic}")],
                [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="back_to_menu")]
            ]

            # Добавляем кнопку для создания презентации, если такая возможность есть
            if hasattr(context.bot_data, 'presentation_service'):
                buttons.insert(1, [InlineKeyboardButton("📑 Создать презентацию", callback_data=f"create_presentation_{topic}")])

            reply_markup = InlineKeyboardMarkup(buttons)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ *Материал по теме успешно отправлен*\n\nЧто бы вы хотели сделать дальше?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            # Логируем успешную отправку информации
            self.logger.info(f"Отправлена информация по теме '{topic}' пользователю {update.effective_user.id}")

            return TOPIC

        except Exception as e:
            self.logger.error(f"Ошибка при отправке информации по теме: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Произошла ошибка при получении информации по теме. Пожалуйста, попробуйте позже или выберите другую тему.\n\nОшибка: {str(e)}",
                parse_mode='Markdown'
            )
            return self.back_to_menu(update, context)
    def topic_info_handler(self, update, context):
        """Обработчик для выбора темы из списка и отображения информации"""
        query = update.callback_query
        query.answer()

        # Получаем выбранную тему
        topic_data = query.data.replace("topic_", "")

        # Проверяем, что в контексте есть список тем
        if not hasattr(context, 'topics_list') or not context.topics_list:
            query.edit_message_text("⚠️ Произошла ошибка: список тем не найден. Выберите /topics заново.")
            return ConversationHandler.END

        # Ищем выбранную тему в списке
        selected_topic = None
        for topic in context.topics_list:
            topic_number = topic.split('.')[0]
            if topic_data == topic_number:
                selected_topic = topic
                break

        if not selected_topic:
            query.edit_message_text("⚠️ Тема не найдена. Выберите /topics заново.")
            return ConversationHandler.END

        # Получаем номер и текст темы
        topic_number, topic_text = selected_topic.split('. ', 1)

        # Отправляем сообщение о начале загрузки
        query.edit_message_text(f"🔍 Проверяю кэш для темы: *{topic_text}*...", 
                                parse_mode=telegram.constants.ParseMode.MARKDOWN)

        # Функция для обновления сообщения о статусе загрузки
        def update_status(status_text):
            try:
                context.bot.edit_message_text(
                    text=status_text,
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
            except Exception as e:
                self.logger.error(f"Ошибка при обновлении статуса: {e}")

        # Получаем кэш-сервис из контекста бота (он должен быть добавлен при инициализации)
        text_cache_service = getattr(context.bot_data, 'text_cache_service', None)

        # Получаем информацию о теме (из кэша или генерируем новую)
        topic_messages = self.topic_service.get_cached_topic_info(
            topic_text, 
            update_callback=update_status,
            text_cache_service=text_cache_service
        )

        # Отправляем сообщения с информацией по теме
        self.message_manager.send_topic_messages(update, context, topic_messages)

    def _send_topic_info(self, update, context, topic):
        """Отправляет информацию по теме"""
        try:
            # Создаем функцию обратного вызова для обновления статуса
            def status_callback(message):
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown'
                )

            # Отправляем начальное сообщение о подготовке материала
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔎 *Готовлю информацию по теме:* {topic}\n\nМатериал будет разделен на 5 глав, каждая глава будет отправлена отдельным сообщением.",
                parse_mode='Markdown'
            )

            # Получаем информацию из сервиса
            messages = context.bot_data['topic_service'].get_topic_info(topic, status_callback)

            # Проверяем, есть ли содержимое
            if not messages or len(messages) <= 1:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ Не удалось получить полную информацию по теме '{topic}'. Пожалуйста, попробуйте другую тему.",
                    parse_mode='Markdown'
                )
                return self.back_to_menu(update, context)

            # Отправляем сообщение о начале передачи глав
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📚 *Начинаю отправку глав по теме:* {topic}",
                parse_mode='Markdown'
            )

            # Отправляем каждую главу с небольшой задержкой
            import time
            for i, message in enumerate(messages):
                # Отправляем сообщение
                sent_message = context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True  # Отключаем предпросмотр ссылок
                )

                # Добавляем задержку между сообщениями, чтобы они приходили по порядку
                if i < len(messages) - 1:
                    time.sleep(1)  # 1 секунда между сообщениями

                # Сохраняем ID последнего сообщения в каждой главе для возможности последующей навигации
                context.user_data.setdefault('chapter_messages', {})
                if i > 0:  # Пропускаем оглавление (первое сообщение)
                    context.user_data['chapter_messages'][i] = sent_message.message_id

            # Отправляем кнопки для навигации и взаимодействия
            buttons = [
                [InlineKeyboardButton("📝 Пройти тест по теме", callback_data=f"start_test_{topic}")],
                [InlineKeyboardButton("📊 Сохранить в изученные", callback_data=f"mark_as_learned_{topic}")],
                [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="back_to_menu")]
            ]

            # Добавляем кнопку для создания презентации, если такая возможность есть
            if hasattr(context.bot_data, 'presentation_service'):
                buttons.insert(1, [InlineKeyboardButton("📑 Создать презентацию", callback_data=f"create_presentation_{topic}")])

            reply_markup = InlineKeyboardMarkup(buttons)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ *Материал по теме успешно отправлен*\n\nЧто бы вы хотели сделать дальше?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            # Логируем успешную отправку информации
            self.logger.info(f"Отправлена информация по теме '{topic}' пользователю {update.effective_user.id}")

            return TOPIC

        except Exception as e:
            self.logger.error(f"Ошибка при отправке информации по теме: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Произошла ошибка при получении информации по теме. Пожалуйста, попробуйте позже или выберите другую тему.\n\nОшибка: {str(e)}",
                parse_mode='Markdown'
            )
            return self.back_to_menu(update, context)
    def topic_info_handler(self, update, context):
        """Обработчик для выбора темы из списка и отображения информации"""
        query = update.callback_query
        query.answer()

        # Получаем выбранную тему
        topic_data = query.data.replace("topic_", "")

        # Проверяем, что в контексте есть список тем
        if not hasattr(context, 'topics_list') or not context.topics_list:
            query.edit_message_text("⚠️ Произошла ошибка: список тем не найден. Выберите /topics заново.")
            return ConversationHandler.END

        # Ищем выбранную тему в списке
        selected_topic = None
        for topic in context.topics_list:
            topic_number = topic.split('.')[0]
            if topic_data == topic_number:
                selected_topic = topic
                break

        if not selected_topic:
            query.edit_message_text("⚠️ Тема не найдена. Выберите /topics заново.")
            return ConversationHandler.END

        # Получаем номер и текст темы
        topic_number, topic_text = selected_topic.split('. ', 1)

        # Отправляем сообщение о начале загрузки
        query.edit_message_text(f"🔍 Проверяю кэш для темы: *{topic_text}*...", 
                                parse_mode=telegram.constants.ParseMode.MARKDOWN)

        # Функция для обновления сообщения о статусе загрузки
        def update_status(status_text):
            try:
                context.bot.edit_message_text(
                    text=status_text,
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
            except Exception as e:
                self.logger.error(f"Ошибка при обновлении статуса: {e}")

        # Получаем кэш-сервис из контекста бота (он должен быть добавлен при инициализации)
        text_cache_service = getattr(context.bot_data, 'text_cache_service', None)

        # Получаем информацию о теме (из кэша или генерируем новую)
        topic_messages = self.topic_service.get_cached_topic_info(
            topic_text, 
            update_callback=update_status,
            text_cache_service=text_cache_service
        )

        # Отправляем сообщения с информацией по теме
        self.message_manager.send_topic_messages(update, context, topic_messages)

    def _send_topic_info(self, update, context, topic):
        """Отправляет информацию по теме"""
        try:
            # Создаем функцию обратного вызова для обновления статуса
            def status_callback(message):
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown'
                )

            # Отправляем начальное сообщение о подготовке материала
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔎 *Готовлю информацию по теме:* {topic}\n\nМатериал будет разделен на 5 глав, каждая глава будет отправлена отдельным сообщением.",
                parse_mode='Markdown'
            )

            # Получаем информацию из сервиса
            messages = context.bot_data['topic_service'].get_topic_info(topic, status_callback)

            # Проверяем, есть ли содержимое
            if not messages or len(messages) <= 1:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ Не удалось получить полную информацию по теме '{topic}'. Пожалуйста, попробуйте другую тему.",
                    parse_mode='Markdown'
                )
                return self.back_to_menu(update, context)

            # Отправляем сообщение о начале передачи глав
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📚 *Начинаю отправку глав по теме:* {topic}",
                parse_mode='Markdown'
            )

            # Отправляем каждую главу с небольшой задержкой
            import time
            for i, message in enumerate(messages):
                # Отправляем сообщение
                sent_message = context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True  # Отключаем предпросмотр ссылок
                )

                # Добавляем задержку между сообщениями, чтобы они приходили по порядку
                if i < len(messages) - 1:
                    time.sleep(1)  # 1 секунда между сообщениями

                # Сохраняем ID последнего сообщения в каждой главе для возможности последующей навигации
                context.user_data.setdefault('chapter_messages', {})
                if i > 0:  # Пропускаем оглавление (первое сообщение)
                    context.user_data['chapter_messages'][i] = sent_message.message_id

            # Отправляем кнопки для навигации и взаимодействия
            buttons = [
                [InlineKeyboardButton("📝 Пройти тест по теме", callback_data=f"start_test_{topic}")],
                [InlineKeyboardButton("📊 Сохранить в изученные", callback_data=f"mark_as_learned_{topic}")],
                [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="back_to_menu")]
            ]

            # Добавляем кнопку для создания презентации, если такая возможность есть
            if hasattr(context.bot_data, 'presentation_service'):
                buttons.insert(1, [InlineKeyboardButton("📑 Создать презентацию", callback_data=f"create_presentation_{topic}")])

            reply_markup = InlineKeyboardMarkup(buttons)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ *Материал по теме успешно отправлен*\n\nЧто бы вы хотели сделать дальше?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            # Логируем успешную отправку информации
            self.logger.info(f"Отправлена информация по теме '{topic}' пользователю {update.effective_user.id}")

            return TOPIC

        except Exception as e:
            self.logger.error(f"Ошибка при отправке информации по теме: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Произошла ошибка при получении информации по теме. Пожалуйста, попробуйте позже или выберите другую тему.\n\nОшибка: {str(e)}",
                parse_mode='Markdown'
            )
            return self.back_to_menu(update, context)
    def topic_info_handler(self, update, context):
        """Обработчик для выбора темы из списка и отображения информации"""
        query = update.callback_query
        query.answer()

        # Получаем выбранную тему
        topic_data = query.data.replace("topic_", "")

        # Проверяем, что в контексте есть список тем
        if not hasattr(context, 'topics_list') or not context.topics_list:
            query.edit_message_text("⚠️ Произошла ошибка: список тем не найден. Выберите /topics заново.")
            return ConversationHandler.END

        # Ищем выбранную тему в списке
        selected_topic = None
        for topic in context.topics_list:
            topic_number = topic.split('.')[0]
            if topic_data == topic_number:
                selected_topic = topic
                break

        if not selected_topic:
            query.edit_message_text("⚠️ Тема не найдена. Выберите /topics заново.")
            return ConversationHandler.END

        # Получаем номер и текст темы
        topic_number, topic_text = selected_topic.split('. ', 1)

        # Отправляем сообщение о начале загрузки
        query.edit_message_text(f"🔍 Проверяю кэш для темы: *{topic_text}*...", 
                                parse_mode=telegram.constants.ParseMode.MARKDOWN)

        # Функция для обновления сообщения о статусе загрузки
        def update_status(status_text):
            try:
                context.bot.edit_message_text(
                    text=status_text,
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
            except Exception as e:
                self.logger.error(f"Ошибка при обновлении статуса: {e}")

        # Получаем кэш-сервис из контекста бота (он должен быть добавлен при инициализации)
        text_cache_service = getattr(context.bot_data, 'text_cache_service', None)

        # Получаем информацию о теме (из кэша или генерируем новую)
        topic_messages = self.topic_service.get_cached_topic_info(
            topic_text, 
            update_callback=update_status,
            text_cache_service=text_cache_service
        )

        # Отправляем сообщения с информацией по теме
        self.message_manager.send_topic_messages(update, context, topic_messages)

    def _send_topic_info(self, update, context, topic):
        """Отправляет информацию по теме"""
        try:
            # Создаем функцию обратного вызова для обновления статуса
            def status_callback(message):
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown'
                )

            # Отправляем начальное сообщение о подготовке материала
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔎 *Готовлю информацию по теме:* {topic}\n\nМатериал будет разделен на 5 глав, каждая глава будет отправлена отдельным сообщением.",
                parse_mode='Markdown'
            )

            # Получаем информацию из сервиса
            messages = context.bot_data['topic_service'].get_topic_info(topic, status_callback)

            # Проверяем, есть ли содержимое
            if not messages or len(messages) <= 1:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ Не удалось получить полную информацию по теме '{topic}'. Пожалуйста, попробуйте другую тему.",
                    parse_mode='Markdown'
                )
                return self.back_to_menu(update, context)

            # Отправляем сообщение о начале передачи глав
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📚 *Начинаю отправку глав по теме:* {topic}",
                parse_mode='Markdown'
            )

            # Отправляем каждую главу с небольшой задержкой
            import time
            for i, message in enumerate(messages):
                # Отправляем сообщение
                sent_message = context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True  # Отключаем предпросмотр ссылок
                )

                # Добавляем задержку между сообщениями, чтобы они приходили по порядку
                if i < len(messages) - 1:
                    time.sleep(1)  # 1 секунда между сообщениями

                # Сохраняем ID последнего сообщения в каждой главе для возможности последующей навигации
                context.user_data.setdefault('chapter_messages', {})
                if i > 0:  # Пропускаем оглавление (первое сообщение)
                    context.user_data['chapter_messages'][i] = sent_message.message_id

            # Отправляем кнопки для навигации и взаимодействия
            buttons = [
                [InlineKeyboardButton("📝 Пройти тест по теме", callback_data=f"start_test_{topic}")],
                [InlineKeyboardButton("📊 Сохранить в изученные", callback_data=f"mark_as_learned_{topic}")],
                [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="back_to_menu")]
            ]

            # Добавляем кнопку для создания презентации, если такая возможность есть
            if hasattr(context.bot_data, 'presentation_service'):
                buttons.insert(1, [InlineKeyboardButton("📑 Создать презентацию", callback_data=f"create_presentation_{topic}")])

            reply_markup = InlineKeyboardMarkup(buttons)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ *Материал по теме успешно отправлен*\n\nЧто бы вы хотели сделать дальше?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            # Логируем успешную отправку информации
            self.logger.info(f"Отправлена информация по теме '{topic}' пользователю {update.effective_user.id}")

            return TOPIC

        except Exception as e:
            self.logger.error(f"Ошибка при отправке информации по теме: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Произошла ошибка при получении информации по теме. Пожалуйста, попробуйте позже или выберите другую тему.\n\nОшибка: {str(e)}",
                parse_mode='Markdown'
            )
            return self.back_to_menu(update, context)
    def topic_info_handler(self, update, context):
        """Обработчик для выбора темы из списка и отображения информации"""
        query = update.callback_query
        query.answer()

        # Получаем выбранную тему
        topic_data = query.data.replace("topic_", "")

        # Проверяем, что в контексте есть список тем
        if not hasattr(context, 'topics_list') or not context.topics_list:
            query.edit_message_text("⚠️ Произошла ошибка: список тем не найден. Выберите /topics заново.")
            return ConversationHandler.END

        # Ищем выбранную тему в списке
        selected_topic = None
        for topic in context.topics_list:
            topic_number = topic.split('.')[0]
            if topic_data == topic_number:
                selected_topic = topic
                break

        if not selected_topic:
            query.edit_message_text("⚠️ Тема не найдена. Выберите /topics заново.")
            return ConversationHandler.END

        # Получаем номер и текст темы
        topic_number, topic_text = selected_topic.split('. ', 1)

        # Отправляем сообщение о начале загрузки
        query.edit_message_text(f"🔍 Проверяю кэш для темы: *{topic_text}*...", 
                                parse_mode=telegram.constants.ParseMode.MARKDOWN)

        # Функция для обновления сообщения о статусе загрузки
        def update_status(status_text):
            try:
                context.bot.edit_message_text(
                    text=status_text,
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
            except Exception as e:
                self.logger.error(f"Ошибка при обновлении статуса: {e}")

        # Получаем кэш-сервис из контекста бота (он должен быть добавлен при инициализации)
        text_cache_service = getattr(context.bot_data, 'text_cache_service', None)

        # Получаем информацию о теме (из кэша или генерируем новую)
        topic_messages = self.topic_service.get_cached_topic_info(
            topic_text, 
            update_callback=update_status,
            text_cache_service=text_cache_service
        )

        # Отправляем сообщения с информацией по теме
        self.message_manager.send_topic_messages(update, context, topic_messages)