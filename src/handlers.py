import telegram
import re
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

        # Инициализируем карту исторических событий
        from src.history_map import HistoryMap
        self.history_map = HistoryMap(logger)

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
        query_data = query.data

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
        elif query_data == 'download_detailed_presentation':
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
        elif query_data == 'history_map':
            # Обработка кнопки интерактивной карты
            user_id = query.from_user.id
            self.logger.info(f"Пользователь {user_id} запросил историческую карту")

            # Создаем клавиатуру для выбора категории событий на карте
            categories = self.history_map.get_categories()
            keyboard = []

            # Добавляем кнопки для каждой категории (максимум 10 на странице)
            category_buttons = []
            for i, category in enumerate(categories[:10]):
                category_buttons.append(InlineKeyboardButton(f"📍 {category}", callback_data=f'map_category_{category}'))
                # Создаем ряды по 2 кнопки
                if i % 2 == 1 or i == len(categories[:10])-1:
                    keyboard.append(category_buttons)
                    category_buttons = []

            # Добавляем кнопки навигации и функций
            keyboard.append([InlineKeyboardButton("📋 Больше категорий ▶️", callback_data='map_more_categories')])
            keyboard.append([InlineKeyboardButton("🔍 Поиск по теме", callback_data='map_search_topic')])
            keyboard.append([InlineKeyboardButton("🎲 Случайные события", callback_data='map_random')])
            keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')])

            query.edit_message_text(
                "🗺️ *Интерактивная карта исторических событий*\n\n"
                "Выберите категорию исторических событий для отображения на карте, "
                "воспользуйтесь поиском по конкретной теме или "
                "посмотрите случайные события из разных периодов истории России.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return self.MAP

        elif query_data.startswith('map_category_'):
            # Обработка выбора категории на карте
            category = query_data[13:]  # map_category_{category}
            user_id = query.from_user.id
            self.logger.info(f"Пользователь {user_id} выбрал категорию карты: {category}")

            # Добавляем клавиатуру для получения карты
            keyboard = [
                [InlineKeyboardButton("🗺️ Получить карту", callback_data=f'map_img_{category}')],
                [InlineKeyboardButton("🔙 Назад к категориям", callback_data='history_map')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем сообщение с выбором формата карты
            query.edit_message_text(
                f"📍 *Категория: {category}*\n\n"
                f"Вы выбрали категорию исторических событий: *{category}*\n\n"
                f"Выберите формат карты:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return self.MAP

        elif query_data.startswith('map_url_'):
            category = query_data.replace('map_url_', '')

            # Генерируем и отправляем изображение карты вместо URL
            status_message = context.bot.send_message(
                chat_id=user_id,
                text=f"🔄 Генерация изображения карты для категории «{category}»...",
                parse_mode='HTML'
            )

            map_image_path = self.history_map.generate_map_image(category=category)

            if map_image_path and os.path.exists(map_image_path):
                # Отправляем изображение карты
                with open(map_image_path, 'rb') as img:
                    context.bot.send_photo(
                        chat_id=user_id,
                        photo=img,
                        caption=f"🗺️ Карта исторических событий: {category}",
                        parse_mode='HTML'
                    )
            else:
                context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Не удалось сгенерировать карту. Пожалуйста, попробуйте позже.",
                    parse_mode='HTML'
                )

            context.bot.delete_message(chat_id=user_id, message_id=status_message.message_id)
            return self.MAP

        elif query_data.startswith('map_img_'):
            category = query_data.replace('map_img_', '')

            # Отправляем сообщение о том, что генерируем карту
            status_message = context.bot.send_message(
                chat_id=user_id,
                text=f"🔄 Генерация карты для категории «{category}»...",
                parse_mode='HTML'
            )

            try:
                # Пробуем сначала сгенерировать изображение карты
                map_path = self.history_map.generate_map_image(category=category)

                if map_path and os.path.exists(map_path):
                    # Отправляем изображение
                    try:
                        with open(map_path, 'rb') as img_file:
                            context.bot.send_photo(
                                chat_id=user_id,
                                photo=img_file,
                                caption=f"🗺️ Карта исторических событий категории «{category}»",
                                parse_mode='HTML'
                            )
                    except Exception as img_error:
                        self.logger.error(f"Ошибка при отправке изображения карты: {img_error}")
                        # Пробуем отправить резервное стандартное изображение
                        default_map_path = 'static/default_map.png'
                        if os.path.exists(default_map_path):
                            try:
                                with open(default_map_path, 'rb') as default_img:
                                    context.bot.send_photo(
                                        chat_id=user_id,
                                        photo=default_img,
                                        caption=f"🗺️ Стандартная карта (не удалось сгенерировать специальную карту для категории «{category}»)",
                                        parse_mode='HTML'
                                    )
                            except Exception as e:
                                context.bot.send_message(
                                    chat_id=user_id,
                                    text=f"❌ Произошла ошибка при отправке карты: {str(e)}",
                                    parse_mode='HTML'
                                )
                        else:
                            context.bot.send_message(
                                chat_id=user_id,
                                text=f"❌ Не удалось сгенерировать и отправить карту.",
                                parse_mode='HTML'
                            )

                    # Удаляем сообщение о генерации
                    try:
                        context.bot.delete_message(
                            chat_id=user_id,
                            message_id=status_message.message_id
                        )
                    except Exception as delete_error:
                        self.logger.error(f"Не удалось удалить сообщение о генерации: {delete_error}")

                    # Удаляем файл карты после отправки
                    try:
                        os.remove(map_path)
                        self.logger.info(f"Файл карты удален: {map_path}")
                    except Exception as e:
                        self.logger.error(f"Не удалось удалить файл карты {map_path}: {e}")

                    self.logger.info(f"Пользователь {user_id} получил карту категории {category}")
                else:
                    # Если не удалось сгенерировать карту, отправляем стандартную
                    default_map_path = 'static/default_map.png'
                    if os.path.exists(default_map_path):
                        try:
                            with open(default_map_path, 'rb') as default_img:
                                context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=default_img,
                                    caption=f"🗺️ Стандартная карта (не удалось сгенерировать специальную карту для категории «{category}»)",
                                    parse_mode='HTML'
                                )
                        except Exception as e:
                            context.bot.send_message(
                                chat_id=user_id,
                                text=f"❌ Не удалось отправить карту: {str(e)}",
                                parse_mode='HTML'
                            )
                    else:
                        context.bot.send_message(
                            chat_id=user_id,
                            text=f"❌ Не удалось сгенерировать карту для категории «{category}». Пожалуйста, попробуйте позже.",
                            parse_mode='HTML'
                        )

                    # Удаляем сообщение о генерации
                    context.bot.delete_message(
                        chat_id=user_id, 
                        message_id=status_message.message_id
                    )
            except Exception as e:
                self.logger.error(f"Ошибка при генерации карты: {e}")
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ Произошла ошибка при генерации карты: {str(e)}. Пожалуйста, попробуйте позже.",
                    parse_mode='HTML'
                )

                # Удаляем сообщение о генерации
                try:
                    context.bot.delete_message(
                        chat_id=user_id, 
                        message_id=status_message.message_id
                    )
                except:
                    pass

            # Запускаем очистку старых карт
            try:
                self.history_map.clean_old_maps()
            except Exception as e:
                self.logger.error(f"Ошибка при очистке старых карт: {e}")

            return self.MAP

        elif query_data == 'map_more_categories':
            # Показываем дополнительные категории
            categories = self.history_map.get_categories()
            keyboard = []

            # Проверяем есть ли дополнительные категории
            if len(categories) > 10:
                # Показываем следующие категории
                remaining_categories = categories[10:]

                # Формируем ряды кнопок (по 2 в ряду)
                for i in range(0, len(remaining_categories), 2):
                    row = []
                    # Добавляем первую кнопку
                    category = remaining_categories[i]
                    row.append(InlineKeyboardButton(f"📍 {category}", callback_data=f'map_category_{category}'))

                    # Добавляем вторую кнопку, если она есть
                    if i + 1 < len(remaining_categories):
                        category = remaining_categories[i + 1]
                        row.append(InlineKeyboardButton(f"📍 {category}", callback_data=f'map_category_{category}'))

                    keyboard.append(row)
            else:
                # Если дополнительных категорий нет, показываем сообщение
                keyboard.append([InlineKeyboardButton("⚠️ Дополнительных категорий нет", callback_data='history_map')])

            # Добавляем навигационные кнопки
            keyboard.append([InlineKeyboardButton("◀️ Назад к основным категориям", callback_data='history_map')])
            keyboard.append([InlineKeyboardButton("🔍 Поиск по теме", callback_data='map_search_topic')])
            keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data='back_to_menu')])

            try:
                query.edit_message_text(
                    "🗺️ *Дополнительные категории исторических событий*\n\n"
                    "Выберите одну из дополнительных категорий для отображения на карте.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e:
                self.logger.error(f"Ошибка при редактировании сообщения с дополнительными категориями: {e}")
                # Если не удалось отредактировать, отправляем новое сообщение
                query.message.reply_text(
                    "🗺️ *Дополнительные категории исторических событий*\n\n"
                    "Выберите одну из дополнительных категорий для отображения на карте.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            return self.MAP

        elif query_data == 'map_search_topic':
            # Предлагаем пользователю ввести тему для генерации карты с более подробными инструкциями
            query.edit_message_text(
                "🔍 *Поиск исторических событий по теме*\n\n"
                "Введите интересующую вас тему или ключевое слово для поиска исторических событий.\n\n"
                "Примеры запросов для детализированных карт:\n"
                "• Конкретные личности: «Петр I», «Екатерина II», «Александр Невский»\n"
                "• Военные события: «Крымская война», «Отечественная война 1812», «Полтавская битва»\n"
                "• Исторические процессы: «освоение Сибири», «индустриализация», «реформы»\n"
                "• География: «основание городов», «Москва», «Северо-Запад России»\n"
                "• Периоды: «18 век», «советский период», «правление Романовых»\n\n"
                "Бот найдет соответствующие события и отобразит их на детализированной карте с пояснениями.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад к категориям", callback_data='history_map')]]),
                parse_mode='Markdown'
            )

            # Устанавливаем флаг ожидания ввода пользовательской темы
            context.user_data['waiting_for_map_topic'] = True
            return self.MAP

        elif query_data == 'map_random':
            # Получаем больше случайных событий для повышения детализации
            random_events = self.history_map.get_random_events(8)

            # Отправляем сообщение о генерации
            status_message = context.bot.send_message(
                chat_id=user_id,
                text="🔄 Генерация детализированной карты со случайными событиями...",
                parse_mode='HTML'
            )

            # Генерируем изображение карты
            map_image_path = self.history_map.generate_map_image(events=random_events)

            if map_image_path and os.path.exists(map_image_path):
                # Отправляем изображение карты
                with open(map_image_path, 'rb') as img:
                    context.bot.send_photo(
                        chat_id=user_id,
                        photo=img,
                        caption="🗺️ Детализированная карта случайных исторических событий России\n"
                               "Номера на карте соответствуют подписям внизу изображения.",
                        parse_mode='HTML'
                    )

                # Удаляем сообщение о генерации
                context.bot.delete_message(
                    chat_id=user_id,
                    message_id=status_message.message_id
                )

                # Удаляем изображение карты после отправки
                try:
                    os.remove(map_image_path)
                except Exception as e:
                    self.logger.error(f"Не удалось удалить файл карты {map_image_path}: {e}")

                self.logger.info(f"Пользователь {user_id} получил детализированную карту со случайными событиями")
            else:
                # Если не удалось сгенерировать карту, отправляем сообщение об ошибке
                context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message.message_id,
                    text="❌ Не удалось сгенерировать изображение карты. Попробуйте позже.",
                    parse_mode='HTML'
                )
                self.logger.error(f"Не удалось сгенерировать изображение карты для пользователя {user_id}")

            return self.MAP

        elif query_data == 'map_image':
            # Отправляем сообщение о том, что генерируем карту
            status_message = context.bot.send_message(
                chat_id=user_id,
                text="🔄 Генерация изображения карты...",
                parse_mode='HTML'
            )

            # Генерируем изображение карты всех событий
            map_image_path = self.history_map.generate_map_image()

            if map_image_path and os.path.exists(map_image_path):
                # Отправляем изображение карты
                with open(map_image_path, 'rb') as img:
                    context.bot.send_photo(
                        chat_id=user_id,
                        photo=img,
                        caption="🗺️ Интерактивная карта исторических событий России",
                        parse_mode='HTML'
                    )

                # Удаляем сообщение о генерации
                context.bot.delete_message(
                    chat_id=user_id,
                    message_id=status_message.message_id
                )

                # Удаляем изображение карты после отправки
                os.remove(map_image_path)

                self.logger.info(f"Пользователь {user_id} получил изображение карты с историческими событиями")
            else:
                # Если не удалось сгенерировать карту, отправляем сообщение об ошибке
                context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message.message_id,
                    text="❌ Не удалось сгенерировать изображение карты. Попробуйте позже или воспользуйтесь ссылкой на карту.",
                    parse_mode='HTML'
                )
                self.logger.error(f"Не удалось сгенерировать изображение карты для пользователя {user_id}")
            return self.MAP

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
        elif query_data == 'test':
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
                
                # Сбрасываем переменные для хранения вопросов
                valid_questions = []
                display_questions = []

                # Прежде всего проверим, получили ли мы данные в виде обычного текста
                if isinstance(test_data, str):
                    # Преобразуем текст в список вопросов, разделенных пустыми строками или номерами
                    raw_questions = re.split(r'\n\s*\n|\n\d+[\.\)]\s+', test_data)
                    processed_questions = []
                    
                    for q in raw_questions:
                        q = q.strip()
                        if q and len(q) > 10 and ('?' in q or 'Вопрос' in q):
                            # Удаляем любые начальные цифры в начале вопроса
                            q = re.sub(r'^(\d+[\.\)]|\d+\.)\s*', '', q).strip()
                            processed_questions.append(q)
                            
                    if processed_questions:
                        valid_questions = processed_questions
                        display_questions = processed_questions
                    else:
                        raise ValueError("Не удалось извлечь вопросы из текстового формата")
                
                # Проверяем структуру полученных данных если это словарь
                elif isinstance(test_data, dict):
                    # Случай 1: Стандартный формат с оригинальными и отображаемыми вопросами
                    if 'original_questions' in test_data and 'display_questions' in test_data:
                        if (isinstance(test_data['original_questions'], list) and 
                            isinstance(test_data['display_questions'], list) and
                            len(test_data['original_questions']) > 0):
                            valid_questions = test_data['original_questions']
                            display_questions = test_data['display_questions']
                        else:
                            raise ValueError("Пустой список вопросов или неверный формат вопросов")
                            
                    # Случай 2: Ошибка в ответе API
                    elif 'status' in test_data and test_data['status'] == 'error':
                        error_msg = test_data.get('content', 'Ошибка API')
                        self.logger.warning(f"Ошибка API при генерации теста: {error_msg}")
                        raise ValueError(f"Не удалось сгенерировать тест: {error_msg}")
                        
                    # Случай 3: Вопросы в поле content
                    elif 'content' in test_data:
                        # Проверяем тип content - список
                        if isinstance(test_data['content'], list) and len(test_data['content']) > 0:
                            valid_questions = test_data['content']
                            display_questions = test_data['content']
                        # Проверяем тип content - строка (требует парсинга)
                        elif isinstance(test_data['content'], str) and len(test_data['content']) > 0:
                            # Разделяем текст на вопросы, используя пустые строки или номера вопросов как разделители
                            raw_questions = re.split(r'\n\s*\n|\n\d+[\.\)]\s+', test_data['content'])
                            processed_questions = []
                            
                            for q in raw_questions:
                                q = q.strip()
                                if q and len(q) > 10 and ('?' in q or 'Вопрос' in q):
                                    # Удаляем любые начальные цифры
                                    q = re.sub(r'^(\d+[\.\)]|\d+\.)\s*', '', q).strip()
                                    processed_questions.append(q)
                                    
                            if processed_questions:
                                valid_questions = processed_questions
                                display_questions = processed_questions
                            else:
                                raise ValueError("Не удалось извлечь вопросы из текстового формата в поле content")
                        else:
                            raise ValueError("Поле content существует, но не содержит списка вопросов или строки")
                        
                    # Случай 4: Поиск вопросов в любом списковом поле
                    else:
                        found_questions = False
                        for field in test_data:
                            # Проверяем, есть ли в поле список
                            if isinstance(test_data[field], list) and len(test_data[field]) > 0:
                                # Проверяем, что элементы списка - строки
                                if all(isinstance(q, str) for q in test_data[field]):
                                    valid_questions = test_data[field]
                                    display_questions = test_data[field]
                                    found_questions = True
                                    break
                            # Проверяем, есть ли в поле строка, которую можно разделить на вопросы
                            elif isinstance(test_data[field], str) and len(test_data[field]) > 100:
                                # Разделяем текст на вопросы
                                raw_questions = re.split(r'\n\s*\n|\n\d+[\.\)]\s+', test_data[field])
                                processed_questions = []
                                
                                for q in raw_questions:
                                    q = q.strip()
                                    if q and len(q) > 10 and ('?' in q or 'Вопрос' in q):
                                        q = re.sub(r'^(\d+[\.\)]|\d+\.)\s*', '', q).strip()
                                        processed_questions.append(q)
                                        
                                if processed_questions:
                                    valid_questions = processed_questions
                                    display_questions = processed_questions
                                    found_questions = True
                                    break
                        
                        if not found_questions:
                            self.logger.warning(f"Неожиданная структура данных теста: {test_data}")
                            raise ValueError("Неверный формат данных теста: отсутствуют вопросы или неверный формат")
                
                # Случай 5: test_data - это список вопросов
                elif isinstance(test_data, list) and len(test_data) > 0:
                    # Проверяем, что элементы списка - строки
                    if all(isinstance(q, str) for q in test_data):
                        valid_questions = test_data
                        display_questions = test_data
                    else:
                        # Попытка извлечь строки из смешанного списка
                        string_questions = [str(q) for q in test_data if q]
                        if string_questions:
                            valid_questions = string_questions
                            display_questions = string_questions
                        else:
                            raise ValueError("Список вопросов содержит элементы неверного типа")
                        
                # Случай 6: Неверный формат данных
                else:
                    self.logger.warning(f"Неожиданный формат test_data: {type(test_data).__name__}")
                    raise ValueError(f"Неверный формат данных теста: получен {type(test_data).__name__}")

                # Принудительно создадим вопросы, если их не удалось получить
                if not valid_questions:
                    # Запрашиваем простой набор вопросов у API напрямую
                    prompt = f"Создай 5 простых вопросов для тестирования по теме '{topic}'. Каждый вопрос должен иметь 4 варианта ответа (1-4) и обязательно указанный правильный ответ в формате 'Правильный ответ: X'. Пронумеруй вопросы."
                    response = self.api_client.ask_grok(prompt, use_cache=False)
                    
                    # Разделяем текст на вопросы, используя либо пустые строки, либо номера
                    raw_questions = re.split(r'\n\s*\n|\n\d+[\.\)]\s+', response)
                    processed_questions = []
                    
                    for q in raw_questions:
                        q = q.strip()
                        if q and len(q) > 10 and ('?' in q or 'Вопрос' in q):
                            # Удаляем начальные цифры, если они есть
                            q = re.sub(r'^(\d+[\.\)]|\d+\.)\s*', '', q).strip()
                            processed_questions.append(q)
                            
                    if processed_questions:
                        valid_questions = processed_questions
                        display_questions = processed_questions
                    else:
                        raise ValueError("Не удалось создать вопросы даже с прямым запросом к API")

                # Валидация данных: проверяем наличие правильных ответов
                valid_test = False
                for question in valid_questions:
                    if re.search(r"Правильный ответ:\s*[1-4]", question):
                        valid_test = True
                        break
                
                if not valid_test:
                    # Если правильных ответов нет, добавим их автоматически
                    self.logger.warning("В вопросах не найдены правильные ответы, добавляем их")
                    
                    new_questions = []
                    for i, q in enumerate(valid_questions):
                        # Добавляем правильный ответ к каждому вопросу, если его нет
                        if not re.search(r"Правильный ответ:", q):
                            # Выбираем случайное число от 1 до 4
                            import random
                            correct_answer = random.randint(1, 4)
                            q += f"\nПравильный ответ: {correct_answer}"
                        new_questions.append(q)
                    
                    valid_questions = new_questions
                    display_questions = new_questions

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

                # Отправляем сообщение с началом теста
                query.edit_message_text(
                    f"📝 *Тест по теме: {topic}*\n\nНачинаем тест из {len(valid_questions)} вопросов! Вот первый вопрос:",
                    parse_mode='Markdown'
                )
                
                # Проверяем существование первого вопроса
                if len(display_questions) > 0:
                    query.message.reply_text(display_questions[0])
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
                    f"Произошла ошибка при генерации теста: {e}. Пожалуйста, попробуйте еще раз.", 
                    reply_markup=self.ui_manager.main_menu()
                )
            return self.ANSWER
        elif query_data == 'more_topics':
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
        elif query_data == 'end_test' or query_data == 'cancel':
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
                        result = self.content_service.get_topic_info(topic, update_message)

                        # Проверяем формат полученных данных
                        if isinstance(result, dict):
                            # Обрабатываем словарь (dict)
                            if result.get("status") == "success":
                                content = result.get("content", "")

                                # Разбиваем длинный контент на части, если нужно
                                if len(content) > 4000:
                                    messages = [content[i:i+4000] for i in range(0, len(content), 4000)]
                                else:
                                    messages = [content]

                                try:
                                    # Пробуем отредактировать первое сообщение
                                    query.edit_message_text(
                                        f"📚 *{topic}*\n\n{messages[0]}", 
                                        parse_mode='Markdown'
                                    )
                                except Exception as e:
                                    # Если редактирование не удалось, отправляем как новое сообщение
                                    self.logger.warning(f"Не удалось отредактировать сообщение: {e}")
                                    query.message.reply_text(
                                        f"📚 *{topic}*\n\n{messages[0]}", 
                                        parse_mode='Markdown'
                                    )

                                # Отправляем остальные части как новые сообщения, если они есть
                                for msg in messages[1:]:
                                    query.message.reply_text(msg, parse_mode='Markdown')
                            else:
                                # Обработка ошибки
                                error_message = result.get("content", f"Не удалось получить информацию по теме: {topic}")
                                query.edit_message_text(
                                    f"⚠️ {error_message}",
                                    parse_mode='Markdown'
                                )
                        elif isinstance(result, list) and len(result) > 0:
                            # Обрабатываем список (list)
                            try:
                                # Пробуем отредактировать первое сообщение
                                query.edit_message_text(result[0], parse_mode='Markdown')
                            except Exception as e:
                                # Если редактирование не удалось, отправляем как новое сообщение
                                self.logger.warning(f"Не удалось отредактировать сообщение: {e}")
                                query.message.reply_text(result[0], parse_mode='Markdown')

                            # Отправляем остальные сообщения как новые
                            for msg in result[1:]:
                                query.message.reply_text(msg, parse_mode='Markdown')
                        elif isinstance(result, list) and len(result) == 0:
                            # Обработка пустого списка сообщений
                            self.logger.warning(f"Получен пустой список сообщений для темы: {topic}")
                            query.edit_message_text(
                                f"К сожалению, не удалось получить информацию по теме *{topic}*. Пожалуйста, попробуйте выбрать другую тему.",
                                parse_mode='Markdown'
                            )
                        else:
                            # Обработка случая, когда result имеет неожиданный формат или None
                            self.logger.warning(f"Неверный формат данных для темы: {topic}. Тип: {type(result)}")
                            query.edit_message_text(
                                f"Произошла ошибка при обработке данных для темы *{topic}*. Пожалуйста, попробуйте выбрать другую тему.",
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
            result = self.content_service.get_topic_info(topic, update_message)

            # Проверяем формат полученных данных
            if isinstance(result, dict):
                # Обрабатываем словарь (dict)
                if result.get("status") == "success":
                    content = result.get("content", "")

                    # Разбиваем длинный контент на части, если нужно
                    if len(content) > 4000:
                        messages = [content[i:i+4000] for i in range(0, len(content), 4000)]
                    else:
                        messages = [content]

                    # Отправляем заголовок с первой частью
                    update.message.reply_text(
                        f"📚 *{topic}*\n\n{messages[0]}", 
                        parse_mode='Markdown'
                    )

                    # Отправляем остальные части как новые сообщения, если они есть
                    for msg in messages[1:]:
                        update.message.reply_text(msg, parse_mode='Markdown')
                else:
                    # Обработка ошибки
                    error_message = result.get("content", f"Не удалось получить информацию по теме: {topic}")
                    update.message.reply_text(
                        f"⚠️ {error_message}",
                        parse_mode='Markdown'
                    )
            elif isinstance(result, list) and len(result) > 0:
                # Обрабатываем список (list)
                for msg in result:
                    update.message.reply_text(msg, parse_mode='Markdown')
            else:
                # Обработка случая, когда список сообщений пуст или формат неизвестен
                self.logger.warning(f"Неверный формат данных для темы: {topic}. Тип: {type(result)}")
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

        # Очищаем историю чата перед ответом на новый вопрос
        self.message_manager.clear_chat_history(update, context)

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

        # Парсим правильный ответ из оригинального текста вопроса с улучшенной обработкой ошибок
        try:
            correct_answer = None
            # Поиск с более гибким регулярным выражением
            patterns = [
                r"Правильный ответ:\s*(\d+)",
                r"Правильный:\s*(\d+)",
                r"Ответ:\s*(\d+)",
                r"Верный ответ:\s*(\d+)"
            ]
            
            for pattern in patterns:
                correct_answer_match = re.search(pattern, original_questions[current_question])
                if correct_answer_match:
                    correct_answer = correct_answer_match.group(1)
                    break
                    
            if not correct_answer:
                # Попытка найти правильный ответ в конце текста
                lines = original_questions[current_question].split('\n')
                for line in reversed(lines):
                    if re.search(r"\d+", line):
                        match = re.search(r"\d+", line)
                        if match:
                            correct_answer = match.group(0)
                            break
            
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
            sent_msg = update.message.reply_text("❌ Неправильно!")
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
        Показывает следующий вопрос теста.

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
            
            # Отправляем номер вопроса
            sent_msg1 = update.message.reply_text(f"Вопрос {current_question+1} из {total_questions}:")
            self.message_manager.save_message_id(update, context, sent_msg1.message_id)

            # Отправляем текст вопроса
            sent_msg2 = update.message.reply_text(display_questions[current_question])
            self.message_manager.save_message_id(update, context, sent_msg2.message_id)

            # Создаем клавиатуру с кнопкой для завершения теста
            keyboard = [[InlineKeyboardButton("❌ Закончить тест", callback_data='end_test')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем инструкцию для ответа
            sent_msg3 = update.message.reply_text(
                "Напиши цифру правильного ответа (1, 2, 3 или 4).", 
                reply_markup=reply_markup
            )
            self.message_manager.save_message_id(update, context, sent_msg3.message_id)
            
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

    def handle_conversation(self, update, context):
        """
        Обрабатывает сообщения пользователя в режиме беседы с оптимизацией производительности.

        Также обрабатывает ввод ID нового администратора или темы для карты,
        если соответствующие флаги установлены.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора

        Returns:
            int: Следующее состояние разговора
        """
        # Обработка специальных состояний (карта, админ) с оптимизацией
        user_data = context.user_data

        # Проверяем, ожидаем ли мы ввод пользовательской темы для карты
        if user_data.get('waiting_for_map_topic', False):
            user_topic = update.message.text
            user_id = update.message.from_user.id

            # Немедленно сбрасываем флаг ожидания для предотвращения повторного вызова
            user_data['waiting_for_map_topic'] = False

            self.logger.debug(f"Пользователь {user_id} запросил карту по теме: {user_topic}")

            # Отправляем сообщение о генерации
            status_message = update.message.reply_text(
                f"🔄 Генерация карты по теме «{user_topic}»...",
                parse_mode='HTML'
            )

            try:
                # Запускаем генерацию карты с таймаутом для предотвращения зависаний
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Запускаем задачу с таймаутом 30 секунд
                    future = executor.submit(self.history_map.generate_map_by_topic, user_topic)
                    try:
                        map_image_path = future.result(timeout=30)
                    except concurrent.futures.TimeoutError:
                        map_image_path = None
                        self.logger.error(f"Превышено время ожидания при генерации карты по теме {user_topic}")

                if map_image_path and os.path.exists(map_image_path):
                    # Отправляем изображение карты
                    with open(map_image_path, 'rb') as img:
                        update.message.reply_photo(
                            photo=img,
                            caption=f"🗺️ Карта по теме «{user_topic}»",
                            parse_mode='HTML'
                        )

                    # Удаляем изображение карты после отправки
                    try:
                        os.remove(map_image_path)
                    except Exception:
                        pass

                    # Предлагаем вернуться к выбору категорий - упрощаем клавиатуру
                    keyboard = [
                        [InlineKeyboardButton("🔍 Другая тема", callback_data='map_search_topic'),
                         InlineKeyboardButton("🔙 К категориям", callback_data='history_map')],
                        [InlineKeyboardButton("📋 Главное меню", callback_data='back_to_menu')]
                    ]
                else:
                    # Если не удалось сгенерировать карту
                    keyboard = [
                        [InlineKeyboardButton("🔍 Другая тема", callback_data='map_search_topic'),
                         InlineKeyboardButton("🔙 К категориям", callback_data='history_map')]
                    ]
                    update.message.reply_text(
                        f"❌ Не удалось найти достаточно событий по теме «{user_topic}».",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except Exception as e:
                self.logger.error(f"Ошибка при генерации карты: {str(e)}")
                keyboard = [
                    [InlineKeyboardButton("🔍 Другая тема", callback_data='map_search_topic'),
                     InlineKeyboardButton("🔙 К категориям", callback_data='history_map')]
                ]
                update.message.reply_text(
                    f"❌ Произошла ошибка при генерации карты. Попробуйте другую тему.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            # В любом случае удаляем сообщение о генерации
            try:
                context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=status_message.message_id
                )
            except:
                pass

            return self.MAP

        # Проверяем, ожидаем ли мы ввод ID нового администратора
        if hasattr(self, 'admin_panel') and user_data.get('waiting_for_admin_id', False):
            self.admin_panel.process_new_admin_id(update, context)
            return self.CONVERSATION

        # Основная логика обработки обычных сообщений
        user_message = update.message.text
        user_id = update.message.from_user.id

        # Отправляем индикатор набора текста сразу
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        try:
            # Оптимизированная проверка исторической тематики с использованием хэш-таблицы (set)
            # вместо итерации по списку - намного быстрее при большом количестве ключевых слов
            history_keywords = {
                'россия', 'история', 'царь', 'император', 'ссср', 'война', 'революция',
                'русь', 'совет', 'петр', 'екатерина', 'сталин', 'ленин', 'князь',
                'династия', 'кремль', 'москва', 'киев', 'новгород', 'рюрик', 'романов'
            }

            # Оптимизируем за счет разбиения на слова и проверки отдельных слов
            # Это работает быстрее при длинных сообщениях
            words = set(user_message.lower().split())
            is_history_related = bool(words.intersection(history_keywords))

            # Быстрая проверка на вопрос или команду рассказать
            if not is_history_related and len(user_message) < 100:
                is_history_related = '?' in user_message or 'расскажи' in user_message.lower()

            # Оптимизированный вызов API с кэшированием и упрощенным запросом
            if is_history_related:
                # Сокращенный промпт для экономии токенов и ускорения ответа
                sanitized_message = self._sanitize_markdown(user_message)
                prompt = f"""Краткий ответ на исторический вопрос о России: "{sanitized_message}". Максимум 200 слов."""

                # Используем меньшее значение температуры и токенов для ускорения ответа и экономии
                response = self.api_client.ask_grok(prompt, max_tokens=600, temp=0.1)

                # Также обрабатываем ответ для избежания проблем с форматированием Markdown
                response = self._sanitize_markdown(response)
            else:
                # Используем заранее подготовленный ответ вместо генерации
                response = "Я отвечаю на вопросы по истории России. Пожалуйста, задайте исторический вопрос."

            # Оптимизация отправки сообщений - объединяем сообщение и кнопки
            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu')]]

            # Пытаемся отправить сообщение с ограничением длины для безопасности
            try:
                # Ограничиваем длину ответа для предотвращения ошибок парсинга
                if len(response) > 3500:
                    # Разбиваем на несколько сообщений если ответ слишком длинный
                    parts = [response[i:i+3500] for i in range(0, len(response), 3500)]
                    # Отправляем первую часть с кнопкой
                    sent_msg = update.message.reply_text(
                        parts[0] + "\n\n" + "Вы можете задать еще вопрос или вернуться в меню:",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=None  # Отключаем Markdown для безопасности
                    )
                    # Отправляем оставшиеся части если есть
                    for part in parts[1:]:
                        update.message.reply_text(part, parse_mode=None)
                else:
                    sent_msg = update.message.reply_text(
                        response + "\n\n" + "Вы можете задать еще вопрос или вернуться в меню:",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=None  # Отключаем Markdown для безопасности
                    )
            except telegram.error.BadRequest as e:
                # В случае ошибки парсинга отправляем без форматирования
                self.logger.error(f"Ошибка при отправке ответа: {e}")
                sent_msg = update.message.reply_text(
                    "Извините, произошла ошибка при форматировании ответа. Вот ответ без форматирования:\n\n" + 
                    response + "\n\n" + "Вы можете задать еще вопрос или вернуться в меню:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=None
                )
            self.message_manager.save_message_id(update, context, sent_msg.message_id)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке беседы: {str(e)}")
            # Упрощенное сообщение об ошибке
            error_msg = update.message.reply_text(
                "Произошла ошибка. Попробуйте позже или вернитесь в меню.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu')]])
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