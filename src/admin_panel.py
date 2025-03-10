import os
import json
import logging
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

class AdminPanel:
    """Класс для управления админ-панелью бота"""

    def __init__(self, logger, config):
        self.logger = logger
        self.config = config
        self.admins_file = 'admins.json' # Added for clarity and consistency
        self.admins = self._load_admins()

    def _load_admins(self):
        """Загружает список администраторов из файла с обработкой ошибок и кэшированием"""
        try:
            if not hasattr(self, '_admin_cache'):
                self._admin_cache = None
                self._admin_cache_time = 0

            # Используем кэш, если он актуален (не старше 5 минут)
            current_time = time.time()
            if self._admin_cache and current_time - self._admin_cache_time < 300:
                return self._admin_cache

            if os.path.exists(self.admins_file):
                with open(self.admins_file, 'r', encoding='utf-8') as f:
                    admin_data = json.load(f)
                    # Обновляем кэш
                    self._admin_cache = admin_data
                    self._admin_cache_time = current_time
                    return admin_data

            # Создаем структуру данных по умолчанию
            default_data = {"admin_ids": [], "super_admin_ids": []}
            self._admin_cache = default_data
            self._admin_cache_time = current_time
            return default_data
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке списка администраторов: {e}")
            return {"admin_ids": [], "super_admin_ids": []}

    def save_admins(self):
        """Сохраняет список администраторов в файл с защитой от повреждения"""
        try:
            # Используем атомарную операцию записи через временный файл
            temp_file = f"{self.admins_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.admins, f, indent=4)

            # Заменяем основной файл только после успешной записи
            os.replace(temp_file, self.admins_file)

            # Обновляем кэш
            self._admin_cache = self.admins.copy()
            self._admin_cache_time = time.time()
            return True #Added return for consistency
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении списка администраторов: {e}")
            return False #Added return for consistency

    def is_admin(self, user_id):
        """Проверяет, является ли пользователь администратором"""
        return user_id in self.admins.get("admin_ids", []) or user_id in self.admins.get("super_admin_ids", [])

    def is_super_admin(self, user_id):
        """Проверяет, является ли пользователь супер-администратором"""
        return user_id in self.admins.get("super_admin_ids", [])

    def add_admin(self, user_id, by_user_id=None, is_super=False):
        """Добавляет нового администратора"""
        try:
            if is_super:
                if user_id not in self.admins.get("super_admin_ids", []):
                    self.admins.setdefault("super_admin_ids", []).append(user_id)
                    self.logger.info(f"Добавлен супер-админ: {user_id}, добавил: {by_user_id}")
            else:
                if user_id not in self.admins.get("admin_ids", []):
                    self.admins.setdefault("admin_ids", []).append(user_id)
                    self.logger.info(f"Добавлен админ: {user_id}, добавил: {by_user_id}")

            return self.save_admins()
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении администратора: {e}")
            return False

    def remove_admin(self, user_id, by_user_id=None):
        """Удаляет администратора"""
        try:
            if user_id in self.admins.get("admin_ids", []):
                self.admins["admin_ids"].remove(user_id)
                self.logger.info(f"Удален админ: {user_id}, удалил: {by_user_id}")
                return self.save_admins()
            elif user_id in self.admins.get("super_admin_ids", []):
                self.admins["super_admin_ids"].remove(user_id)
                self.logger.info(f"Удален супер-админ: {user_id}, удалил: {by_user_id}")
                return self.save_admins()
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при удалении администратора: {e}")
            return False

    def handle_admin_command(self, update: Update, context: CallbackContext):
        """Обрабатывает команду /admin"""
        user_id = update.effective_user.id

        if not self.is_admin(user_id):
            update.message.reply_text("У вас нет прав администратора.")
            self.logger.warning(f"Пользователь {user_id} попытался получить доступ к админ-панели без прав")
            return

        # Показываем админ-панель
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 Управление админами", callback_data='admin_manage')],
            [InlineKeyboardButton("📝 Просмотр логов", callback_data='admin_logs')],
            [InlineKeyboardButton("🔄 Перезапустить бота", callback_data='admin_restart')]
        ]

        # Добавляем специальные функции для супер-админа
        if self.is_super_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Настройки бота", callback_data='admin_settings')])
            keyboard.append([InlineKeyboardButton("🔧 Техническое обслуживание", callback_data='admin_maintenance')])
            keyboard.append([InlineKeyboardButton("📚 Управление темами", callback_data='admin_topics')])
            keyboard.append([InlineKeyboardButton("🧪 Управление тестами", callback_data='admin_tests')])
            keyboard.append([InlineKeyboardButton("📈 Управление аналитикой", callback_data='admin_analytics')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"👑 *Панель администратора*\n\n"
            f"Добро пожаловать, {update.effective_user.first_name}!\n"
            f"Выберите действие в меню ниже:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Админ {user_id} открыл панель управления")

    def handle_admin_callback(self, update: Update, context: CallbackContext):
        """Обрабатывает нажатия на кнопки в админ-панели"""
        query = update.callback_query
        user_id = query.from_user.id

        if not self.is_admin(user_id):
            query.answer("У вас нет прав администратора.")
            self.logger.warning(f"Пользователь {user_id} попытался использовать функции админ-панели без прав")
            return

        query.answer()
        action = query.data

        if action == 'admin_stats':
            self._show_stats(query, context)
        elif action == 'admin_manage':
            self._show_admin_management(query, context)
        elif action == 'admin_logs':
            self._show_logs(query, context)
        elif action == 'admin_restart':
            self._restart_bot(query, context)
        elif action == 'admin_settings' and self.is_super_admin(user_id):
            self._show_settings(query, context)
        elif action == 'admin_maintenance' and self.is_super_admin(user_id):
            self._show_maintenance(query, context)
        elif action == 'admin_topics' and self.is_super_admin(user_id):
            self._show_topics_management(query, context)
        elif action == 'admin_tests' and self.is_super_admin(user_id):
            self._show_tests_management(query, context)
        elif action == 'admin_analytics' and self.is_super_admin(user_id):
            self._show_analytics_management(query, context)
        elif action == 'admin_back':
            # Возврат в главное меню админ-панели
            self._back_to_admin_menu(query, context)
        elif action.startswith('admin_add_'):
            # Обработка добавления админа
            self._handle_add_admin(query, context, action)
        elif action.startswith('admin_remove_'):
            # Обработка удаления админа
            self._handle_remove_admin(query, context, action)
        elif action.startswith('admin_topic_'):
            # Обработка действий с темами
            self._handle_topic_action(query, context, action)
        elif action.startswith('admin_test_'):
            # Обработка действий с тестами
            self._handle_test_action(query, context, action)
        elif action.startswith('admin_analytics_'):
            # Обработка действий с аналитикой
            self._handle_analytics_action(query, context, action)

    def _show_stats(self, query, context):
        """Показывает статистику бота"""
        try:
            # Подсчет количества сообщений и пользователей
            user_count = self._count_users()
            message_count = self._count_messages()

            stats_text = (
                "📊 *Статистика бота*\n\n"
                f"👥 Уникальных пользователей: {user_count}\n"
                f"💬 Всего сообщений: {message_count}\n"
                f"⏱️ Время работы: {self._get_uptime()}\n\n"
                f"*Пользовательская активность за последние 24 часа:*\n"
                f"🔄 Запусков бота: {self._count_bot_starts()}\n"
                f"📝 Запросов тем: {self._count_topic_requests()}\n"
                f"✅ Пройдено тестов: {self._count_completed_tests()}\n"
            )

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            self.logger.info(f"Админ {query.from_user.id} просмотрел статистику")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении статистики: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке статистики: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _show_admin_management(self, query, context):
        """Показывает интерфейс управления администраторами"""
        try:
            admins = self.admins.get("admin_ids", [])
            super_admins = self.admins.get("super_admin_ids", [])

            admin_text = "👥 *Управление администраторами*\n\n"

            # Список супер-админов
            admin_text += "*Супер-администраторы:*\n"
            if super_admins:
                for i, admin_id in enumerate(super_admins, 1):
                    admin_text += f"{i}. ID: {admin_id}\n"
            else:
                admin_text += "Нет супер-администраторов\n"

            # Список обычных админов
            admin_text += "\n*Администраторы:*\n"
            if admins:
                for i, admin_id in enumerate(admins, 1):
                    admin_text += f"{i}. ID: {admin_id}\n"
            else:
                admin_text += "Нет администраторов\n"

            # Кнопки управления
            keyboard = [
                [InlineKeyboardButton("➕ Добавить админа", callback_data='admin_add_regular')],
                [InlineKeyboardButton("➕ Добавить супер-админа", callback_data='admin_add_super')],
                [InlineKeyboardButton("➖ Удалить админа", callback_data='admin_remove_admin')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                admin_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            self.logger.info(f"Админ {query.from_user.id} открыл управление администраторами")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении управления администраторами: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке управления администраторами: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _show_logs(self, query, context):
        """Показывает последние записи логов"""
        try:
            log_content = self._get_last_logs(100)  # Получаем последние 100 строк логов

            # Разбиваем на части, если слишком длинное сообщение
            max_length = 4000
            log_parts = []

            current_part = "📝 *Последние записи логов*\n\n```"
            for log_line in log_content:
                if len(current_part) + len(log_line) + 4 > max_length:  # +4 для учета ```
                    current_part += "```"
                    log_parts.append(current_part)
                    current_part = "```\n" + log_line
                else:
                    current_part += log_line

            if current_part:
                current_part += "```"
                log_parts.append(current_part)

            # Отправляем первую часть с кнопкой назад
            query.edit_message_text(
                log_parts[0] if log_parts else "Логи отсутствуют",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]]),
                parse_mode='Markdown'
            )

            # Отправляем остальные части, если они есть
            for part in log_parts[1:]:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=part,
                    parse_mode='Markdown'
                )

            self.logger.info(f"Админ {query.from_user.id} просмотрел логи")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении логов: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке логов: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _restart_bot(self, query, context):
        """Перезапуск бота"""
        user_id = query.from_user.id

        # Проверяем права доступа (нужны права админа)
        if not self.is_admin(user_id):
            query.answer("У вас нет прав для перезапуска бота")
            return

        query.edit_message_text(
            "🔄 *Перезапуск бота*\n\n"
            "Вы уверены, что хотите перезапустить бота? "
            "Это приведет к кратковременной недоступности сервиса.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Да", callback_data='admin_restart_confirm'),
                    InlineKeyboardButton("❌ Нет", callback_data='admin_back')
                ]
            ]),
            parse_mode='Markdown'
        )

    def _show_settings(self, query, context):
        """Показывает настройки бота (только для супер-админов)"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        # Получаем текущие настройки
        settings = self._get_bot_settings()

        settings_text = (
            "⚙️ *Настройки бота*\n\n"
            f"🔄 Автоматическое обновление тем: {'Включено' if settings.get('auto_update_topics', True) else 'Выключено'}\n"
            f"📊 Сбор статистики: {'Включено' if settings.get('collect_statistics', True) else 'Выключено'}\n"
            f"🔍 Режим разработчика: {'Включено' if settings.get('developer_mode', False) else 'Выключено'}\n"
            f"🔐 Приватный режим: {'Включено' if settings.get('private_mode', False) else 'Выключено'}\n"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Автоматическое обновление тем", callback_data='admin_toggle_auto_update')],
            [InlineKeyboardButton("📊 Сбор статистики", callback_data='admin_toggle_statistics')],
            [InlineKeyboardButton("🔍 Режим разработчика", callback_data='admin_toggle_dev_mode')],
            [InlineKeyboardButton("🔐 Приватный режим", callback_data='admin_toggle_private_mode')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Супер-админ {query.from_user.id} открыл настройки бота")

    def _show_maintenance(self, query, context):
        """Показывает меню технического обслуживания (только для супер-админов)"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        maintenance_text = (
            "🔧 *Техническое обслуживание*\n\n"
            "Выберите действие из списка ниже:"
        )

        keyboard = [
            [InlineKeyboardButton("🗑️ Очистить кэш", callback_data='admin_clear_cache')],
            [InlineKeyboardButton("💾 Резервное копирование", callback_data='admin_backup')],
            [InlineKeyboardButton("🔄 Обновить данные API", callback_data='admin_update_api')],
            [InlineKeyboardButton("🧹 Очистка логов", callback_data='admin_clean_logs')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            maintenance_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Супер-админ {query.from_user.id} открыл меню технического обслуживания")

    def _back_to_admin_menu(self, query, context):
        """Возвращает пользователя в главное меню админ-панели"""
        user_id = query.from_user.id

        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 Управление админами", callback_data='admin_manage')],
            [InlineKeyboardButton("📝 Просмотр логов", callback_data='admin_logs')],
            [InlineKeyboardButton("🔄 Перезапустить бота", callback_data='admin_restart')]
        ]

        # Добавляем специальные функции для супер-админа
        if self.is_super_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Настройки бота", callback_data='admin_settings')])
            keyboard.append([InlineKeyboardButton("🔧 Техническое обслуживание", callback_data='admin_maintenance')])
            keyboard.append([InlineKeyboardButton("📚 Управление темами", callback_data='admin_topics')])
            keyboard.append([InlineKeyboardButton("🧪 Управление тестами", callback_data='admin_tests')])
            keyboard.append([InlineKeyboardButton("📈 Управление аналитикой", callback_data='admin_analytics')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"👑 *Панель администратора*\n\n"
            f"Добро пожаловать, {query.from_user.first_name}!\n"
            f"Выберите действие в меню ниже:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def _handle_add_admin(self, query, context, action):
        """Обрабатывает добавление нового администратора"""
        user_id = query.from_user.id

        # Проверка прав доступа (нужны права супер-админа для добавления админов)
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для добавления администраторов")
            return

        # Определяем тип добавляемого админа
        is_super = action == 'admin_add_super'
        admin_type = "супер-администратора" if is_super else "администратора"

        query.edit_message_text(
            f"➕ *Добавление {admin_type}*\n\n"
            f"Для добавления нового {admin_type}, отправьте его Telegram ID в следующем сообщении.\n\n"
            f"Чтобы отменить, нажмите кнопку ниже.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data='admin_back')]]),
            parse_mode='Markdown'
        )

        # Сохраняем контекст для следующего сообщения
        context.user_data['waiting_for_admin_id'] = is_super

        self.logger.info(f"Админ {user_id} инициировал добавление нового {admin_type}")

    def _handle_remove_admin(self, query, context, action):
        """Обрабатывает удаление администратора"""
        user_id = query.from_user.id

        # Проверка прав доступа (нужны права супер-админа для удаления админов)
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для удаления администраторов")
            return

        # Формируем список админов для удаления
        admins = self.admins.get("admin_ids", [])
        super_admins = self.admins.get("super_admin_ids", [])

        if not admins and not super_admins:
            query.edit_message_text(
                "В системе нет администраторов для удаления",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )
            return

        # Создаем клавиатуру с кнопками для выбора админа для удаления
        keyboard = []

        # Добавляем супер-админов
        for admin_id in super_admins:
            if admin_id != user_id:  # Не даем удалить самого себя
                keyboard.append([InlineKeyboardButton(f"Супер-админ: {admin_id}", callback_data=f'admin_delete_{admin_id}')])

        # Добавляем обычных админов
        for admin_id in admins:
            keyboard.append([InlineKeyboardButton(f"Админ: {admin_id}", callback_data=f'admin_delete_{admin_id}')])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='admin_back')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "👥 *Удаление администратора*\n\n"
            "Выберите администратора для удаления из списка ниже:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Админ {user_id} открыл меню удаления администраторов")

    # Вспомогательные методы для работы с данными

    def _count_users(self):
        """Подсчитывает количество уникальных пользователей"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из базы данных
            return 42  # Пример
        except Exception:
            return 0

    def _count_messages(self):
        """Подсчитывает общее количество сообщений"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из базы данных
            return 1337  # Пример
        except Exception:
            return 0

    def _get_uptime(self):
        """Возвращает время работы бота"""
        try:
            # Заглушка, нужно реализовать фактический подсчет времени работы
            return "3 дня 7 часов"  # Пример
        except Exception:
            return "Неизвестно"

    def _count_bot_starts(self):
        """Подсчитывает количество запусков бота за последние 24 часа"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из логов
            return 25  # Пример
        except Exception:
            return 0

    def _count_topic_requests(self):
        """Подсчитывает количество запросов тем за последние 24 часа"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из логов
            return 73  # Пример
        except Exception:
            return 0

    def _count_completed_tests(self):
        """Подсчитывает количество пройденных тестов за последние 24 часа"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из логов
            return 18  # Пример
        except Exception:
            return 0

    def _get_last_logs(self, lines=100):
        """Получает последние строки из файла логов"""
        try:
            log_files = []
            log_dir = "logs"

            # Проверяем, существует ли директория логов
            if os.path.exists(log_dir) and os.path.isdir(log_dir):
                # Получаем список файлов логов
                files = os.listdir(log_dir)
                log_files = [os.path.join(log_dir, f) for f in files if f.startswith("bot_log_")]

            # Если директории нет или нет файлов логов, проверяем в корневой директории
            if not log_files:
                files = [f for f in os.listdir() if f.startswith("bot_log_")]
                log_files = files

            # Сортируем файлы по дате изменения (новые в начале)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            if not log_files:
                return ["Файлы логов не найдены"]

            # Берем самый свежий файл логов
            latest_log = log_files[0]

            with open(latest_log, 'r', encoding='utf-8') as f:
                # Получаем последние lines строк
                return list(f)[-lines:]
        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла логов: {e}")
            return [f"Ошибка при чтении логов: {e}"]

    def _get_bot_settings(self):
        """Получает текущие настройки бота"""
        try:
            if os.path.exists('bot_settings.json'):
                with open('bot_settings.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Возвращаем настройки по умолчанию
                return {
                    "auto_update_topics": True,
                    "collect_statistics": True,
                    "developer_mode": False,
                    "private_mode": False
                }
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке настроек бота: {e}")
            return {}

    def process_new_admin_id(self, update, context):
        """Обрабатывает ввод ID нового администратора"""
        user_id = update.effective_user.id

        # Проверяем, что пользователь является супер-админом
        if not self.is_super_admin(user_id):
            update.message.reply_text("У вас нет прав для добавления администраторов")
            return

        # Проверяем, ожидаем ли мы ID нового администратора
        if 'waiting_for_admin_id' not in context.user_data:
            update.message.reply_text("Ошибка: не инициирован процесс добавления администратора")
            return

        is_super = context.user_data.get('waiting_for_admin_id')
        admin_type = "супер-администратора" if is_super else "администратора"

        # Очищаем состояние ожидания
        del context.user_data['waiting_for_admin_id']

        # Парсим ID из сообщения
        try:
            new_admin_id = int(update.message.text.strip())
        except ValueError:
            update.message.reply_text(
                f"❌ Ошибка: ID администратора должен быть числом.\n"
                f"Попробуйте снова через меню администратора.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )
            return

        # Проверяем, не существует ли уже такой админ
        if new_admin_id in self.admins.get("admin_ids", []) or new_admin_id in self.admins.get("super_admin_ids", []):
            update.message.reply_text(
                f"❌ Ошибка: пользователь с ID {new_admin_id} уже является администратором.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )
            return

        # Добавляем нового админа
        success = self.add_admin(new_admin_id, by_user_id=user_id, is_super=is_super)

        if success:
            update.message.reply_text(
                f"✅ {admin_type.capitalize()} с ID {new_admin_id} успешно добавлен!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )
            self.logger.info(f"Админ {user_id} добавил нового {admin_type} с ID {new_admin_id}")
        else:
            update.message.reply_text(
                f"❌ Ошибка при добавлении {admin_type}. Попробуйте снова позже.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )

    def handle_delete_admin_callback(self, update, context, admin_id_to_delete):
        """Обрабатывает удаление администратора по callback"""
        query = update.callback_query
        user_id = query.from_user.id

        # Проверяем права доступа
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для удаления администраторов")
            return

        # Проверяем, не пытается ли админ удалить самого себя
        if int(admin_id_to_delete) == user_id:
            query.answer("Вы не можете удалить самого себя")
            return

        # Удаляем администратора
        success = self.remove_admin(int(admin_id_to_delete), by_user_id=user_id)

        if success:
            query.answer(f"Администратор с ID {admin_id_to_delete} успешно удален!")
            self.logger.info(f"Админ {user_id} удалил администратора с ID {admin_id_to_delete}")

            # Возвращаемся к списку администраторов
            self._show_admin_management(query, context)
        else:
            query.answer(f"Ошибка при удалении администратора с ID {admin_id_to_delete}")

    def _show_topics_management(self, query, context):
        """Показывает интерфейс управления историческими темами"""
        try:
            topics_text = "📚 *Управление историческими темами*\n\n"
            topics_text += "Здесь вы можете управлять историческими темами, добавлять новые или редактировать существующие."

            keyboard = [
                [InlineKeyboardButton("➕ Добавить новую тему", callback_data='admin_topic_add')],
                [InlineKeyboardButton("📋 Просмотреть все темы", callback_data='admin_topic_list')],
                [InlineKeyboardButton("🔍 Найти тему", callback_data='admin_topic_search')],
                [InlineKeyboardButton("🔄 Обновить темы из API", callback_data='admin_topic_update')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                topics_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            self.logger.info(f"Админ {query.from_user.id} открыл управление темами")
        except Exception as e:
            self.logger.error(f"Ошибка при открытии управления темами: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке управления темами: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _show_tests_management(self, query, context):
        """Показывает интерфейс управления тестами"""
        try:
            tests_text = "🧪 *Управление тестами*\n\n"
            tests_text += "Здесь вы можете настроить параметры генерации тестов и просмотреть статистику прохождения."

            keyboard = [
                [InlineKeyboardButton("⚙️ Настройки генерации тестов", callback_data='admin_test_settings')],
                [InlineKeyboardButton("📊 Статистика прохождения", callback_data='admin_test_stats')],
                [InlineKeyboardButton("🔍 Предпросмотр теста", callback_data='admin_test_preview')],
                [InlineKeyboardButton("🗑️ Очистка кэша тестов", callback_data='admin_test_clear_cache')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                tests_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            self.logger.info(f"Админ {query.from_user.id} открыл управление тестами")
        except Exception as e:
            self.logger.error(f"Ошибка при открытии управления тестами: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке управления тестами: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _show_analytics_management(self, query, context):
        """Показывает интерфейс управления аналитикой"""
        try:
            analytics_text = "📈 *Управление аналитикой*\n\n"
            analytics_text += "Здесь вы можете просмотреть подробную аналитику использования бота и выгрузить отчеты."

            keyboard = [
                [InlineKeyboardButton("👥 Активность пользователей", callback_data='admin_analytics_users')],
                [InlineKeyboardButton("📚 Популярность тем", callback_data='admin_analytics_topics')],
                [InlineKeyboardButton("🧪 Статистика тестирования", callback_data='admin_analytics_tests')],
                [InlineKeyboardButton("💾 Экспорт аналитики", callback_data='admin_analytics_export')],
                [InlineKeyboardButton("⚙️ Настройки сбора данных", callback_data='admin_analytics_settings')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                analytics_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            self.logger.info(f"Админ {query.from_user.id} открыл управление аналитикой")
        except Exception as e:
            self.logger.error(f"Ошибка при открытии управления аналитикой: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке управления аналитикой: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _handle_topic_action(self, query, context, action):
        """Обрабатывает действия с историческими темами"""
        user_id = query.from_user.id
        
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для управления темами")
            return
            
        if action == 'admin_topic_add':
            # Логика добавления новой темы
            query.edit_message_text(
                "➕ *Добавление новой исторической темы*\n\n"
                "Для добавления новой темы, отправьте сообщение в формате:\n"
                "`Название темы | Краткое описание`\n\n"
                "Например:\n"
                "`Реформы Петра I | Политические и экономические реформы первого российского императора`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data='admin_topics')]]),
                parse_mode='Markdown'
            )
            # Устанавливаем состояние ожидания ввода темы
            context.user_data['waiting_for_topic'] = True
            
        elif action == 'admin_topic_list':
            # Логика отображения списка тем
            # Здесь должен быть код загрузки тем из базы данных
            # Например, используя TopicService
            topics = ["Тема 1", "Тема 2", "Тема 3"]  # Заглушка, заменить на реальные данные
            
            topics_text = "📋 *Список исторических тем*\n\n"
            for i, topic in enumerate(topics[:10], 1):
                topics_text += f"{i}. {topic}\n"
                
            if len(topics) > 10:
                topics_text += f"\nПоказано 10 из {len(topics)} тем. Используйте поиск для более точных результатов."
                
            query.edit_message_text(
                topics_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_topics')]]),
                parse_mode='Markdown'
            )
            
        elif action == 'admin_topic_search':
            # Логика поиска темы
            query.edit_message_text(
                "🔍 *Поиск исторической темы*\n\n"
                "Введите ключевое слово или фразу для поиска темы:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data='admin_topics')]]),
                parse_mode='Markdown'
            )
            # Устанавливаем состояние ожидания ввода поискового запроса
            context.user_data['waiting_for_topic_search'] = True
            
        elif action == 'admin_topic_update':
            # Логика обновления тем из API
            query.edit_message_text(
                "🔄 *Обновление исторических тем*\n\n"
                "Выполняется обновление базы исторических тем из API...\n"
                "Это может занять некоторое время.",
                parse_mode='Markdown'
            )
            
            try:
                # Здесь должен быть код обновления тем
                # Например, вызов функции из TopicService
                # topic_service.update_all_topics()
                
                # Заглушка для демонстрации
                import time
                time.sleep(2)
                
                query.edit_message_text(
                    "✅ *Обновление выполнено успешно*\n\n"
                    "База исторических тем успешно обновлена.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_topics')]]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                self.logger.error(f"Ошибка при обновлении тем: {e}")
                query.edit_message_text(
                    f"❌ *Ошибка при обновлении тем*\n\n"
                    f"Произошла ошибка: {e}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_topics')]]),
                    parse_mode='Markdown'
                )

    def _handle_test_action(self, query, context, action):
        """Обрабатывает действия с тестами"""
        user_id = query.from_user.id
        
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для управления тестами")
            return
            
        if action == 'admin_test_settings':
            # Настройки генерации тестов
            test_settings = self._get_test_settings()
            
            settings_text = (
                "⚙️ *Настройки генерации тестов*\n\n"
                f"📊 Количество вопросов: {test_settings.get('questions_count', 5)}\n"
                f"🔄 Время на ответ: {test_settings.get('answer_time', 30)} сек\n"
                f"🌡️ Температура генерации: {test_settings.get('temperature', 0.7)}\n"
                f"🔢 Максимальное количество вариантов: {test_settings.get('max_options', 4)}\n"
                f"📏 Сложность по умолчанию: {test_settings.get('default_difficulty', 'средняя')}\n"
            )
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить настройки", callback_data='admin_test_edit_settings')],
                [InlineKeyboardButton("🔄 Сбросить по умолчанию", callback_data='admin_test_reset_settings')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_tests')]
            ]
            
            query.edit_message_text(
                settings_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif action == 'admin_test_stats':
            # Статистика прохождения тестов
            stats_text = (
                "📊 *Статистика прохождения тестов*\n\n"
                "👥 Всего пройдено тестов: 247\n"
                "✅ Средний процент правильных ответов: 68%\n"
                "⏱️ Среднее время прохождения: 3 мин 24 сек\n\n"
                "*Популярные темы тестирования:*\n"
                "1. Великая Отечественная война - 42 теста\n"
                "2. Правление Петра I - 39 тестов\n"
                "3. Революция 1917 года - 28 тестов\n"
            )
            
            query.edit_message_text(
                stats_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_tests')]]),
                parse_mode='Markdown'
            )
            
        elif action == 'admin_test_preview':
            # Предпросмотр теста
            query.edit_message_text(
                "🔍 *Предпросмотр теста*\n\n"
                "Введите тему для генерации тестового вопроса:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data='admin_tests')]]),
                parse_mode='Markdown'
            )
            # Устанавливаем состояние ожидания ввода темы для теста
            context.user_data['waiting_for_test_topic'] = True
            
        elif action == 'admin_test_clear_cache':
            # Очистка кэша тестов
            query.edit_message_text(
                "🗑️ *Очистка кэша тестов*\n\n"
                "Вы уверены, что хотите очистить кэш тестов? "
                "Это может повлиять на скорость генерации новых тестов.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Да", callback_data='admin_test_confirm_clear'),
                        InlineKeyboardButton("❌ Нет", callback_data='admin_tests')
                    ]
                ]),
                parse_mode='Markdown'
            )

    def _handle_analytics_action(self, query, context, action):
        """Обрабатывает действия с аналитикой"""
        user_id = query.from_user.id
        
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для управления аналитикой")
            return
            
        if action == 'admin_analytics_users':
            # Активность пользователей
            users_text = (
                "👥 *Активность пользователей*\n\n"
                "Всего уникальных пользователей: 352\n"
                "Активных за последние 24 часа: 78\n"
                "Новых пользователей за неделю: 42\n\n"
                "*График активности по дням недели:*\n"
                "Пн: ██████ 60\n"
                "Вт: ████ 40\n"
                "Ср: ███████ 70\n"
                "Чт: ██████████ 100\n"
                "Пт: ████████ 80\n"
                "Сб: ███ 30\n"
                "Вс: ██ 20\n"
            )
            
            query.edit_message_text(
                users_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_analytics')]]),
                parse_mode='Markdown'
            )
            
        elif action == 'admin_analytics_topics':
            # Популярность тем
            topics_text = (
                "📚 *Популярность исторических тем*\n\n"
                "*Самые запрашиваемые темы:*\n"
                "1. Великая Отечественная война - 126 запросов\n"
                "2. Революция 1917 года - 89 запросов\n"
                "3. Правление Ивана Грозного - 78 запросов\n"
                "4. Петровские реформы - 65 запросов\n"
                "5. Отмена крепостного права - 57 запросов\n\n"
                "*Средняя оценка полезности информации:* 4.7/5"
            )
            
            query.edit_message_text(
                topics_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_analytics')]]),
                parse_mode='Markdown'
            )
            
        elif action == 'admin_analytics_tests':
            # Статистика тестирования
            tests_text = (
                "🧪 *Статистика тестирования*\n\n"
                "Всего пройдено тестов: 247\n"
                "Средний результат: 68%\n\n"
                "*Распределение по сложности:*\n"
                "- Легкие: 42% (сред. результат 82%)\n"
                "- Средние: 53% (сред. результат 65%)\n"
                "- Сложные: 5% (сред. результат 48%)\n\n"
                "*Самые сложные вопросы:*\n"
                "1. Даты Ливонской войны (31% правильных ответов)\n"
                "2. Условия Ништадтского мира (35% правильных ответов)\n"
            )
            
            query.edit_message_text(
                tests_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_analytics')]]),
                parse_mode='Markdown'
            )
            
        elif action == 'admin_analytics_export':
            # Экспорт аналитики
            export_text = (
                "💾 *Экспорт аналитических данных*\n\n"
                "Выберите формат экспорта:"
            )
            
            keyboard = [
                [InlineKeyboardButton("📊 CSV", callback_data='admin_analytics_export_csv')],
                [InlineKeyboardButton("📑 JSON", callback_data='admin_analytics_export_json')],
                [InlineKeyboardButton("📈 Excel", callback_data='admin_analytics_export_excel')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_analytics')]
            ]
            
            query.edit_message_text(
                export_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif action == 'admin_analytics_settings':
            # Настройки сбора данных
            settings = self._get_analytics_settings()
            
            settings_text = (
                "⚙️ *Настройки сбора аналитических данных*\n\n"
                f"📊 Сбор общей статистики: {'Включен' if settings.get('collect_general', True) else 'Выключен'}\n"
                f"👤 Сбор пользовательских данных: {'Включен' if settings.get('collect_user_data', True) else 'Выключен'}\n"
                f"📚 Отслеживание популярности тем: {'Включено' if settings.get('track_topics', True) else 'Выключено'}\n"
                f"🧪 Анализ результатов тестов: {'Включен' if settings.get('analyze_tests', True) else 'Выключен'}\n"
                f"⏱️ Интервал агрегации данных: {settings.get('aggregation_interval', '24')} часа\n"
            )
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить настройки", callback_data='admin_analytics_edit_settings')],
                [InlineKeyboardButton("🔄 Сбросить по умолчанию", callback_data='admin_analytics_reset_settings')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_analytics')]
            ]
            
            query.edit_message_text(
                settings_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    def _get_test_settings(self):
        """Получает настройки генерации тестов"""
        try:
            if os.path.exists('test_settings.json'):
                with open('test_settings.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Возвращаем настройки по умолчанию
                return {
                    "questions_count": 5,
                    "answer_time": 30,
                    "temperature": 0.7,
                    "max_options": 4,
                    "default_difficulty": "средняя"
                }
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке настроек тестов: {e}")
            return {}

    def _get_analytics_settings(self):
        """Получает настройки сбора аналитических данных"""
        try:
            if os.path.exists('analytics_settings.json'):
                with open('analytics_settings.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Возвращаем настройки по умолчанию
                return {
                    "collect_general": True,
                    "collect_user_data": True,
                    "track_topics": True,
                    "analyze_tests": True,
                    "aggregation_interval": 24
                }
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке настроек аналитики: {e}")
            return {}
